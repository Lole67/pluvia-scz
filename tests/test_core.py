import numpy as np
import pytest
from flood.simulator import Scenario, simulate
from flood.web import create_app

def scenario(rain=50, saturation=0, drainage=0):
    return Scenario(rain, 2, saturation, drainage)

def test_dry_domain():
    r=simulate(np.arange(16).reshape(4,4),5,scenario(0))
    assert np.array_equal(r['maximum_mm'],np.zeros((4,4)))

def test_flat_analytic_balance_and_exact_rain():
    r=simulate(np.zeros((4,4)),5,scenario(50,0,5),dt_s=37)
    np.testing.assert_allclose(r['final_mm'],30,atol=1e-10)
    assert r['ledger'][-1]['rain_m3']==pytest.approx(50000)
    assert max(abs(x['residual_m3']) for x in r['ledger']) < r['tolerance_m3']

def test_sinks_cannot_overdraw():
    r=simulate(np.zeros((3,3)),100,scenario(1,0,100))
    np.testing.assert_allclose(r['final_mm'],0,atol=1e-12)
    assert r['ledger'][-1]['infiltration_m3']+r['ledger'][-1]['drainage_m3']==pytest.approx(562.5)

def test_downhill_transfer_and_depression():
    z=np.ones((5,5));z[2,2]=0
    r=simulate(z,0,scenario(10))
    assert r['final_mm'][2,2] > 10
    assert r['final_mm'].min() >= -1e-8
    assert r['final_mm'].sum()==pytest.approx(250)
    assert np.all(r['maximum_mm'] >= r['final_mm']-1e-10)

def test_flat_monotonic_and_repeatable():
    z=np.zeros((3,3))
    low=simulate(z,5,scenario(20))
    high=simulate(z,5,scenario(40))
    drained=simulate(z,5,scenario(40,0,10))
    saturated=simulate(z,5,scenario(40,1))
    assert np.all(high['maximum_mm'] >= low['maximum_mm'])
    assert np.all(drained['maximum_mm'] <= high['maximum_mm'])
    assert np.all(saturated['maximum_mm'] >= high['maximum_mm'])
    np.testing.assert_array_equal(high['maximum_mm'],simulate(z,5,scenario(40))['maximum_mm'])

@pytest.mark.parametrize('bad',[{}, {'rain_mm':True}, {'rain_mm':float('nan')}, {'extra':2}])
def test_invalid_inputs(bad):
    with pytest.raises(ValueError):Scenario.from_dict(bad)

def test_web_roundtrip_and_restart(tmp_path):
    app=create_app(runs_dir=tmp_path);client=app.test_client()
    assert client.get('/').status_code==200
    for asset in ['/static/app.js','/static/style.css','/api/territory']:
        assert client.get(asset).status_code==200
    assert client.post('/api/simulate',json={}).status_code==400
    config={'rain_mm':50,'duration_h':2,'saturation':.5,'drainage_mmh':5}
    first=client.post('/api/simulate',json=config)
    assert first.status_code==201
    d=first.get_json();assert np.asarray(d['maximum_mm']).shape==(24,24)
    assert sum(d['summary']['category_area_km2'].values())==16
    second=client.post('/api/simulate',json=config).get_json()
    assert d['run_id']!=second['run_id'] and d['scenario_id']!=second['scenario_id']
    assert d['maximum_mm']==second['maximum_mm']
    restarted=create_app(runs_dir=tmp_path).test_client()
    assert restarted.get('/api/runs/'+d['run_id']).get_json()==d
    assert len(restarted.get('/api/runs').get_json())==2
    assert restarted.get('/api/runs/not-a-run').status_code==404

def test_real_grid_and_temporal_refinement():
    from flood.territory import load_territory
    from flood.web import ROOT
    m,a,g=load_territory(ROOT/'data/pilot-v1')
    assert m['cell_m']==250 and len(g['features'])==576
    assert a['report_mask'].sum()==256
    assert g['features'][0]['geometry']['coordinates'][0][0][1]>g['features'][-1]['geometry']['coordinates'][0][0][1]
    r30=simulate(a['elevation_m'],a['infiltration_mmh'],scenario(),dt_s=30)
    r15=simulate(a['elevation_m'],a['infiltration_mmh'],scenario(),dt_s=15)
    # Pilot criterion: aggregate maximum error under 5% on step halving.
    error=np.abs(r30['maximum_mm']-r15['maximum_mm']).sum()/r15['maximum_mm'].sum()
    assert error<.05
    assert abs(r30['ledger'][-1]['residual_m3'])<r30['tolerance_m3']
