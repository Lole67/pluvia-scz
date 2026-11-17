"""Interactive recovery for someone with local access to the installation."""
from getpass import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flood.auth import Accounts


def main():
    path = Path(__file__).resolve().parents[1] / 'data/private/accounts.sqlite3'
    if not path.is_file():
        raise SystemExit('No hay cuentas. Inicia run.py para crear el primer administrador.')
    accounts = Accounts(path)
    username = input('Usuario cuya contraseña quieres restablecer: ').strip().lower()
    user = next((u for u in accounts.users() if u['username'] == username), None)
    if not user:
        raise SystemExit('Cuenta no encontrada.')
    password = getpass('Nueva contraseña (12 a 128 caracteres): ')
    if password != getpass('Repite la nueva contraseña: '):
        raise SystemExit('Las contraseñas no coinciden. No se hicieron cambios.')
    try:
        if not password:
            raise ValueError('La contraseña no puede estar vacía.')
        accounts.update_user(user['id'], user['role'], True, password)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print('Contraseña actualizada, cuenta activa y sesiones anteriores cerradas.')


if __name__ == '__main__':
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit('\nOperación cancelada.')
