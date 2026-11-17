from flood.web import create_app
from getpass import getpass

if __name__ == '__main__':
    app = create_app()
    accounts = app.extensions['accounts']
    if not accounts.has_users():
        print('Pluvia SCZ: crea la primera cuenta administradora.')
        try:
            while not accounts.has_users():
                username = input('Usuario: ')
                name = input('Nombre: ')
                password = getpass('Contraseña (12 a 128 caracteres; no se muestra): ')
                confirmation = getpass('Repite la contraseña: ')
                if password != confirmation:
                    print('Las contraseñas no coinciden.')
                    continue
                try:
                    accounts.create_user(username, name, password, 'admin', first=True)
                except ValueError as exc:
                    print(exc)
        except (EOFError, KeyboardInterrupt):
            raise SystemExit('\nCreación cancelada. No se inició el servidor.')
    app.run(host='127.0.0.1', port=5050, debug=False)
