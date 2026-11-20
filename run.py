"""Start the .NET application with this interpreter as the numerical engine."""
from pathlib import Path
import os
import shutil
import subprocess
import sys


def main(arguments=None):
    root = Path(__file__).resolve().parent
    dotnet = shutil.which('dotnet')
    if not dotnet:
        raise SystemExit('Instala el SDK .NET 10 y vuelve a iniciar Pluvia SCZ.')
    env = os.environ.copy()
    env['PLUVIA_ROOT'] = str(root)
    env['PLUVIA_PYTHON'] = sys.executable
    env.setdefault('DOTNET_CLI_HOME', str(root / 'work/dotnet-home'))
    env.setdefault('MSBuildEnableWorkloadResolver', 'false')
    print('Pluvia SCZ: http://127.0.0.1:5050 | Swagger: http://127.0.0.1:5050/swagger', flush=True)
    project = root / 'api/Pluvia.Api'
    try:
        if not (project / 'obj/project.assets.json').exists():
            restored = subprocess.call([dotnet, 'restore', str(project), '--ignore-failed-sources'], cwd=root, env=env)
            if restored:
                return restored
        return subprocess.call([dotnet, 'run', '--no-restore', '--project', str(project), '--', *(arguments or [])], cwd=root, env=env)
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
