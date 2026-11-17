"""Diagnóstico de sensibilidad del piloto, no calibración observacional."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from flood.simulator import simulate,Scenario
from flood.territory import load_territory
root=Path(__file__).resolve().parents[1]
m,a,_=load_territory(root/'data/pilot-v1')
scenario=Scenario(50,2,.5,5)
base=simulate(a['elevation_m'],a['infiltration_mmh'],scenario)
report=base['maximum_mm'][4:-4,4:-4]
records=[]
for mobility in [5,10,20]:
    r=simulate(a['elevation_m'],a['infiltration_mmh'],scenario,mobility_m2_s=mobility)
    values=r['maximum_mm'][4:-4,4:-4]
    records.append({'mobility_m2_s':mobility,'report_max_mm':float(values.max()),
                    'relative_l1_to_base':float(np.abs(values-report).sum()/report.sum()),
                    'domain_max_mm':float(r['maximum_mm'].max())})
cropped=simulate(a['elevation_m'][2:-2,2:-2],a['infiltration_mmh'][2:-2,2:-2],scenario)
same_report=cropped['maximum_mm'][2:-2,2:-2]
b=base['ledger'][-1]
result={'date':'2026-11-03','scenario':vars(scenario),'mobility_sensitivity':records,
        'boundary_test':{'description':'Mismo reporte 4x4 km; margen de 500 m contra 1000 m; ambos bordes cerrados. No demuestra independencia de un dominio mayor.',
                         'relative_l1_change':float(np.abs(same_report-report).sum()/report.sum()),
                         'report_max_mm_500m_margin':float(same_report.max())},
        'mass_residual_m3':b['residual_m3'],
        'interpretation':'Máximos sensibles a conductancia sintética y borde. No usar como profundidad real. No entrenar aún etiquetas definitivas ni afirmar validación hidráulica.'}
(root/'SENSITIVITY.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
