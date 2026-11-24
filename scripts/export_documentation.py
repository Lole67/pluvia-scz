"""Imprime las fuentes HTML autocontenidas de docs/fuentes como PDF."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def browser():
    for name in ("msedge", "google-chrome", "chromium", "chromium-browser"):
        executable = shutil.which(name)
        if executable:
            return executable
    for variable in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        directory = os.environ.get(variable)
        if directory:
            for suffix in ("Microsoft/Edge/Application/msedge.exe", "Google/Chrome/Application/chrome.exe"):
                candidate = Path(directory) / suffix
                if candidate.is_file():
                    return str(candidate)
    raise SystemExit("Para exportar los PDF se necesita Edge, Chrome o Chromium.")


def export(source):
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / (source.stem + ".pdf")
        subprocess.run([
            browser(), "--headless", "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
            f"--user-data-dir={Path(temp) / 'perfil'}", f"--print-to-pdf={output}", source.as_uri(),
        ], check=True)
        if not output.is_file() or not output.stat().st_size:
            raise RuntimeError(f"No se generó el PDF de {source.name}.")
        target = DOCS / output.name
        shutil.copyfile(output, target)
        print(target)


if __name__ == "__main__":
    for source in sorted((DOCS / "fuentes").glob("*.html")):
        export(source)
