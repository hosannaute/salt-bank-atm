import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from simulator import Bank, make_server


class BankingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'test.db'
        self.bank = Bank(self.path)
        self.token = self.bank.register({'name': 'Test User', 'pin': '0123'})
        self.account = self.bank.session(self.token)
        self.other = self.bank.session(self.bank.register({'name': 'Recipient', 'pin': '5678'}))

    def tearDown(self):
        self.directory.cleanup()

    def move(self, kind, amount, **kwargs):
        return self.bank.transact(self.account, {'kind': kind, 'amount': amount, 'pin': '0123', **kwargs})

    def test_register_card_and_hashed_pin(self):
        user = self.bank.snapshot(self.account)
        self.assertEqual(user['balance'], 0)
        self.assertEqual(len(user['card']), 4)
        self.assertNotIn('pin', user)
        self.assertEqual(self.bank.session(self.bank.login({'account': self.account, 'pin': '0123'}, 'test')), self.account)
        with self.bank.connect() as db:
            self.assertNotEqual(db.execute('SELECT pin FROM accounts WHERE id=?', (self.account,)).fetchone()['pin'], '0123')

    def test_full_flow_and_persistence(self):
        self.move('deposit', 10000)
        self.move('withdraw', 1500)
        self.move('transfer', 2500, target=self.other)
        restored = Bank(self.path)
        self.assertEqual(restored.snapshot(self.account)['balance'], 6000)
        self.assertEqual(restored.snapshot(self.other)['balance'], 2500)
        self.assertEqual(restored.snapshot(self.account)['transactions'][0]['amount'], -2500)
        self.assertEqual(restored.snapshot(self.other)['transactions'][0]['kind'], 'received')

    def test_invalid_transactions_do_not_change_balance(self):
        self.move('deposit', 5000)
        for kind, amount, extra in [('deposit', -10, {}), ('deposit', True, {}), ('deposit', 1.5, {}),
                                    ('withdraw', 600, {}), ('withdraw', 100500, {}), ('withdraw', 10000, {}),
                                    ('withdraw', 1000, {'pin': '9999'}), ('transfer', 100, {'target': self.account}),
                                    ('transfer', 100, {'target': '00000000'}), ('transfer', 100, {'target': []})]:
            with self.subTest(kind=kind, amount=amount, extra=extra), self.assertRaises(ValueError):
                self.move(kind, amount, **extra)
        self.assertEqual(self.bank.snapshot(self.account)['balance'], 5000)
        self.assertEqual(len(self.bank.snapshot(self.account)['transactions']), 2)

    def test_frozen_card_stops_spending_but_allows_deposits(self):
        with self.bank.connect() as db:
            db.execute('UPDATE accounts SET frozen=1 WHERE id=?', (self.account,))
        self.move('deposit', 1000)
        for kind in ['withdraw', 'transfer']:
            with self.assertRaisesRegex(ValueError, 'frozen'):
                self.move(kind, 500, target=self.other)

    def test_concurrent_withdrawals_cannot_overdraw(self):
        self.move('deposit', 1000)
        results = []
        def withdraw():
            try:
                self.move('withdraw', 1000)
                results.append('ok')
            except ValueError:
                results.append('declined')
        threads = [threading.Thread(target=withdraw) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertCountEqual(results, ['ok', 'declined'])
        self.assertEqual(self.bank.snapshot(self.account)['balance'], 0)

    def test_validation_and_login_throttle(self):
        for pin in ['12', 'abcd', '１２３４', 1234]:
            with self.assertRaises(ValueError): self.bank.register({'name': 'User', 'pin': pin})
        for _ in range(5):
            with self.assertRaises(ValueError): self.bank.login({'account': self.account, 'pin': '9999'}, 'bad')
        with self.assertRaisesRegex(ValueError, 'Too many'):
            self.bank.login({'account': self.account, 'pin': '0123'}, 'bad')
        with self.assertRaises(ValueError): self.bank.session('invalid')


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.server = make_server(Path(self.directory.name) / 'test.db', port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = http.client.HTTPConnection('127.0.0.1', self.server.server_port)

    def tearDown(self):
        self.client.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def request(self, path, data=None, cookie='', origin=None):
        headers = {'Content-Type': 'application/json', 'Cookie': cookie}
        if origin: headers['Origin'] = origin
        self.client.request('GET' if data is None else 'POST', path, None if data is None else json.dumps(data), headers)
        response = self.client.getresponse()
        body = response.read()
        return response, json.loads(body) if path.startswith('/api/') else body

    def test_session_logout_and_origin(self):
        self.assertEqual(self.request('/api/me')[0].status, 401)
        response, user = self.request('/api/register', {'name': 'Web User', 'pin': '1234'})
        self.assertEqual(response.status, 200)
        cookie = response.getheader('Set-Cookie').split(';')[0]
        self.assertIn('HttpOnly', response.getheader('Set-Cookie'))
        self.assertEqual(self.request('/api/me', cookie=cookie)[1]['id'], user['id'])
        self.assertEqual(self.request('/api/transaction', {'kind':'deposit','amount':5000}, cookie, 'https://evil.example')[0].status, 403)
        self.assertEqual(self.request('/api/transaction', {'kind':'deposit','amount':5000}, cookie)[1]['balance'], 5000)
        self.request('/api/logout', {}, cookie)
        self.assertEqual(self.request('/api/me', cookie=cookie)[0].status, 401)

    def test_frontend_and_bad_payload(self):
        response, body = self.request('/')
        self.assertEqual(response.status, 200)
        self.assertIn(b'Your money, at a glance.', body)
        self.assertIn("default-src 'self'", response.getheader('Content-Security-Policy'))
        self.assertEqual(self.request('/api/register', [1,2])[0].status, 400)


if __name__ == '__main__':
    unittest.main()
