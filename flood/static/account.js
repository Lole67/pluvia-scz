'use strict';
const byId = id => document.getElementById(id);
const request = (url, options) => PluviaSession.request(url, options);
const json = (method, body) => ({method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
function message(text, error = false) { byId('message').textContent = text; byId('message').className = error ? 'form-error' : ''; }
function bindForm(id, handler) {
  byId(id).addEventListener('submit', async event => {
    event.preventDefault(); const form = event.currentTarget, button = form.querySelector('button');
    button.disabled = true; message('Procesando…');
    try { await handler(Object.fromEntries(new FormData(form)), form); }
    catch (error) { message(error.message, true); }
    finally { button.disabled = false; }
  });
}
bindForm('login-form', async data => {
  const result = await request('/api/auth/login', json('POST', data));
  sessionStorage.setItem('pluvia-token', result.token); location.replace('/');
});
bindForm('password-form', async data => {
  await request('/api/auth/password', json('POST', data));
  sessionStorage.removeItem('pluvia-token'); location.replace('/login?password=changed');
});
bindForm('create-form', async (data, form) => {
  await request('/api/users', json('POST', data)); form.reset(); await users(); message('Usuario creado.');
});
async function users() {
  const data = await request('/api/users'); byId('user-list').replaceChildren();
  data.forEach(user => {
    const form = document.createElement('form'); form.className = 'user-row';
    const name = document.createElement('div'); name.textContent = `${user.name} (${user.username})`;
    function field(label, element) { const wrapper = document.createElement('label'); wrapper.append(document.createTextNode(label), element); return wrapper; }
    const role = document.createElement('select'); role.add(new Option('Cliente','client')); role.add(new Option('Administrador','admin')); role.value = user.role;
    const state = document.createElement('select'); state.add(new Option('Activa','1')); state.add(new Option('Desactivada','0')); state.value = String(user.active);
    const password = document.createElement('input'); password.type = 'password'; password.minLength = 12; password.maxLength = 128; password.autocomplete = 'new-password'; password.placeholder = 'Sin cambiar';
    const save = document.createElement('button'); save.type = 'submit'; save.textContent = 'Guardar';
    form.append(name,field('Rol',role),field('Estado',state),field('Restablecer contraseña',password),save);
    form.addEventListener('submit', async event => {
      event.preventDefault(); save.disabled = true;
      try { await request(`/api/users/${user.id}`,json('PUT',{role:role.value,active:state.value==='1',password:password.value || null})); await PluviaSession.requireUser(); await users(); message('Cuenta actualizada.'); }
      catch (error) { message(error.message,true); } finally { save.disabled = false; }
    });
    byId('user-list').append(form);
  });
}
(async () => {
  if (location.pathname === '/login') {
    byId('login-view').hidden = false;
    if (new URLSearchParams(location.search).get('password') === 'changed') message('Contraseña actualizada. Inicia sesión nuevamente.');
    return;
  }
  try {
    const user = await PluviaSession.requireUser(); byId('account-nav').hidden = false;
    if (location.pathname === '/admin/users') {
      if (user.role !== 'admin') throw Error('Se requiere una cuenta administradora.');
      byId('account-main').classList.add('users-main'); byId('users-view').hidden = false; await users();
    } else byId('password-view').hidden = false;
  } catch (error) { message(error.message,true); }
})();
