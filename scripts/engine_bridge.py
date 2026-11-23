"""JSON over standard input/output for the .NET host. No HTTP or persistence."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    payload = json.load(sys.stdin)
    if payload.get('operation') == 'verify_legacy_password':
        from werkzeug.security import check_password_hash
        print(json.dumps({'valid': check_password_hash(payload['hash'], payload['password'])}))
        return
    from flood.simulator import Scenario, simulate
    from flood.territory import load_territory
    manifest, arrays, _ = load_territory(Path(__file__).resolve().parents[1] / 'data/pilot-v1')
    from flood.areas import fractions, summarize
    import numpy as np
    params = dict(payload['scenario'])
    prefer_ml = params.pop('prefer_ml', False)
    report = params.pop('report_polygon', None)
    intervention = params.pop('drain_polygon', None)
    rate = params.pop('local_mmh', None)
    scenario = Scenario.from_dict(params)
    weights = arrays['report_mask'].astype(float) if report is None else fractions(report, arrays['report_mask'].shape)
    drainage = None
    if intervention is not None:
        drainage = scenario.drainage_mmh + fractions(intervention, weights.shape) * (rate - scenario.drainage_mmh)
    from flood.surrogate import features, predict, predict_tree
    from flood.simulator import ENGINE_VERSION, INDEX_VERSION, index_from_max
    model_path = Path(__file__).resolve().parents[1]/'data/pilot-v1/ml/model.json'
    model = json.loads(model_path.read_text()) if prefer_ml and model_path.is_file() else {}
    reason = 'Simulador seleccionado.'
    use_ml = False
    if prefer_ml:
        if intervention is not None:
            reason = 'La intervenciÃ³n local requiere el simulador.'
        elif not model.get('active') or (model['territory'],model['simulator'],model['index']) != (manifest['version'],ENGINE_VERSION,INDEX_VERSION):
            reason = 'Sin modelo activo compatible con esta versiÃ³n.'
        elif scenario.rain_profile not in model['profiles'] or any(not lo<=getattr(scenario,k)<=hi for k,(lo,hi) in model['bounds'].items()):
            reason = 'PatrÃ³n o parÃ¡metros fuera del dominio de entrenamiento.'
        else:
            use_ml = True
            reason = 'Perfil y parÃ¡metros compatibles con el modelo evaluado.'
    if use_ml:
        matrix = features(arrays,scenario)
        values = predict_tree(matrix,model['tree']) if 'tree' in model else predict(matrix[:,:7],model['coefficients'],scenario.rain_mm)
        maximum = values.reshape(weights.shape)
        result = dict(maximum_mm=maximum,index=index_from_max(maximum),motor='ml',engine_version=model['version'])
    else:
        result = simulate(arrays['elevation_m'], arrays['infiltration_mmh'], scenario, drainage_field=drainage)
        result.update(motor='simulator',engine_version=ENGINE_VERSION)
    result['motor_reason'] = reason
    result['summary'] = summarize(result, weights)
    result['report_weights'] = weights.tolist()
    for key in ('maximum_mm', 'final_mm', 'index'):
        if key in result:
            result[key] = result[key].tolist()
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
