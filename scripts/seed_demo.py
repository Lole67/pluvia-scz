"""Create named synthetic scenarios through the API; no credentials are stored."""
import argparse
import getpass
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:5050')
    args = parser.parse_args()
    token = None

    def call(method, path, body=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        request = Request(args.url.rstrip('/') + path,
                          json.dumps(body).encode() if body is not None else None,
                          headers=headers, method=method)
        with urlopen(request, timeout=180) as response:
            raw = response.read()
            return json.loads(raw) if raw else None

    try:
        token = call('POST', '/api/auth/login', {
            'username': input('Usuario de Pluvia: '),
            'password': getpass.getpass('Contraseña de Pluvia: '),
        })['token']
        existing = {s['name']: s['id'] for s in call('GET', '/api/scenarios')}
        for name, rain in [('Demo - lluvia 50 mm', 50), ('Demo - lluvia 100 mm', 100)]:
            if name in existing:
                print(name + ': ya existe; no se modifica.')
                continue
            result = call('POST', '/api/scenarios', {
                'name': name,
                'parameters': {'rain_mm': rain, 'duration_h': 2, 'saturation': .5, 'drainage_mmh': 5},
            })
            print(name + ': ' + result['id'])
    except HTTPError as error:
        raise SystemExit(f'HTTP {error.code}: {error.read().decode("utf-8")}')
    except URLError:
        raise SystemExit('No se pudo conectar. Inicia Pluvia antes de cargar los escenarios.')
    finally:
        if token:
            call('POST', '/api/auth/logout')


if __name__ == '__main__':
    main()
