"""Build a source ZIP from an explicit allowlist, excluding local/private artifacts."""
from pathlib import Path
import hashlib
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'bin', 'obj', '.vs', '.git', '__pycache__', '.pytest_cache', '.venv', 'work', 'private', 'runs', 'raw', 'backups'}


def project_files():
    names = {'.gitignore', 'INICIAR.cmd', 'start.ps1', 'run.py', 'README.md', 'DATA_SOURCES.md', 'requirements.txt', 'dependencies.lock.txt'}
    for directory in ('api', 'flood', 'web', 'scripts', 'tests', 'data/pilot-v1'):
        for path in (ROOT / directory).rglob('*'):
            if path.is_file() and not EXCLUDED.intersection(path.relative_to(ROOT).parts):
                names.add(path.relative_to(ROOT).as_posix())
    for name in ('PLUVIA_SCZ_SPRINT_1.md', 'PLUVIA_SCZ_SPRINT_1.pdf', 'CASOS_DE_USO.md',
                 'CASOS_DE_USO.pdf', 'CASOS_DE_USO.puml', 'ACCESO_Y_ROLES.md'):
        names.add('docs/' + name)
    for name in sorted(names):
        path = ROOT / name
        if path.suffix.lower() in {'.sqlite', '.sqlite3', '.db', '.pyc', '.log', '.exe', '.dll', '.pdb', '.key', '.pem'}:
            raise ValueError(f'Archivo no distribuible: {name}')
        if path.suffix.lower() in {'.cs', '.py', '.js', '.html', '.md', '.json', '.txt', '.csproj', '.ps1', '.cmd'}:
            text = path.read_text(encoding='utf-8-sig')
            if re.search(r'C:[\\/]Users[\\/]|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9]+|-----BEGIN [A-Z ]*PRIVATE KEY-----', text):
                raise ValueError(f'Revisar información local o credenciales: {name}')
        yield path


def main():
    destination = ROOT / 'work/distribution/pluvia-scz.zip'
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = list(project_files())
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, 'pluvia-scz/' + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
    print(destination)
    print(f'{len(files)} archivos; SHA256: {hashlib.sha256(destination.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    main()
