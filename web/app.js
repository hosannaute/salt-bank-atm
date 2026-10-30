'use strict';
const $ = (s) => document.querySelector(s);
const money = (n) => '₦' + Number(n).toLocaleString('en-NG', {minimumFractionDigits:2,maximumFractionDigits:2});
let user, mode = 'register', currentView = 'overview', action, balanceHidden = false, busy = false, toastTimer;
const names = {deposit:'Money added',withdraw:'Cash withdrawal',transfer:'Transfer sent',received:'Transfer received',account:'Welcome to Salt Bank'};
const icons = {deposit:'↓',withdraw:'↗',transfer:'⇄',received:'↙',account:'✳'};
async function api(path, data) {
  const response = await fetch('/api/' + path, {method:data === undefined ? 'GET' : 'POST', headers:data === undefined ? {} : {'Content-Type':'application/json'}, body:data === undefined ? undefined : JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Something went wrong. Please try again.');
  return result;
}
function toast(message) { $('#toast').textContent = message; $('#toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').hidden = true, 3500); }
function authMode(next) {
  mode = next; const register = mode === 'register';
  $('#register-tab').classList.toggle('active',register); $('#login-tab').classList.toggle('active',!register);
  $('#name-field').hidden = !register; $('#name-field input').disabled = !register;
  $('#account-field').hidden = register; $('#account-field input').disabled = register; $('#account-field input').required = !register;
  $('#auth-title').textContent = register ? 'Welcome to your everyday bank.' : 'Good to have you back.';
  $('#auth-subtitle').textContent = register ? 'A fresh start. A card with your name on it.' : 'Your account number and practice PIN are all you need.';
  $('#auth-submit').textContent = register ? 'Open my account ↗' : 'Sign in securely ↗';
  $('#auth-form input[name="pin"]').autocomplete = register ? 'new-password' : 'current-password';
  $('#auth-error').textContent = '';
}
$('#register-tab').onclick = () => authMode('register'); $('#login-tab').onclick = () => authMode('login');
$('#auth-form').onsubmit = async (event) => {
  event.preventDefault(); $('#auth-submit').disabled = true; $('#auth-error').textContent = '';
  try { user = await api(mode, Object.fromEntries(new FormData(event.target))); event.target.reset(); showApp(); if(mode === 'register') toast('Account opened! Your virtual card is ready. Save your account number to sign in again.'); }
  catch(error) { $('#auth-error').textContent = error.message; }
  finally { $('#auth-submit').disabled = false; }
};
function showApp() { $('#auth').hidden = true; $('#app').hidden = false; render(); setView('overview'); }
function render() {
  const name = user.name.split(' ')[0];
  $('#avatar').textContent = name.slice(0,1).toUpperCase(); $('#avatar').title = user.name;
  $('#account-number').textContent = user.id;
  $('#balance').replaceChildren();
  if(balanceHidden) $('#balance').textContent = '₦ ••••••';
  else { const [whole, fraction] = money(user.balance).split('.'); $('#balance').append(document.createTextNode(whole)); const small = document.createElement('span'); small.textContent = '.' + fraction; $('#balance').append(small); }
  document.querySelectorAll('.card-tail').forEach(el => el.textContent = user.card);
  document.querySelectorAll('.card-holder').forEach(el => el.textContent = user.name);
  $('#card-status').textContent = user.frozen ? 'Card frozen' : 'Card active';
  $('#freeze-card').textContent = user.frozen ? 'Unfreeze card' : 'Freeze card';
  $('#atm-greeting').textContent = `Ready for some cash, ${name}?`;
  const history = currentView === 'activity' ? user.transactions : user.transactions.slice(0,5);
  const tbody = $('#transactions'); tbody.replaceChildren();
  history.forEach(item => {
    const row = document.createElement('tr');
    const title = document.createElement('td'), layout = document.createElement('div'), icon = document.createElement('span'), text = document.createElement('div'), b = document.createElement('b'), small = document.createElement('small');
    layout.className = 'transaction-name'; icon.className = 'transaction-icon'; icon.textContent = icons[item.kind] || '↔'; b.textContent = names[item.kind] || item.kind; small.textContent = item.detail; text.append(b,small); layout.append(icon,text); title.append(layout);
    const date = document.createElement('td'); date.textContent = new Date(item.created).toLocaleDateString('en-NG',{day:'numeric',month:'short'});
    const status = document.createElement('td'), badge = document.createElement('span'); badge.className = 'badge'; badge.textContent = 'Completed'; status.append(badge);
    const amount = document.createElement('td'); amount.textContent = item.amount === 0 ? '—' : (item.amount > 0 ? '+' : '−') + money(Math.abs(item.amount)); if(item.amount > 0) amount.className = 'positive';
    row.append(title,date,status,amount); tbody.append(row);
  });
  $('#empty-state').hidden = history.length > 0;
  $('.table-wrap').hidden = history.length === 0;
  $('#activity-limit').hidden = currentView !== 'activity' || user.transactions.length < 100;
}
function setView(view) {
  currentView = view;
  const titles = {overview:['Your money, at a glance.','A good day to make your next move.'],atm:['Your next move starts here.','A familiar experience. A little more confidence.'],card:['Meet your everyday card.','Made for your practice journey.'],activity:['Every move, remembered.','Follow your deposits, withdrawals, and transfers.']};
  document.querySelectorAll('.view').forEach(el => el.hidden = true);
  if(view === 'activity') {
    $('#overview-view').hidden = false; $('.balance-panel').hidden = true; $('.card-panel').hidden = true; $('.quick-panel').hidden = true;
    $('.dashboard-grid').style.gridTemplateColumns = 'minmax(0,1fr)'; $('#activity-title').textContent = 'Transaction history'; $('#all-activity').hidden = true;
  } else {
    $('#' + view + '-view').hidden = false; $('.balance-panel').hidden = false; $('.card-panel').hidden = false; $('.quick-panel').hidden = false;
    $('.dashboard-grid').style.gridTemplateColumns = ''; $('#activity-title').textContent = 'Recent activity'; $('#all-activity').hidden = false;
  }
  $('#page-title').textContent = titles[view][0]; $('#page-subtitle').textContent = titles[view][1];
  $('#crumb').textContent = {overview:'Overview',atm:'ATM machine',card:'My card',activity:'Transactions'}[view];
  document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active',el.dataset.view === view));
  render();
}
$('#balance-visibility').onclick = () => { balanceHidden = !balanceHidden; $('#balance-visibility').setAttribute('aria-label', balanceHidden ? 'Show balance' : 'Hide balance'); render(); };
$('#copy-account').onclick = async () => { try { await navigator.clipboard.writeText(user.id); toast('Account number copied.'); } catch { toast('Your account number: ' + user.id); } };
$('#logout').onclick = async () => { try { await api('logout',{}); user = null; $('#app').hidden = true; $('#auth').hidden = false; $('#auth-form').reset(); balanceHidden = false; authMode('login'); } catch(error) { toast(error.message); } };
$('#freeze-card').onclick = async () => { $('#freeze-card').disabled = true; try { user = await api('card',{frozen:!user.frozen}); render(); toast(user.frozen ? 'Card frozen. Withdrawals and transfers are paused.' : 'Card unfrozen. You’re ready to go.'); } catch(error) { toast(error.message); } finally { $('#freeze-card').disabled = false; } };
function openTransaction(kind, amount) {
  if(busy) return;
  action = kind; const form = $('#transaction-form'); form.reset();
  $('#transaction-entry').hidden = false; $('#transaction-success').hidden = true; $('#transaction-error').textContent = '';
  $('#dialog-title').textContent = {deposit:'A little boost to your balance.',withdraw:'Let’s get you some cash.',transfer:'Send a little something.'}[kind];
  $('#dialog-icon').textContent = icons[kind];
  $('#dialog-description').textContent = {deposit:'Add simulated money. Your real bank is never charged.',withdraw:'Choose multiples of ₦500, up to ₦100,000.',transfer:'Send practice money to another Salt Bank simulator account.'}[kind];
  $('#recipient-label').hidden = kind !== 'transfer'; form.elements.target.required = kind === 'transfer'; form.elements.target.disabled = kind !== 'transfer';
  $('#transaction-pin').hidden = kind === 'deposit'; form.elements.pin.required = kind !== 'deposit'; form.elements.pin.disabled = kind === 'deposit';
  form.elements.amount.step = kind === 'withdraw' ? '500' : '1'; form.elements.amount.min = kind === 'withdraw' ? '500' : '1'; form.elements.amount.max = kind === 'withdraw' ? '100000' : '1000000';
  if(amount) form.elements.amount.value = amount;
  $('#transaction-submit').textContent = {deposit:'Add practice money ↗',withdraw:'Confirm withdrawal ↗',transfer:'Confirm transfer ↗'}[kind];
  $('#transaction-dialog').showModal();
  (kind === 'transfer' ? form.elements.target : form.elements.amount).focus();
}
document.addEventListener('click', event => {
  const target = event.target.closest('button'); if(!target) return;
  if(target.dataset.view) setView(target.dataset.view);
  if(target.dataset.action) openTransaction(target.dataset.action);
  if(target.dataset.cash) openTransaction('withdraw',target.dataset.cash);
  if(target.dataset.amount) $('#transaction-form').elements.amount.value = target.dataset.amount;
  if(target.classList.contains('close') && !busy) $('#transaction-dialog').close();
});
$('#transaction-dialog').addEventListener('cancel',event => { if(busy) event.preventDefault(); });
$('#transaction-form').onsubmit = async event => {
  event.preventDefault(); if(busy || !$('#transaction-success').hidden) return; busy = true;
  const submit = $('#transaction-submit'); submit.disabled = true; submit.textContent = 'Processing…';
  $('#transaction-error').textContent = '';
  const values = Object.fromEntries(new FormData(event.target)); const amount = Number(values.amount);
  try {
    user = await api('transaction',{kind:action,amount,pin:values.pin,target:values.target});
    render(); $('#transaction-entry').hidden = true; $('#transaction-success').hidden = false;
    $('#success-title').textContent = {deposit:'Balance, boosted.',withdraw:'Cash collected.',transfer:'On its way. Already there.'}[action];
    $('#success-message').textContent = action === 'withdraw' ? `${amount/500} virtual ₦500 notes dispensed. Don’t forget your card!` : action === 'deposit' ? 'Your practice money is ready to use.' : 'The recipient’s simulator balance has been updated.';
    $('#cash-notes').hidden = action !== 'withdraw'; $('#receipt-id').textContent = 'SLT-' + String(user.receipt).padStart(6,'0'); $('#receipt-amount').textContent = money(amount); $('#receipt-balance').textContent = money(user.balance);
    $('#transaction-success .close').focus();
    event.target.elements.pin.value = '';
  } catch(error) { $('#transaction-error').textContent = error.message; }
  finally { busy = false; submit.disabled = false; submit.textContent = {deposit:'Add practice money ↗',withdraw:'Confirm withdrawal ↗',transfer:'Confirm transfer ↗'}[action]; }
};
$('#date-label').textContent = new Date().toLocaleDateString('en-NG',{weekday:'long',day:'numeric',month:'long',year:'numeric'}).toUpperCase();
$('#year').textContent = new Date().getFullYear();
(async () => { try { user = await api('me'); showApp(); } catch { $('#auth').hidden = false; } })();
