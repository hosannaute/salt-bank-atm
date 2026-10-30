# Salt Bank · ATM Simulator

**[▶ Open the browser demo](https://hosannaute.github.io/salt-bank-atm/)** · No download or installation needed once GitHub Pages is enabled.

For a quick tour: create a practice account, add simulated funds, then try the ATM and collect a receipt. No real banking details are needed.

A responsive ATM simulator built entirely with **HTML, CSS, and vanilla JavaScript**. No Python backend, framework, package installation, or build step is required.

- Register an account and receive a virtual debit card.
- Sign in with an eight-digit account number and four-digit practice PIN.
- Add simulated money, withdraw virtual cash, and transfer between practice accounts.
- Get transaction receipts, view history, and freeze/unfreeze your card.
- Use the dashboard on desktop or mobile.

**Simulation only.** No real money, real payment cards, or bank connections. Use a fictitious name and a practice PIN, never actual banking credentials.

## Open the app

Open `index.html` in a modern browser. Everything runs on your device. For a consistent local origin and browser storage, an optional dependency-free JavaScript server is included:

```bash
npm start
```

Open `http://127.0.0.1:8000`. Node.js 18+ is only needed for this optional server and the development tests. No `npm install` is necessary. Use `PORT=8001 npm start` to choose another port.

You can also serve this directory using a static website host, including GitHub Pages. All asset paths are relative, so repository subpaths work. Use HTTPS when hosting; browser PIN hashing requires a secure context (HTTPS, localhost, or supported local-file browsing).

## Try the simulator

1. Create an account with a name and four-digit PIN. Save the eight-digit account number displayed below your balance.
2. Add practice money. Your balance starts at ₦0; your real bank is never charged.
3. Open **ATM machine**, select an amount, and confirm with your practice PIN. Collect a virtual receipt and cash animation.
4. To try transfers, sign out, register a second account in the **same browser and site**, then sign back into the first account and send money to the second account number.
5. Under **My card**, freeze your card to block withdrawals and outgoing transfers. Incoming money is still allowed.

Withdrawals use ₦500 notes, up to ₦100,000 per transaction. Deposits and transfers accept whole naira amounts up to ₦1,000,000. History displays the latest 100 entries.

## Browser storage

Accounts and transactions persist locally in **IndexedDB**. Each tab keeps its own sign-in session in session storage for 30 minutes. Reloading retains your balance; clearing site data removes practice accounts. Accounts are not shared across devices, browser profiles, or different site addresses. Moving from a local file to a hosted website starts a separate practice bank.

PINs are salted and hashed with Web Crypto PBKDF2. This is still a client-side learning simulator: users can inspect or change their own browser data. It provides no real authentication or financial security. There is no account recovery or backend. Browser storage must be enabled.

Updates use IndexedDB read/write transactions so transfers and simultaneous withdrawals commit atomically. No financial or personal data is sent to a server.

## Development

- `index.html` — page structure and forms
- `style.css` — responsive dashboard, card, and ATM styling
- `app.js` — interface and interaction handling
- `bank.js` — browser storage, accounts, PIN checks, and transactions
- `serve.cjs` — optional static development server

Run the banking tests with Node.js:

```bash
npm test
```

Tests cover registration, hashed PINs, persistence, transfers, invalid transactions, card freezing, concurrent withdrawals, sessions, and history limits. They use an isolated in-memory storage adapter. Browser checks also exercise real IndexedDB and the desktop/mobile interface.

## Legacy terminal app

The original `salt_bank_atm.py` and `bank_data.json` are preserved as a separate legacy CLI. The website does not read or modify that data. The previous Python web server has been replaced by the browser-only implementation.

## Publish the recruiter demo

The static app is published to the `gh-pages` branch. Enable it once in [repository Pages settings](https://github.com/hosannaute/salt-bank-atm/settings/pages):

1. Under **Build and deployment**, choose **Deploy from a branch**.
2. Select **gh-pages** and **/ (root)**, then **Save**.
3. Wait for the Pages deployment to finish. The demo address is `https://hosannaute.github.io/salt-bank-atm/`.

For a prominent link on the repository home page, open the gear beside **About**, set **Website** to that address, and save.

After committing future app changes, refresh the website branch with:

```bash
npm run deploy
```

This publishes only HTML, CSS, JavaScript, the favicon, and `.nojekyll`. It preserves website branch history and excludes source tests, legacy account data, and local databases. Publishing the branch does not itself enable Pages; the repository setting above is required.
