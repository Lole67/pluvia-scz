"""Start the .NET application with this interpreter as the numerical engine."""
from pathlib import Path
import os
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET


def needs_restore(project):
    """Also restore when an update changes NuGet references in an existing checkout."""
    try:
        assets = json.loads((project / 'obj/project.assets.json').read_text(encoding='utf-8-sig'))
        references = ET.parse(project / 'Pluvia.Api.csproj').findall('.//PackageReference')
        return any(f"{p.attrib['Include']}/{p.attrib['Version']}" not in assets['libraries'] for p in references)
    except (OSError, ValueError, KeyError):
        return True


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
        if needs_restore(project):
            restored = subprocess.call([dotnet, 'restore', str(project), '--ignore-failed-sources'], cwd=root, env=env)
            if restored:
                return restored
        return subprocess.call([dotnet, 'run', '--no-restore', '--project', str(project), '--', *(arguments or [])], cwd=root, env=env)
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
