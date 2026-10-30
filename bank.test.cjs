const {test} = require('node:test');
const assert = require('node:assert/strict');
const {SaltBank} = require('./bank.js');
class MemoryStore {
  constructor(){ this.state = {accounts:{}, nextTransaction:1}; }
  async read(){ return structuredClone(this.state); }
  async update(change){ const copy = structuredClone(this.state); const result = change(copy); this.state = copy; return result; }
}
class Session {
  constructor(){ this.values = {}; }
  getItem(key){ return this.values[key] || null; }
  setItem(key,value){ this.values[key] = value; }
  removeItem(key){ delete this.values[key]; }
}
async function fixture(){
  const store = new MemoryStore(), session = new Session(), bank = new SaltBank(store, session);
  const user = await bank.request('register',{name:'Alex Morgan',pin:'0123'});
  return {store, session, bank, user};
}
test('registers with a virtual card and hashes a leading-zero PIN', async () => {
  const {store,bank,user} = await fixture();
  assert.match(user.id,/^[0-9]{8}$/); assert.match(user.card,/^[0-9]{4}$/); assert.equal(user.balance,0);
  assert.equal(user.pin,undefined); assert.notEqual(store.state.accounts[user.id].pin,'0123');
  await bank.request('logout'); await assert.rejects(bank.request('me'),/sign in/);
  assert.equal((await bank.request('login',{account:user.id,pin:'0123'})).id,user.id);
});
test('deposits, withdraws, and retains balances across new instances', async () => {
  const {store,session,bank} = await fixture();
  await bank.request('transaction',{kind:'deposit',amount:10000});
  await bank.request('transaction',{kind:'withdraw',amount:1500,pin:'0123'});
  const user = await new SaltBank(store,session).request('me');
  assert.equal(user.balance,8500); assert.equal(user.transactions.length,3); assert.equal(user.transactions[0].amount,-1500);
});
test('transfer updates both accounts and their histories together', async () => {
  const {bank,user} = await fixture();
  await bank.request('transaction',{kind:'deposit',amount:5000});
  const other = await bank.request('register',{name:'Recipient',pin:'5678'});
  await bank.request('login',{account:user.id,pin:'0123'});
  await bank.request('transaction',{kind:'transfer',amount:2000,target:other.id,pin:'0123'});
  assert.equal((await bank.request('me')).balance,3000);
  const received = await bank.request('login',{account:other.id,pin:'5678'});
  assert.equal(received.balance,2000); assert.equal(received.transactions[0].kind,'received');
});
test('rejects invalid amounts, recipients, PINs and overdrafts without side effects', async () => {
  const {bank,user} = await fixture();
  await bank.request('transaction',{kind:'deposit',amount:5000});
  for(const data of [
    {kind:'deposit',amount:-1},{kind:'deposit',amount:true},{kind:'deposit',amount:1.5},
    {kind:'withdraw',amount:600,pin:'0123'},{kind:'withdraw',amount:10000,pin:'0123'},
    {kind:'withdraw',amount:500,pin:'9999'},
    {kind:'transfer',amount:100,pin:'0123',target:user.id},
    {kind:'transfer',amount:100,pin:'0123',target:'00000000'}
  ]) await assert.rejects(bank.request('transaction',data));
  assert.equal((await bank.request('me')).balance,5000);
  assert.equal((await bank.request('me')).transactions.length,2);
});
test('frozen cards reject spending, accept deposits and can be unfrozen', async () => {
  const {bank} = await fixture();
  await bank.request('card',{frozen:true});
  await bank.request('transaction',{kind:'deposit',amount:1000});
  await assert.rejects(bank.request('transaction',{kind:'withdraw',amount:500,pin:'0123'}),/frozen/);
  await bank.request('card',{frozen:false});
  assert.equal((await bank.request('transaction',{kind:'withdraw',amount:500,pin:'0123'})).balance,500);
});
test('concurrent withdrawals cannot spend the same balance twice', async () => {
  const {bank} = await fixture();
  await bank.request('transaction',{kind:'deposit',amount:1000});
  const results = await Promise.allSettled([1,2].map(() => bank.request('transaction',{kind:'withdraw',amount:1000,pin:'0123'})));
  assert.equal(results.filter(result=>result.status==='fulfilled').length,1);
  assert.equal((await bank.request('me')).balance,0);
});
test('validates account creation and incorrect login', async () => {
  const {bank,user} = await fixture();
  for (const pin of ['12','abcd','１２３４',1234]) await assert.rejects(bank.request('register',{name:'User',pin}));
  await assert.rejects(bank.request('login',{account:user.id,pin:'9999'}),/incorrect/);
  await assert.rejects(bank.request('register',{name:'',pin:'1234'}));
});
test('expired sessions require login and history returns only 100 latest entries', async () => {
  const {bank,session,store,user} = await fixture();
  for(let n=0;n<110;n++) await bank.request('transaction',{kind:'deposit',amount:1});
  assert.equal((await bank.request('me')).transactions.length,100);
  assert.equal(store.state.accounts[user.id].transactions.length,111);
  session.setItem('salt-bank-session',JSON.stringify({account:user.id,expires:0}));
  await assert.rejects(bank.request('me'),/sign in/);
  await bank.request('logout');
});
