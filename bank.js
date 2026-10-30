'use strict';
// All records are fictional and local to this browser. This is not a security boundary.
class BrowserBankStore {
  async open() {
    if (!this.connection) this.connection = new Promise((resolve, reject) => {
      const request = indexedDB.open('salt-bank-simulator', 1);
      request.onupgradeneeded = () => request.result.createObjectStore('bank');
      request.onsuccess = () => {
        request.result.onversionchange = () => { request.result.close(); this.connection = null; };
        resolve(request.result);
      };
      request.onerror = () => { this.connection = null; reject(new Error('Browser storage is unavailable. Allow site storage and try again.')); };
    });
    return this.connection;
  }
  async access(change) {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('bank', change ? 'readwrite' : 'readonly');
      const store = tx.objectStore('bank');
      const request = store.get('state');
      let output, failure;
      request.onsuccess = () => {
        try {
          const state = request.result || {accounts: {}, nextTransaction: 1};
          output = change ? change(state) : state;
          if (change) store.put(state, 'state');
        } catch (error) { failure = error; tx.abort(); }
      };
      tx.oncomplete = () => resolve(output);
      tx.onabort = tx.onerror = () => reject(failure || new Error('Could not save your practice data. Check available browser storage.'));
    });
  }
  read() { return this.access(); }
  update(change) { return this.access(change); }
}

class SaltBank {
  constructor(store = new BrowserBankStore(), session = sessionStorage) {
    this.store = store;
    this.session = session;
  }
  validatePin(pin) {
    if (typeof pin !== 'string' || !/^[0-9]{4}$/.test(pin)) throw new Error('Choose a PIN with exactly four digits.');
  }
  randomNumber(range) {
    const numbers = new Uint32Array(1);
    crypto.getRandomValues(numbers);
    return numbers[0] % range;
  }
  async hash(pin, salt) {
    if (!crypto.subtle) throw new Error('This browser needs HTTPS or localhost for PIN protection. Use the local JavaScript server.');
    const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(pin), 'PBKDF2', false, ['deriveBits']);
    const bits = await crypto.subtle.deriveBits({name:'PBKDF2', hash:'SHA-256', iterations:160000, salt:new TextEncoder().encode(salt)}, key, 256);
    return Array.from(new Uint8Array(bits), n => n.toString(16).padStart(2,'0')).join('');
  }
  signedIn() {
    let value;
    try { value = JSON.parse(this.session.getItem('salt-bank-session')); } catch { /* invalid local session */ }
    if (!value || value.expires <= Date.now()) {
      this.session.removeItem('salt-bank-session');
      throw new Error('Please sign in to continue.');
    }
    return value.account;
  }
  signIn(account) {
    this.session.setItem('salt-bank-session', JSON.stringify({account, expires:Date.now() + 30 * 60 * 1000}));
  }
  account(state, id) {
    if (!Object.hasOwn(state.accounts, id)) throw new Error('Please sign in to continue.');
    return state.accounts[id];
  }
  snapshot(state, id) {
    const {name, balance, card, frozen, transactions} = this.account(state, id);
    return structuredClone({id, name, balance, card, frozen, transactions:transactions.slice(-100).reverse()});
  }
  log(state, account, kind, amount, detail) {
    const id = state.nextTransaction++;
    account.transactions.push({id, kind, amount, detail, created:new Date().toISOString()});
    return id;
  }
  async request(path, data = {}) {
    if (path === 'register') {
      const {name, pin} = data;
      if (typeof name !== 'string' || name.trim().length < 2 || name.trim().length > 60) throw new Error('Enter your full name (2–60 characters).');
      this.validatePin(pin);
      const salt = Array.from(crypto.getRandomValues(new Uint8Array(16)), n => n.toString(16).padStart(2,'0')).join('');
      const hashed = await this.hash(pin, salt);
      const user = await this.store.update(state => {
        let id;
        do { id = String(10000000 + this.randomNumber(90000000)); } while (Object.hasOwn(state.accounts, id));
        const account = {name:name.trim(), salt, pin:hashed, balance:0, card:String(this.randomNumber(10000)).padStart(4,'0'), frozen:false, transactions:[]};
        state.accounts[id] = account;
        this.log(state, account, 'account', 0, 'Account opened · virtual card issued');
        return this.snapshot(state, id);
      });
      this.signIn(user.id);
      return user;
    }
    if (path === 'login') {
      this.validatePin(data.pin);
      if (typeof data.account !== 'string' || !/^[0-9]{8}$/.test(data.account)) throw new Error('Enter your 8-digit account number.');
      const state = await this.store.read();
      const account = state.accounts[data.account];
      if (!account || await this.hash(data.pin, account.salt) !== account.pin) throw new Error('Account number or PIN is incorrect. Accounts only exist in the browser where they were created.');
      this.signIn(data.account);
      return this.snapshot(state, data.account);
    }
    if (path === 'logout') {
      this.session.removeItem('salt-bank-session');
      return {ok:true};
    }
    const id = this.signedIn();
    if (path === 'me') return this.snapshot(await this.store.read(), id);
    if (path === 'card') {
      if (typeof data.frozen !== 'boolean') throw new Error('Choose a valid card state.');
      return this.store.update(state => {
        this.account(state, id).frozen = data.frozen;
        return this.snapshot(state, id);
      });
    }
    if (path !== 'transaction') throw new Error('Unknown action.');
    const {kind, amount, target} = data;
    if (!['deposit','withdraw','transfer'].includes(kind)) throw new Error('Choose a supported transaction.');
    if (!Number.isSafeInteger(amount) || amount < 1 || amount > 1000000) throw new Error('Enter a whole naira amount between ₦1 and ₦1,000,000.');
    if (kind === 'withdraw' && (amount % 500 || amount > 100000)) throw new Error('Withdraw in multiples of ₦500, up to ₦100,000 per transaction.');
    // Hash outside the IndexedDB transaction; all balance changes then commit together.
    let hashed;
    if (kind !== 'deposit') {
      this.validatePin(data.pin);
      const state = await this.store.read();
      hashed = await this.hash(data.pin, this.account(state, id).salt);
    }
    return this.store.update(state => {
      const account = this.account(state, id);
      if (kind !== 'deposit') {
        if (account.frozen) throw new Error('Your card is frozen. Unfreeze it in My card to continue.');
        if (account.pin !== hashed) throw new Error('Incorrect transaction PIN.');
        if (account.balance < amount) throw new Error('Insufficient funds. Add money to your account first.');
      }
      let detail = kind === 'deposit' ? 'Practice cash added to account' : 'ATM cash withdrawal';
      if (kind === 'transfer') {
        if (typeof target !== 'string' || !/^[0-9]{8}$/.test(target)) throw new Error('Enter an 8-digit recipient account number.');
        if (target === id) throw new Error('Choose an account other than your own.');
        if (!Object.hasOwn(state.accounts, target)) throw new Error('Recipient not found. Create another account in this same browser to try a transfer.');
        const recipient = state.accounts[target];
        if (!Number.isSafeInteger(recipient.balance + amount)) throw new Error('Recipient balance limit reached.');
        recipient.balance += amount;
        this.log(state, recipient, 'received', amount, 'From ' + account.name);
        detail = 'To ' + recipient.name;
      }
      const signed = kind === 'deposit' ? amount : -amount;
      if (!Number.isSafeInteger(account.balance + signed)) throw new Error('Practice balance limit reached.');
      account.balance += signed;
      const receipt = this.log(state, account, kind, signed, detail);
      return {...this.snapshot(state, id), receipt};
    });
  }
}

globalThis.SaltBank = SaltBank;
if (typeof module !== 'undefined') module.exports = {SaltBank};
