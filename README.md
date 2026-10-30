# Salt Bank · ATM Simulator

A visual banking simulator for practicing everyday money skills. Open an account, get a virtual debit card, add practice money, withdraw virtual cash, and transfer to another simulator account. The responsive dashboard includes balances, receipts, transaction history, and card freezing.

**Simulation only:** no real money, bank connections, payments, or actual cards. Use a made-up name and practice PIN. Never enter real banking credentials.

## Run the visual app

Requires Python 3.10+; no third-party packages or build tools needed.

```bash
cd /workspace/salt-bank-atm
python3 simulator.py
```

Open `http://127.0.0.1:8000` in a browser on the same machine. The server binds to loopback by default. In a remote development environment, use your editor's port forwarding for port 8000. Keep it private: this is a local learning project, not a production banking service.

Optional settings:

```bash
python3 simulator.py --port 8001 --data-dir /tmp/salt-bank-practice
```

New accounts start at ₦0. Register with a name and four-digit PIN; a virtual card is issued automatically. Save your eight-digit account number, shown below the balance, to sign in again. Add money, then try the ATM. Withdrawals require your PIN, use ₦500 denominations, and are limited to ₦100,000 per transaction. Deposits and transfers allow whole naira amounts up to ₦1,000,000 per transaction. Transfers require another registered simulator account number; create a second account to try them.

Freeze/unfreeze your card under **My card**. A frozen card blocks withdrawals and outgoing transfers while allowing incoming funds. Successful transactions produce a receipt and update balances/history immediately. The history shows the latest 100 entries.

## Data and security scope

SQLite stores simulator accounts and transactions in `~/.local/share/salt-bank/simulator.db` by default. Choose a separate `--data-dir` for testing or another practice bank. This database is independent of the original `bank_data.json`; sample accounts are not imported or displayed. Existing CLI data remains unchanged.

PINs are salted and hashed with PBKDF2; sessions use HTTP-only SameSite cookies and expire after 30 minutes. Restarting the server signs users out but retains accounts and balances. Local HTTP is intentional; keep the service private. The app is not designed for public deployment or real financial data. It has no account recovery; use another practice account if you forget your PIN.

## Validate

```bash
python3 -m unittest -v test_simulator.py
```

Tests use temporary databases and cover account creation, PIN validation, authentication, transaction persistence, transfers, card freezes, rejected transactions, concurrent withdrawals, session logout, origin checks, and frontend serving.

## Original terminal app

The original CLI remains available:

```bash
python3 /workspace/salt-bank-atm/salt_bank_atm.py
```

It uses `bank_data.json` relative to the current working directory. Run from a separate scratch directory to avoid modifying the tracked sample data. Its older account/PIN format is separate from the visual simulator.
