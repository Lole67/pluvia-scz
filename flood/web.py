"""Web local del piloto. Escenarios y ejecuciones inmutables en archivos JSON."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from uuid import uuid4

from flask import Flask, jsonify, render_template, request
import numpy as np

from .simulator import Scenario, simulate, ENGINE_VERSION, INDEX_VERSION
from .territory import load_territory

ROOT = Path(__file__).resolve().parents[1]


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
        for file in sorted(output.glob('*.json'), reverse=True):
            data = json.loads(file.read_text(encoding='utf-8'))
            items.append({k: data[k] for k in ('run_id', 'created_at', 'scenario', 'elapsed_s')})
        return jsonify(items[:100])

    @app.get('/api/runs/<run_id>')
    def get_run(run_id):
        if len(run_id) != 32 or any(c not in '0123456789abcdef' for c in run_id):
            return jsonify(error='Identificador inválido.'), 404
        files = list(output.glob('*_' + run_id + '.json'))
        if not files:
            return jsonify(error='Ejecución no encontrada.'), 404
        return app.response_class(files[0].read_text(encoding='utf-8'), mimetype='application/json')

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
