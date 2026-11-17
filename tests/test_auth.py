import json
import time

import pytest

from flood.web import create_app

PASSWORD = 'prueba-segura-12345'
SCENARIO = {'rain_mm': 50, 'duration_h': .1, 'saturation': .5, 'drainage_mmh': 5}


def token(client):
    with client.session_transaction() as sess:
        return sess['csrf']


def login(client, username='admin', password=PASSWORD):
    client.environ_base.pop('HTTP_X_CSRF_TOKEN', None)
    client.get('/login')
    result = client.post('/login', data={'username': username, 'password': password, 'csrf_token': token(client)})
    if result.status_code == 302:
        client.environ_base['HTTP_X_CSRF_TOKEN'] = token(client)
    return result


@pytest.fixture
def app(tmp_path):
    app = create_app(runs_dir=tmp_path / 'runs', auth_dir=tmp_path / 'private')
    app.config['TESTING'] = True
    accounts = app.extensions['accounts']
    accounts.create_user('admin', 'Administrador', PASSWORD, 'admin')
    accounts.create_user('alice', 'Cliente A', PASSWORD)
    accounts.create_user('bob', 'Cliente B', PASSWORD)
    return app


def test_unauthenticated_access(app):
    client = app.test_client()
    assert client.get('/').location.endswith('/login')
    for path in ['/api/territory', '/api/runs', '/api/runs/' + 'a' * 32]:
        assert client.get(path).status_code == 401
    assert client.post('/api/simulate', json=SCENARIO).status_code == 401
    assert client.get('/admin/users').location.endswith('/login')
    assert client.get('/login').status_code == 200


def test_login_csrf_logout_revokes_replayed_cookie(app):
    client = app.test_client()
    client.get('/login')
    assert client.post('/login', data={'username': 'admin', 'password': PASSWORD}).status_code == 403
    assert login(client, password='wrong').status_code == 401
    assert login(client).status_code == 302
    page = client.get('/')
    assert page.status_code == 200 and page.headers['Cache-Control'] == 'no-store'
    cookie = client.get_cookie('pluvia_session')
    assert cookie.http_only and cookie.same_site == 'Lax'
    replay = cookie.value
    assert client.post('/logout').status_code == 302
    assert client.get('/api/runs').status_code == 401
    client.set_cookie('pluvia_session', replay)
    assert client.get('/api/runs').status_code == 401


def test_isolation_and_legacy_runs(app, tmp_path):
    alice, bob, admin = [app.test_client() for _ in range(3)]
    login(alice, 'alice'); login(bob, 'bob'); login(admin)
    result = alice.post('/api/simulate', json=SCENARIO)
    assert result.status_code == 201
    run = result.json
    assert run['owner_username'] == 'alice'
    assert len(alice.get('/api/runs').json) == 1
    assert bob.get('/api/runs').json == []
    assert bob.get('/api/runs/' + run['run_id']).status_code == 404
    assert admin.get('/api/runs/' + run['run_id']).status_code == 200
    assert alice.post('/api/simulate', json=dict(SCENARIO, owner_id=1)).status_code == 400
    path = next((tmp_path / 'runs').glob('*.json'))
    legacy = dict(run)
    del legacy['owner_id']; del legacy['owner_username']
    path.write_text(json.dumps(legacy), encoding='utf-8')
    assert alice.get('/api/runs').json == []
    assert alice.get('/api/runs/' + run['run_id']).status_code == 404
    assert len(admin.get('/api/runs').json) == 1
    path.write_text('{', encoding='utf-8')
    assert alice.get('/api/runs?include_warnings=1').json == {'runs': [], 'warnings': []}
    assert alice.get('/api/runs/' + run['run_id']).status_code == 404
    assert admin.get('/api/runs/' + run['run_id']).status_code == 422


def test_admin_permissions_and_csrf(app):
    client = app.test_client(); login(client, 'alice')
    assert client.get('/admin/users').status_code == 403
    assert client.post('/admin/users', data={'username': 'rogue', 'role': 'admin'}).status_code == 403
    assert client.post('/admin/users/1', data={'role': 'client', 'active': '0'}).status_code == 403
    assert b'/admin/users' not in client.get('/').data
    del client.environ_base['HTTP_X_CSRF_TOKEN']
    assert client.post('/api/simulate', json=SCENARIO).status_code == 403
    assert client.post('/logout').status_code == 403
    assert client.post('/account', data={}).status_code == 403
    admin = app.test_client(); login(admin)
    assert admin.get('/admin/users').status_code == 200
    del admin.environ_base['HTTP_X_CSRF_TOKEN']
    assert admin.post('/admin/users', data={}).status_code == 403
    assert admin.post('/admin/users/2', data={}).status_code == 403


def test_account_management_and_revocation(app):
    admin, alice = app.test_client(), app.test_client()
    login(admin); login(alice, 'alice')
    payload = {'username': 'new-user', 'name': 'Nueva cuenta', 'password': PASSWORD, 'role': 'client'}
    assert admin.post('/admin/users', data=payload).status_code == 302
    assert admin.post('/admin/users', data=payload).status_code == 400
    assert admin.post('/admin/users', data=dict(payload, username='short', password='short')).status_code == 400
    assert admin.post('/admin/users', data=dict(payload, username='role', role='root')).status_code == 400
    assert admin.post('/admin/users/1', data={'role': 'client', 'active': '1'}).status_code == 400
    assert admin.post('/admin/users/1', data={'role': 'admin', 'active': '0'}).status_code == 400
    assert admin.post('/admin/users/2', data={'role': 'client', 'active': '0'}).status_code == 302
    assert alice.get('/api/runs').status_code == 401
    assert login(alice, 'alice').status_code == 401
    assert admin.post('/admin/users/2', data={'role': 'client', 'active': '1', 'password': 'otra-clave-segura'}).status_code == 302
    assert login(alice, 'alice').status_code == 401
    assert login(alice, 'alice', 'otra-clave-segura').status_code == 302
    assert admin.post('/admin/users/2', data={'role': 'admin', 'active': '1'}).status_code == 302
    assert alice.get('/api/runs').status_code == 401
    assert login(alice, 'alice', 'otra-clave-segura').status_code == 302
    assert alice.get('/admin/users').status_code == 200


def test_password_change_revokes_all_sessions(app):
    one, two = app.test_client(), app.test_client()
    login(one, 'alice'); login(two, 'alice')
    payload = {'current_password': PASSWORD, 'password': 'mi-nueva-clave-segura', 'confirmation': 'mi-nueva-clave-segura'}
    assert one.post('/account', data=dict(payload, current_password='wrong')).status_code == 400
    assert one.post('/account', data=dict(payload, confirmation='mismatch')).status_code == 400
    assert one.post('/account', data=payload).status_code == 302
    assert two.get('/api/runs').status_code == 401
    assert login(one, 'alice').status_code == 401
    assert login(one, 'alice', 'mi-nueva-clave-segura').status_code == 302


def test_rate_limit(app):
    client = app.test_client()
    for _ in range(10):
        assert login(client, password='wrong').status_code == 401
    assert login(client).status_code == 429
    accounts = app.extensions['accounts']
    with accounts.connection() as db, db:
        db.execute('UPDATE attempts SET at=?', (time.time() - 901,))
    assert login(client).status_code == 302


def test_restart_expiry_and_password_storage(app, tmp_path):
    client = app.test_client(); login(client)
    cookie = client.get_cookie('pluvia_session').value
    restarted = create_app(runs_dir=tmp_path / 'runs', auth_dir=tmp_path / 'private')
    other = restarted.test_client(); other.set_cookie('pluvia_session', cookie)
    assert other.get('/api/territory').status_code == 200
    accounts = app.extensions['accounts']
    with accounts.connection() as db, db:
        stored = db.execute('SELECT password_hash FROM users LIMIT 1').fetchone()[0]
        assert stored.startswith('scrypt:') and PASSWORD not in stored
        db.execute('UPDATE sessions SET expires=?', (time.time() - 1,))
    assert other.get('/api/territory').status_code == 401


def test_first_account_is_one_time(tmp_path):
    app = create_app(runs_dir=tmp_path / 'runs', auth_dir=tmp_path / 'private')
    accounts = app.extensions['accounts']
    assert not accounts.has_users()
    accounts.create_user('admin', 'Admin', PASSWORD, 'admin', first=True)
    with pytest.raises(ValueError):
        accounts.create_user('other', 'Other', PASSWORD, 'admin', first=True)
