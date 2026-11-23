"""HTTP integration tests against the real .NET host and isolated SQLite files.

Run `dotnet build api/Pluvia.Api.Tests` before pytest. No personal database is touched.
PLUVIA_TEST_TRANSPORT=memory runs the same ASP.NET middleware/endpoints without sockets.
"""
from contextlib import contextmanager
from pathlib import Path
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import numpy as np
import pytest
from werkzeug.security import generate_password_hash
from flood.simulator import Scenario, simulate
from flood.territory import load_territory

ROOT = Path(__file__).resolve().parents[1]
BUILD_CONFIG = os.environ.get('PLUVIA_TEST_CONFIGURATION', 'Debug')
DLL = ROOT / f'api/Pluvia.Api/bin/{BUILD_CONFIG}/net10.0/Pluvia.Api.dll'
PASSWORD = 'Test-password-only-2026'
PARAMS = dict(rain_mm=50, duration_h=2, saturation=.5, drainage_mmh=5)


class Client:
    def __init__(self, base):
        self.base = base

    def call(self, method, path, data=None, token=None, expected=200, as_text=False):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = Request(self.base + path, json.dumps(data).encode() if data is not None else None, headers, method=method)
        try:
            response = urlopen(req, timeout=30)
        except HTTPError as error:
            response = error
        raw = response.read()
        self.last_headers = dict(response.headers)
        assert response.status == expected, (path, response.status, raw[:1000])
        if as_text:
            return raw.decode('utf-8-sig')
        return json.loads(raw) if raw else None

    def login(self, username='testadmin', password=PASSWORD):
        return self.call('POST', '/api/auth/login', dict(username=username, password=password))['token']


class MemoryClient(Client):
    def __init__(self, process):
        self.process = process

    def call(self, method, path, data=None, token=None, expected=200, as_text=False):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        self.process.stdin.write(json.dumps(dict(method=method, path=path, body=json.dumps(data) if data is not None else None, headers=headers)) + '\n')
        self.process.stdin.flush()
        raw = self.process.stdout.readline()
        assert raw, 'In-memory host stopped unexpectedly.'
        reply = json.loads(raw)
        self.last_headers = reply['headers']
        assert reply['status'] == expected, (path, reply)
        if as_text:
            return reply['body']
        return json.loads(reply['body']) if reply['body'] else None


@contextmanager
def server(directory, root=ROOT, migrate=False, python=None):
    assert DLL.is_file(), 'Build api/Pluvia.Api before running integration tests.'
    directory.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, PLUVIA_ROOT=str(root), PLUVIA_DATA=str(directory),
               PLUVIA_URL=f'http://127.0.0.1:{port}', PLUVIA_SKIP_IMPORT='0' if migrate else '1',
               PLUVIA_PYTHON=str(python or sys.executable), DOTNET_CLI_HOME=str(directory / 'dotnet'))
    memory = os.environ.get('PLUVIA_TEST_TRANSPORT') == 'memory'
    executable = ROOT / f'api/Pluvia.Api.Tests/bin/{BUILD_CONFIG}/net10.0/Pluvia.Api.Tests.dll' if memory else DLL
    with (directory / 'server.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen(['dotnet', str(executable)], env=env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE if memory else log, stderr=log, text=True, encoding='utf-8',
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            if not (directory / 'pluvia.sqlite3').exists() and not (migrate and (root / 'data/private/accounts.sqlite3').exists()):
                process.stdin.write(f'testadmin\nTest Administrator\n{PASSWORD}\n{PASSWORD}\n')
                process.stdin.flush()
            if memory:
                # Existing databases do not consume bootstrap input.
                while True:
                    line = process.stdout.readline()
                    if line.strip() == 'READY':
                        break
                    assert line, (directory / 'server.log').read_text(encoding='utf-8', errors='replace')
                yield MemoryClient(process)
                return
            process.stdin.close()
            client = Client(env['PLUVIA_URL'])
            last_error = None
            for _ in range(30):
                if process.poll() is not None:
                    pytest.fail((directory / 'server.log').read_text(encoding='utf-8'))
                try:
                    urlopen(client.base + '/login', timeout=.3).close()
                    break
                except (URLError, TimeoutError) as error:
                    last_error = repr(error)
                    time.sleep(.1)
            else:
                pytest.fail('API not reachable: ' + str(last_error) + '\n' + (directory / 'server.log').read_text(encoding='utf-8', errors='replace'))
            yield client
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


@pytest.fixture
def api(tmp_path):
    with server(tmp_path / 'database') as client:
        yield client


def test_swagger_auth_roles_and_session_revocation(api):
    schema = api.call('GET', '/swagger/v1/swagger.json')
    assert '/api/scenarios/{id}/simulate' in schema['paths']
    assert schema['components']['securitySchemes']['Bearer']['scheme'] == 'bearer'
    assert set(schema['components']['schemas']['ScenarioInput']['required']) == set(PARAMS)
    api.call('GET', '/api/runs', expected=401)
    api.call('POST', '/api/auth/login', dict(username='testadmin', password='bad'), expected=401)
    admin = api.login()
    user_id = api.call('POST', '/api/users', dict(username='client1', name='Client', password=PASSWORD, role='client'), admin, 201)['id']
    client = api.login('client1')
    api.call('GET', '/api/users', token=client, expected=403)
    api.call('PUT', '/api/users/1', dict(role='client', active=True), admin, 400)
    api.call('PUT', '/api/users/1', dict(role='admin'), admin, 400)
    api.call('PUT', f'/api/users/{user_id}', dict(role='client', active=False), admin, 204)
    api.call('GET', '/api/auth/me', token=client, expected=401)
    api.call('POST', '/api/auth/logout', token=admin, expected=204)
    api.call('GET', '/api/auth/me', token=admin, expected=401)


def test_strict_parameters(api):
    token = api.login()
    invalid = [{}, {k:v for k,v in PARAMS.items() if k != 'rain_mm'}, dict(PARAMS, rain_mm=True),
               dict(PARAMS, rain_mm='50'), dict(PARAMS, rain_mm=301), dict(PARAMS, extra=1),
               dict(PARAMS, duration_h=0), dict(PARAMS, saturation=None)]
    for data in invalid:
        api.call('POST', '/api/simulate', data, token, 400)
    assert api.call('GET', '/api/runs', token=token) == []


def test_simulation_history_and_immutable_snapshot(api):
    admin = api.login()
    for username in ('owner', 'other'):
        api.call('POST', '/api/users', dict(username=username, name=username, password=PASSWORD, role='client'), admin, 201)
    owner, other = api.login('owner'), api.login('other')
    scenario = api.call('POST', '/api/scenarios', dict(name='Rain', parameters=PARAMS), owner, 201)['id']
    run = api.call('POST', f'/api/scenarios/{scenario}/simulate', token=owner, expected=201)
    assert run['scenario_id'] == scenario
    _, arrays, _ = load_territory(ROOT / 'data/pilot-v1')
    reference = simulate(arrays['elevation_m'], arrays['infiltration_mmh'], Scenario(**PARAMS))
    for key in ('maximum_mm', 'final_mm', 'index'):
        np.testing.assert_array_equal(run[key], reference[key])
    assert sum(run['summary']['category_area_km2'].values()) == 16
    api.call('PUT', f'/api/scenarios/{scenario}', dict(name='Changed', parameters=dict(PARAMS, rain_mm=100)), owner)
    loaded = api.call('GET', '/api/runs/' + run['run_id'], token=owner)
    assert loaded['scenario'] == PARAMS
    assert loaded['run_id'] == run['run_id']
    assert api.call('GET', '/api/runs', token=other) == []
    assert api.call('GET', '/api/scenarios', token=other) == []
    api.call('GET', '/api/runs/' + run['run_id'], token=other, expected=404)
    api.call('POST', f'/api/scenarios/{scenario}/simulate', token=other, expected=404)
    api.call('PUT', f'/api/scenarios/{scenario}', dict(name='Attack', parameters=PARAMS), other, 404)
    assert len(api.call('GET', '/api/runs?status=completed', token=admin)) == 1


def test_password_and_restart_persistence(tmp_path):
    directory = tmp_path / 'database'
    with server(directory) as api:
        token = api.login()
        run = api.call('POST', '/api/simulate', dict(PARAMS, duration_h=.1), token, 201)
        api.call('POST', '/api/auth/password', dict(currentPassword='bad', password=PASSWORD+'!', confirmation=PASSWORD+'!'), token, 400)
        api.call('POST', '/api/auth/password', dict(currentPassword=PASSWORD, password=PASSWORD+'!', confirmation=PASSWORD+'!'), token, 204)
        api.call('GET', '/api/auth/me', token=token, expected=401)
    with server(directory) as api:
        token = api.login(password=PASSWORD+'!')
        assert api.call('GET', '/api/runs/' + run['run_id'], token=token)['maximum_mm'] == run['maximum_mm']


def test_failed_engine_recorded(tmp_path):
    with server(tmp_path / 'database', python=tmp_path / 'missing-python') as api:
        token = api.login()
        api.call('POST', '/api/simulate', PARAMS, token, 500)
        history = api.call('GET', '/api/runs?status=failed', token=token)
        assert len(history) == 1 and history[0]['error']
        assert api.call('GET', '/api/runs/' + history[0]['run_id'], token=token)['status'] == 'failed'


def test_login_throttling(api):
    for _ in range(10):
        api.call('POST', '/api/auth/login', dict(username='testadmin', password='wrong'), expected=401)
    api.call('POST', '/api/auth/login', dict(username='testadmin', password=PASSWORD), expected=429)


def test_pilot_land_cover(api):
    territory = api.call('GET', '/api/territory', token=api.login())
    source = territory['manifest']['sources']['land_cover']
    assert source['year'] == 2021 and source['classes']['0'] == 'Sin datos'
    cells = territory['geojson']['features']
    assert len(cells) == 576
    for feature in cells:
        percentages = feature['properties']['land_cover_pct']
        assert percentages.keys() <= source['classes'].keys()
        assert all(0 < value <= 100 for value in percentages.values())
        assert sum(percentages.values()) == pytest.approx(100)
    central = next(f['properties'] for f in cells if f['properties']['cell_id'] == 'UTM20S-480750-8034500')
    assert central['land_cover_pct']['50'] == pytest.approx(75.84)

    survey = territory['soilgrids']
    assert survey['territory_version'] == territory['manifest']['version']
    by_id = {cell['cell_id']: cell for cell in survey['cells']}
    assert set(by_id) == {f['properties']['cell_id'] for f in cells}
    valid = [c for c in by_id.values() if c['status'] == 'valida']
    assert len(valid) == 14 and all(c['soil_ksat_mmh'] > 0 for c in valid)
    report = [by_id[f['properties']['cell_id']] for f in cells if f['properties']['report']]
    assert len(report) == 256 and all(c['sand_pct'] is None and c['clay_pct'] is None for c in report)


def test_fractional_report_and_engine_selection(api):
    owner = api.login()
    triangle = [[8, 8], [9, 8], [8, 9]]
    params = dict(PARAMS, report_polygon=triangle, rain_profile=[70,30], prefer_ml=True)
    def run(**overrides):
        return api.call('POST', '/api/simulate', dict(params, **overrides), owner, 201)
    ml = run()
    assert ml['motor'] == 'ml' and 'ledger' not in ml
    assert ml['report_weights'][8][8] == .5
    assert sum(ml['summary']['category_area_km2'].values()) == pytest.approx(.03125)
    assert api.call('GET', '/api/runs/'+ml['run_id'], token=owner)['maximum_mm'] == ml['maximum_mm']
    local = run(drain_polygon=triangle, local_mmh=40)
    assert local['motor'] == 'simulator' and 'local' in local['motor_reason']
    assert abs(local['ledger'][-1]['residual_m3']) <= local['tolerance_m3']
    assert local['ledger'][-1]['rain_m3'] == pytest.approx(50/1000 * 36e6)
    assert run(rain_mm=250)['motor'] == 'simulator'
    assert run(rain_mm=0)['summary']['max_mm'] == 0
    api.call('POST','/api/simulate',dict(params,rain_profile=[20,20]),owner,400)
    api.call('POST','/api/simulate',dict(params,report_polygon=[[8,8],[10,10],[10,8],[8,10]]),owner,400)


def test_static_ui_and_security_headers(api):
    import re
    html = api.call('GET', '/', as_text=True)
    assert '{{' not in html and '{%' not in html
    assert 'saved-scenarios' in html and 'Consultar resultados' in html
    assert api.last_headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    for source in re.findall(r'<script src="([^"]+)"', html):
        assert api.call('GET', source, as_text=True)
    assert 'login-form' in api.call('GET', '/login', as_text=True)
    assert 'users-view' in api.call('GET', '/admin/users', as_text=True)
    assert 'swagger-ui-bundle.js' in api.call('GET', '/swagger/index.html', as_text=True)
    assert 'SwaggerUIBundle' in api.call('GET', '/swagger/index.js', as_text=True)


def test_sessions_expiry_storage_and_all_sessions_revoked(tmp_path):
    directory = tmp_path / 'database'
    with server(directory) as api:
        first, second = api.login(), api.login()
        with sqlite3.connect(directory / 'pluvia.sqlite3') as db:
            stored = [r[0] for r in db.execute('SELECT token_hash FROM sessions')]
            assert first not in stored and second not in stored
            assert PASSWORD not in db.execute('SELECT password_hash FROM users').fetchone()[0]
            db.execute('UPDATE sessions SET expires=0')
        api.call('GET', '/api/auth/me', token=first, expected=401)
        first, second = api.login(), api.login()
        api.call('POST', '/api/auth/password', dict(currentPassword=PASSWORD, password=PASSWORD+'!', confirmation=PASSWORD+'!'), first, 204)
        api.call('GET', '/api/auth/me', token=second, expected=401)


def test_legacy_import_backup_and_idempotence(tmp_path):
    with server(tmp_path / 'source') as api:
        result = api.call('POST', '/api/simulate', dict(PARAMS, duration_h=.1), api.login(), 201)
    root = tmp_path / 'legacy'
    shutil.copytree(ROOT / 'flood', root / 'flood', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT / 'scripts', root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT / 'web', root / 'web')
    shutil.copytree(ROOT / 'data/pilot-v1', root / 'data/pilot-v1')
    (root / 'data/private').mkdir()
    old = root / 'data/private/accounts.sqlite3'
    old_hash = generate_password_hash(PASSWORD)
    with sqlite3.connect(old) as db:
        db.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,name TEXT,password_hash TEXT,role TEXT,active INTEGER)')
        db.execute('INSERT INTO users VALUES(1,?,?,?,?,1)', ('testadmin', 'Legacy Admin', old_hash, 'admin'))
    runs = root / 'data/runs'
    runs.mkdir()
    raw = json.dumps(result)
    run_file = runs / ('date_' + result['run_id'] + '.json')
    run_file.write_text(raw, encoding='utf-8')
    damaged = ['{bad', '{}', '[]', json.dumps(dict(result, owner_id=True)), json.dumps(dict(result, summary={})), json.dumps(dict(result, run_id=None))]
    for index, content in enumerate(damaged):
        (runs / f'corrupt{index}.json').write_text(content, encoding='utf-8')
    directory = tmp_path / 'destination'
    for _ in range(2):
        with server(directory, root=root, migrate=True) as api:
            token = api.login()
            assert len(api.call('GET', '/api/runs', token=token)) == 1
            assert api.call('GET', '/api/runs/' + result['run_id'], token=token)['maximum_mm'] == result['maximum_mm']
            assert len(api.call('GET', '/api/runs?include_warnings=1', token=token)['warnings']) == len(damaged)
    assert run_file.read_text(encoding='utf-8') == raw
    assert len(list((directory / 'backups').glob('*/accounts.sqlite3'))) == 1
    with sqlite3.connect(old) as db:
        assert db.execute('SELECT password_hash FROM users').fetchone()[0] == old_hash
    with sqlite3.connect(directory / 'pluvia.sqlite3') as db:
        assert not db.execute('SELECT password_hash FROM users').fetchone()[0].startswith('scrypt:')
        assert db.execute("SELECT value FROM metadata WHERE key='legacy_skipped'").fetchone()[0] == str(len(damaged))


def test_scenario_crud_relationship_errors_and_persistence(tmp_path):
    directory = tmp_path / 'crud'
    with server(directory) as api:
        token = api.login()
        schema = api.call('GET', '/swagger/v1/swagger.json')
        assert {'get', 'put', 'delete'} <= schema['paths']['/api/scenarios/{id}'].keys()
        assert '409' in schema['paths']['/api/scenarios/{id}']['delete']['responses']
        assert '400' in schema['paths']['/api/runs']['post']['responses']
        for bad in ({}, {'name': ' '}, {'name': 'x', 'parameters': None},
                    {'name': 'x' * 101, 'parameters': PARAMS},
                    {'name': 'x', 'parameters': dict(PARAMS, rain_mm=301)}):
            api.call('POST', '/api/scenarios', bad, token, 400)
        scenario = api.call('POST', '/api/scenarios', dict(name='Persistente', parameters=PARAMS), token, 201)['id']
        location = api.last_headers['Location']
        assert location.endswith('/api/scenarios/' + scenario)
        assert api.call('GET', '/api/scenarios/' + scenario, token=token)['name'] == 'Persistente'
        assert api.call('GET', f'/api/scenarios/{scenario}/simulations', token=token) == []
        updated = dict(PARAMS, duration_h=.1)
        api.call('PUT', '/api/scenarios/' + scenario, dict(name='Editado', parameters=updated), token)
        assert api.call('GET', '/api/scenarios/' + scenario, token=token)['parameters'] == updated
        api.call('POST', '/api/runs', {'scenario_id': 'missing'}, token, 400)
        api.call('POST', '/api/runs', {}, token, 400)
        for method in ('GET', 'PUT', 'DELETE'):
            api.call(method, '/api/scenarios/missing', dict(name='x', parameters=PARAMS) if method == 'PUT' else None, token, 404)
        run = api.call('POST', '/api/runs', {'scenario_id': scenario}, token, 201)
        assert api.last_headers['Location'].endswith('/api/runs/' + run['run_id'])
        related = api.call('GET', f'/api/scenarios/{scenario}/simulations', token=token)
        assert [r['run_id'] for r in related] == [run['run_id']]
        api.call('DELETE', '/api/scenarios/' + scenario, token=token, expected=409)
        disposable = api.call('POST', '/api/scenarios', dict(name='Borrable', parameters=PARAMS), token, 201)['id']
        api.call('DELETE', '/api/scenarios/' + disposable, token=token, expected=204)
        api.call('GET', '/api/scenarios/' + disposable, token=token, expected=404)
    with server(directory) as api:
        token = api.login()
        assert api.call('GET', '/api/scenarios/' + scenario, token=token)['name'] == 'Editado'
        assert api.call('GET', '/api/runs/' + run['run_id'], token=token)['maximum_mm'] == run['maximum_mm']
        api.call('GET', '/api/scenarios/' + disposable, token=token, expected=404)
    with sqlite3.connect(directory / 'pluvia.sqlite3') as db:
        assert db.execute('SELECT COUNT(*) FROM __EFMigrationsHistory').fetchone()[0] == 2
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []


def test_scenario_owner_permissions(api):
    admin = api.login()
    for name in ('alice', 'bob'):
        api.call('POST', '/api/users', dict(username=name, name=name, password=PASSWORD, role='client'), admin, 201)
    alice, bob = api.login('alice'), api.login('bob')
    scenario = api.call('POST', '/api/scenarios', dict(name='Privado', parameters=PARAMS), alice, 201)['id']
    for path in (f'/api/scenarios/{scenario}', f'/api/scenarios/{scenario}/simulations'):
        api.call('GET', path, token=bob, expected=404)
    api.call('DELETE', f'/api/scenarios/{scenario}', token=bob, expected=404)
    api.call('POST', '/api/runs', {'scenario_id': scenario}, bob, 400)
    assert api.call('GET', f'/api/scenarios/{scenario}', token=admin)['name'] == 'Privado'
    api.call('DELETE', f'/api/scenarios/{scenario}', token=alice, expected=204)


def test_adopt_pre_ef_database_without_changing_existing_rows(tmp_path):
    directory = tmp_path / 'adoption'
    with server(directory) as api:
        token = api.login()
        run = api.call('POST', '/api/simulate', dict(PARAMS, duration_h=.1), token, 201)
    tables = ('users', 'sessions', 'attempts', 'scenarios', 'simulations', 'results', 'metadata')
    with sqlite3.connect(directory / 'pluvia.sqlite3') as db:
        before = {t: db.execute(f'SELECT * FROM {t} ORDER BY rowid').fetchall() for t in tables}
        db.execute('DROP TABLE __EFMigrationsHistory')
    # The previous release has the same tables, but no EF history table.
    with server(directory):
        pass
    with sqlite3.connect(directory / 'pluvia.sqlite3') as db:
        after = {t: db.execute(f'SELECT * FROM {t} ORDER BY rowid').fetchall() for t in tables}
        assert before == after
        assert db.execute('SELECT COUNT(*) FROM __EFMigrationsHistory').fetchone()[0] == 2
    backups = list((directory / 'backups').glob('before-ef-*/pluvia.sqlite3'))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as db:
        assert db.execute('SELECT payload FROM results WHERE simulation_id=?', (run['run_id'],)).fetchone()[0] == before['results'][0][1]


def test_direct_runs_keep_snapshots_without_creating_saved_scenarios(tmp_path):
    with server(tmp_path / 'direct') as api:
        token = api.login()
        runs = [api.call('POST', '/api/simulate', PARAMS, token, 201) for _ in range(2)]
        assert runs[0]['run_id'] != runs[1]['run_id']
        assert api.call('GET', '/api/scenarios', token=token) == []
        for run in runs:
            result = api.call('GET', '/api/runs/' + run['run_id'], token=token)
            assert result.get('scenario_id') is None
            assert result['scenario']['rain_mm'] == PARAMS['rain_mm']
