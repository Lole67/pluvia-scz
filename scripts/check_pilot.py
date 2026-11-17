"""Evidencia reproducible del piloto; no valida inundaciones observadas."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import importlib.metadata
from getpass import getpass
import numpy as np
from flood.territory import load_territory
from flood.simulator import simulate, Scenario
from flood.web import create_app, ROOT

m,a,g=load_territory(ROOT/'data/pilot-v1')
client=create_app().test_client()
client.get('/login')
with client.session_transaction() as session:
    csrf = session['csrf']
response = client.post('/login', data={'username': input('Usuario para guardar las pruebas: '),
                                     'password': getpass('Contraseña: '), 'csrf_token': csrf})
if response.status_code != 302:
    raise SystemExit('No se pudo iniciar sesión. Inicia run.py para configurar una cuenta.')
with client.session_transaction() as session:
    client.environ_base['HTTP_X_CSRF_TOKEN'] = session['csrf']
examples=[]
for rain in (50,100):
    r=client.post('/api/simulate',json={'rain_mm':rain,'duration_h':2,'saturation':.5,'drainage_mmh':5})
    if r.status_code != 201: raise RuntimeError(r.get_data(as_text=True))
    d=r.get_json()
    examples.append({k:d[k] for k in ('run_id','scenario','summary','elapsed_s')})
refinement=[]
previous=None
for dt in (30,15,7.5):
    r=simulate(a['elevation_m'],a['infiltration_mmh'],Scenario(50,2,.5,5),dt_s=dt)
    row={'step_s':dt,'max_mm':float(r['maximum_mm'].max()),
         'balance_residual_m3':r['ledger'][-1]['residual_m3']}
    if previous is not None:
        row['relative_l1_change']=float(np.abs(previous-r['maximum_mm']).sum()/r['maximum_mm'].sum())
    refinement.append(row);previous=r['maximum_mm']
packages=['Flask','numpy','rasterio','pyproj','pytest']
versions={p:importlib.metadata.version(p) for p in packages}
(ROOT/'requirements.txt').write_text(''.join(f'{p}=={v}\n' for p,v in versions.items()),encoding='utf-8')
report={'date':'2026-11-03','territory_version':m['version'],'examples':examples,
        'temporal_refinement':refinement,'dependencies':versions,
        'verification':'API y cálculo comprobados; navegador pendiente. Sin validación observacional.'}
(ROOT/'VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
