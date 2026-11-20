from export_documentation import ROOT, export

if __name__ == '__main__':
    export(ROOT / 'docs/CASOS_DE_USO.md', ROOT / 'docs/CASOS_DE_USO.pdf', diagram=True)
