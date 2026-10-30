"""Local-only ATM learning simulator. No real bank or payment integrations."""
import argparse
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

WEB = Path(__file__).resolve().parent / 'web'


def pin_hash(pin, salt):
    return hashlib.pbkdf2_hmac('sha256', pin.encode(), bytes.fromhex(salt), 160000).hex()


class Bank:
    def __init__(self, path):
        self.path = str(path)
        self.sessions = {}
        self.attempts = {}
        self.lock = threading.Lock()
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, salt TEXT NOT NULL,
                    pin TEXT NOT NULL, balance INTEGER NOT NULL DEFAULT 0 CHECK(balance >= 0),
                    card TEXT NOT NULL, frozen INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY, account TEXT NOT NULL, kind TEXT NOT NULL,
                    amount INTEGER NOT NULL, detail TEXT NOT NULL,
                    created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def session(self, token):
        with self.lock:
            entry = self.sessions.get(token)
            if entry and entry[1] > time.time():
                return entry[0]
            self.sessions.pop(token, None)
        raise ValueError('Please sign in to continue.')

    def signin(self, account):
        token = secrets.token_urlsafe(32)
        with self.lock:
            now = time.time()
            self.sessions = {k: v for k, v in self.sessions.items() if v[1] > now}
            self.sessions[token] = (account, now + 1800)
        return token

    @staticmethod
    def validate_pin(pin):
        if not isinstance(pin, str) or len(pin) != 4 or not pin.isascii() or not pin.isdigit():
            raise ValueError('Choose a PIN with exactly four digits.')

    def register(self, data):
        name = data.get('name', '')
        if not isinstance(name, str) or not 2 <= len(name.strip()) <= 60:
            raise ValueError('Enter your full name (2–60 characters).')
        pin = data.get('pin')
        self.validate_pin(pin)
        salt = secrets.token_hex(16)
        with self.connect() as db:
            while True:
                account = str(secrets.randbelow(90000000) + 10000000)
                if not db.execute('SELECT id FROM accounts WHERE id=?', (account,)).fetchone():
                    break
            db.execute('INSERT INTO accounts(id,name,salt,pin,card) VALUES(?,?,?,?,?)',
                       (account, name.strip(), salt, pin_hash(pin, salt), f'{secrets.randbelow(10000):04d}'))
            db.execute('INSERT INTO transactions(account,kind,amount,detail) VALUES(?,?,?,?)',
                       (account, 'account', 0, 'Account opened · virtual card issued'))
        return self.signin(account)

    def login(self, data, address):
        account, pin = data.get('account'), data.get('pin')
        self.validate_pin(pin)
        if not isinstance(account, str) or len(account) != 8 or not account.isascii() or not account.isdigit():
            raise ValueError('Enter your 8-digit account number.')
        with self.lock:
            failures, until = self.attempts.get(address, (0, 0))
            if until > time.time():
                raise ValueError('Too many attempts. Try again in a minute.')
        with self.connect() as db:
            user = db.execute('SELECT * FROM accounts WHERE id=?', (account,)).fetchone()
        if not user or not hmac.compare_digest(user['pin'], pin_hash(pin, user['salt'])):
            with self.lock:
                self.attempts[address] = (failures + 1, time.time() + 60 if failures + 1 >= 5 else 0)
            raise ValueError('Account number or PIN is incorrect.')
        with self.lock:
            self.attempts.pop(address, None)
        return self.signin(account)

    def snapshot(self, account):
        with self.connect() as db:
            user = dict(db.execute('SELECT id,name,balance,card,frozen FROM accounts WHERE id=?', (account,)).fetchone())
            user['transactions'] = [dict(r) for r in db.execute(
                'SELECT id,kind,amount,detail,created FROM transactions WHERE account=? ORDER BY id DESC LIMIT 100', (account,))]
        return user

    def transact(self, account, data):
        kind, amount = data.get('kind'), data.get('amount')
        if kind not in ('deposit', 'withdraw', 'transfer'):
            raise ValueError('Choose a supported transaction.')
        if type(amount) is not int or not 0 < amount <= 1000000:
            raise ValueError('Enter a whole naira amount between ₦1 and ₦1,000,000.')
        if kind == 'withdraw' and (amount % 500 or amount > 100000):
            raise ValueError('Withdraw in multiples of ₦500, up to ₦100,000 per transaction.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            user = db.execute('SELECT * FROM accounts WHERE id=?', (account,)).fetchone()
            if kind in ('withdraw', 'transfer'):
                if user['frozen']:
                    raise ValueError('Your card is frozen. Unfreeze it in My card to continue.')
                pin = data.get('pin')
                self.validate_pin(pin)
                if not hmac.compare_digest(user['pin'], pin_hash(pin, user['salt'])):
                    raise ValueError('Incorrect transaction PIN.')
                if amount > user['balance']:
                    raise ValueError('Insufficient funds. Add money to your account first.')
            detail = 'Cash added to account' if kind == 'deposit' else 'ATM cash withdrawal'
            if kind == 'transfer':
                target = data.get('target')
                if not isinstance(target, str) or len(target) != 8 or not target.isascii() or not target.isdigit():
                    raise ValueError('Enter an 8-digit recipient account number.')
                recipient = db.execute('SELECT name FROM accounts WHERE id=?', (target,)).fetchone()
                if target == account:
                    raise ValueError('Choose an account other than your own.')
                if not recipient:
                    raise ValueError('Recipient account not found. Use another simulator account.')
                db.execute('UPDATE accounts SET balance=balance+? WHERE id=?', (amount, target))
                db.execute('INSERT INTO transactions(account,kind,amount,detail) VALUES(?,?,?,?)',
                           (target, 'received', amount, 'From ' + user['name']))
                detail = 'To ' + recipient['name']
            signed = amount if kind == 'deposit' else -amount
            db.execute('UPDATE accounts SET balance=balance+? WHERE id=?', (signed, account))
            cursor = db.execute('INSERT INTO transactions(account,kind,amount,detail) VALUES(?,?,?,?)',
                                (account, kind, signed, detail))
            receipt = cursor.lastrowid
        return receipt


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, format, *args):
        pass

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        super().end_headers()

    def token(self):
        cookie = SimpleCookie()
        cookie.load(self.headers.get('Cookie', ''))
        return cookie['session'].value if 'session' in cookie else ''

    def reply(self, data, status=200, cookie=None):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(payload)))
        if cookie is not None:
            self.send_header('Set-Cookie', f'session={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age={1800 if cookie else 0}')
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == '/api/me':
            try:
                self.reply(self.server.bank.snapshot(self.server.bank.session(self.token())))
            except ValueError as exc:
                self.reply({'error': str(exc)}, 401)
        elif self.path.startswith('/api/'):
            self.reply({'error': 'Not found'}, 404)
        else:
            super().do_GET()

    def do_POST(self):
        try:
            origin = self.headers.get('Origin')
            if origin and urlsplit(origin).netloc != self.headers.get('Host'):
                self.reply({'error': 'Origin not allowed'}, 403)
                return
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096 or self.headers.get('Content-Type') != 'application/json':
                raise ValueError('Send a small JSON request.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object.')
            bank = self.server.bank
            if self.path in ('/api/register', '/api/login'):
                token = bank.register(data) if self.path.endswith('register') else bank.login(data, self.client_address[0])
                self.reply(bank.snapshot(bank.session(token)), cookie=token)
                return
            account = bank.session(self.token())
            if self.path == '/api/logout':
                with bank.lock:
                    bank.sessions.pop(self.token(), None)
                self.reply({'ok': True}, cookie='')
            elif self.path == '/api/transaction':
                receipt = bank.transact(account, data)
                self.reply({**bank.snapshot(account), 'receipt': receipt})
            elif self.path == '/api/card':
                if type(data.get('frozen')) is not bool:
                    raise ValueError('Choose a valid card state.')
                with bank.connect() as db:
                    db.execute('UPDATE accounts SET frozen=? WHERE id=?', (int(data['frozen']), account))
                self.reply(bank.snapshot(account))
            else:
                self.reply({'error': 'Not found'}, 404)
        except (ValueError, TypeError, sqlite3.IntegrityError) as exc:
            self.reply({'error': str(exc)}, 400)


def make_server(path, host='127.0.0.1', port=8000):
    server = ThreadingHTTPServer((host, port), Handler)
    server.bank = Bank(path)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--data-dir', default=str(Path.home() / '.local/share/salt-bank'))
    args = parser.parse_args()
    directory = Path(args.data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    server = make_server(directory / 'simulator.db', args.host, args.port)
    print(f'Salt Bank simulator running at http://{args.host}:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
