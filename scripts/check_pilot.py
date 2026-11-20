"""Numerical refinement check; does not access accounts or modify dependencies."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import numpy as np
from flood.territory import load_territory
from flood.simulator import simulate, Scenario

root = Path(__file__).resolve().parents[1]
manifest, arrays, _ = load_territory(root / 'data/pilot-v1')
rows, previous = [], None
for step in (30, 15, 7.5):
    result = simulate(arrays['elevation_m'], arrays['infiltration_mmh'], Scenario(50, 2, .5, 5), dt_s=step)
    row = dict(step_s=step, max_mm=float(result['maximum_mm'].max()), residual_m3=result['ledger'][-1]['residual_m3'])
    if previous is not None:
        row['relative_l1_change'] = float(np.abs(previous-result['maximum_mm']).sum()/result['maximum_mm'].sum())
    rows.append(row)
    previous = result['maximum_mm']
print(json.dumps(dict(territory_version=manifest['version'], temporal_refinement=rows), indent=2))
