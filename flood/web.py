"""Web local del piloto. Escenarios y ejecuciones inmutables en archivos JSON."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from uuid import uuid4

from flask import Flask, jsonify, render_template, request
import numpy as np

from .simulator import Scenario, simulate, ENGINE_VERSION, INDEX_VERSION
from .territory import load_territory

ROOT = Path(__file__).resolve().parents[1]


def read_saved_run(file):
    """Read a saved result without repairing or deleting the original file."""
    data = json.loads(file.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('La ejecución debe ser un objeto JSON.')
    run_id = data['run_id']
    if (not isinstance(run_id, str) or len(run_id) != 32
            or any(c not in '0123456789abcdef' for c in run_id)
            or not file.name.endswith('_' + run_id + '.json')):
        raise ValueError('Identificador inconsistente.')
    datetime.fromisoformat(data['created_at'])
    Scenario.from_dict(data['scenario'])
    if isinstance(data['elapsed_s'], bool) or not math.isfinite(data['elapsed_s']) or data['elapsed_s'] < 0:
        raise ValueError('Tiempo de ejecución inválido.')
    for key in ('territory_version', 'engine_version', 'index_version'):
        if not isinstance(data[key], str) or not data[key]:
            raise ValueError('Versión ausente.')
    shape = None
    for key in ('maximum_mm', 'final_mm', 'index'):
        matrix = np.asarray(data[key], dtype=float)
        if matrix.ndim != 2 or matrix.size == 0 or not np.isfinite(matrix).all():
            raise ValueError('Matriz inválida.')
        if shape is not None and shape != matrix.shape:
            raise ValueError('Matrices incompatibles.')
        shape = matrix.shape
    numbers = [data['tolerance_m3'], data['summary']['max_mm'], data['summary']['mean_index']]
    numbers += [data['summary']['category_area_km2'][k] for k in ('baja', 'media', 'alta', 'muy_alta')]
    numbers += [data['ledger'][-1][k] for k in ('rain_m3', 'infiltration_m3', 'drainage_m3', 'stored_m3', 'residual_m3')]
    if any(isinstance(n, bool) or not math.isfinite(n) for n in numbers):
        raise ValueError('Indicadores inválidos.')
    return data


SAVED_RUN_ERRORS = (OSError, UnicodeError, ValueError, KeyError, TypeError, IndexError, OverflowError)


def create_app(data_dir=None, runs_dir=None):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 4096
    manifest, arrays, geo = load_territory(data_dir or ROOT / 'data/pilot-v1')
    output = Path(runs_dir or ROOT / 'data/runs')
    output.mkdir(parents=True, exist_ok=True)

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/api/territory')
    def territory():
        vendor = Path(app.static_folder) / 'vendor/leaflet'
        return jsonify(manifest=manifest, geojson=geo,
                       leaflet_local=all((vendor / f).is_file() for f in ('leaflet.js', 'leaflet.css')))

    @app.get('/api/runs')
    def history():
        items = []
        warnings = []
        for file in sorted(output.glob('*.json'), reverse=True):
            try:
                data = read_saved_run(file)
            except SAVED_RUN_ERRORS:
                warnings.append(file.name)
                app.logger.warning('Ejecución omitida del historial: %s', file.name)
                continue
            items.append({k: data[k] for k in ('run_id', 'created_at', 'scenario', 'elapsed_s')})
        if request.args.get('include_warnings') == '1':
            return jsonify(runs=items[:100], warnings=warnings)
        return jsonify(items[:100])

    @app.get('/api/runs/<run_id>')
    def get_run(run_id):
        if len(run_id) != 32 or any(c not in '0123456789abcdef' for c in run_id):
            return jsonify(error='Identificador inválido.'), 404
        files = list(output.glob('*_' + run_id + '.json'))
        if not files:
            return jsonify(error='Ejecución no encontrada.'), 404
        try:
            data = read_saved_run(files[0])
        except SAVED_RUN_ERRORS:
            return jsonify(error='La ejecución guardada está dañada o incompleta. El archivo se conserva para revisión.'), 422
        return jsonify(data)

    @app.post('/api/simulate')
    def run():
        try:
            scenario = Scenario.from_dict(request.get_json(silent=True))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        started = time.perf_counter()
        result = simulate(arrays['elevation_m'], arrays['infiltration_mmh'], scenario)
        elapsed = time.perf_counter() - started
        mask = arrays['report_mask'].astype(bool)
        peak = result['maximum_mm'][mask]
        index = result['index'][mask]
        categories = {'baja': float(np.count_nonzero(index < 25) * .0625),
                      'media': float(np.count_nonzero((index >= 25) & (index < 50)) * .0625),
                      'alta': float(np.count_nonzero((index >= 50) & (index < 75)) * .0625),
                      'muy_alta': float(np.count_nonzero(index >= 75) * .0625)}
        now = datetime.now(timezone.utc)
        data = {'run_id': uuid4().hex, 'scenario_id': uuid4().hex,
                'created_at': now.isoformat(), 'scenario': asdict(scenario),
                'territory_version': manifest['version'], 'engine_version': ENGINE_VERSION,
                'index_version': INDEX_VERSION, 'elapsed_s': elapsed,
                'rain_pattern': 'constant', 'boundary': 'closed', 'mobility_m2_s': 20,
                'window': 'duración de lluvia; sin recesión', 'seed': None,
                'area': 'zona piloto fija, reporte central de 16 km²',
                'maximum_mm': result['maximum_mm'].tolist(),
                'final_mm': result['final_mm'].tolist(), 'index': result['index'].tolist(),
                'ledger': result['ledger'], 'step_s': result['step_s'], 'steps': result['steps'],
                'tolerance_m3': result['tolerance_m3'],
                'summary': {'max_mm': float(peak.max()), 'mean_max_mm': float(peak.mean()),
                            'mean_index': float(index.mean()), 'category_area_km2': categories},
                'sources': manifest['sources'], 'warnings': manifest['warnings']}
        text = json.dumps(data, ensure_ascii=False, allow_nan=False)
        filename = now.strftime('%Y%m%dT%H%M%S%f') + '_' + data['run_id'] + '.json'
        # Nombre único, publicación atómica: nunca sustituye una ejecución previa.
        temporary = output / (filename + '.tmp')
        temporary.write_text(text, encoding='utf-8')
        temporary.rename(output / filename)
        return app.response_class(text, status=201, mimetype='application/json')

    return app
