"""CatÃ¡logo sintÃ©tico y evaluaciÃ³n bloqueada del sustituto lineal."""
import json
import hashlib
import argparse
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flood.simulator import Scenario, simulate, ENGINE_VERSION, INDEX_VERSION
from flood.surrogate import FEATURES, PROFILES, features, predict, predict_tree
from flood.territory import load_territory


def category_report(expected, predicted):
    # Filas: referencia del simulador. Columnas: estimación del árbol.
    bins = [25, 50, 75]
    matrix = np.zeros((4, 4), dtype=int)
    np.add.at(matrix, (np.digitize(expected, bins), np.digitize(predicted, bins)), 1)
    hits = matrix[2:, 2:].sum()
    missed = matrix[2:, :2].sum()
    extra = matrix[:2, 2:].sum()
    print("Simulador / ML     Baja  Media  Alta  Muy alta")
    for label, row in zip(("Baja", "Media", "Alta", "Muy alta"), matrix):
        print(f"{label:14}", *(f"{value:5}" for value in row))
    print(f"Coincidencia exacta: {matrix.trace()}/{matrix.sum()} ({matrix.trace()/matrix.sum():.1%})")
    print(f"Desde 50 mm: {hits} detectadas, {missed} omitidas, {extra} marcadas de más.")


def evaluate_saved(out, arrays, territory_version):
    model = json.loads((out / 'model.json').read_text(encoding='utf8'))
    if model['territory'] != territory_version or model['features'] != FEATURES:
        raise ValueError("El modelo guardado requiere otra versión del territorio o de las variables.")
    catalog = json.loads((out / 'catalog.json').read_text(encoding='utf8'))
    with np.load(out / 'catalog.npz') as archive:
        peaks, blocks = archive['maximum_mm'], archive['block']
    if peaks.shape != (len(catalog), *blocks.shape) or blocks.shape != arrays['elevation_m'].shape:
        raise ValueError("Las dimensiones del catálogo y la malla no coinciden.")
    print("Modelo", model['version'])
    for split, partition in enumerate(('validation', 'test'), start=1):
        mask = np.isin(blocks, model['blocks'][split]).ravel()
        expected, predicted = [], []
        for record, peak in zip(catalog, peaks):
            if record['partition'] == partition:
                scenario = Scenario.from_dict(record['parameters'])
                expected.append(peak.ravel()[mask])
                predicted.append(predict_tree(features(arrays, scenario)[mask], model['tree']))
        print("Validación" if split == 1 else "Prueba")
        category_report(np.concatenate(expected), np.concatenate(predicted))


def main():
    territory, arrays, _ = load_territory(ROOT/'data/pilot-v1')
    rng = np.random.default_rng(42)
    out = ROOT/'data/pilot-v1/ml'
    parser = argparse.ArgumentParser()
    parser.add_argument('--evaluar', action='store_true', help='Evaluar el árbol y el catálogo guardados.')
    if parser.parse_args().evaluar:
        evaluate_saved(out, arrays, territory['version'])
        return
    out.mkdir(exist_ok=True)
    rows, cols = np.indices(arrays['elevation_m'].shape)
    blocks = (rows//6)*4 + cols//6
    reserved = rng.permutation(16).tolist()
    partitions = [reserved[:10], reserved[10:13], reserved[13:]]
    xs, ys, catalog, labels = [[],[],[]], [[],[],[]], [], []
    for i in range(72):
        split = 0 if i < 48 else (1 if i < 60 else 2)
        sc = Scenario(float(rng.choice([0,25,50,75,100,150])), float(rng.choice([.5,1,2,3])),
                      float(rng.choice([0,.5,1])), float(rng.choice([0,5,10])), PROFILES[i%3])
        # Evitar que escenarios idÃ©nticos crucen particiones.
        if any(row['parameters']==vars(sc) for row in catalog):
            continue
        result = simulate(arrays['elevation_m'], arrays['infiltration_mmh'], sc)
        labels.append(result['maximum_mm'])
        mask = np.isin(blocks, partitions[split]).ravel()
        xs[split].append(features(arrays,sc)[mask]); ys[split].append(result['maximum_mm'].ravel()[mask])
        catalog.append(dict(id=i,partition=['train','validation','test'][split],parameters=vars(sc)))
    x = [np.vstack(a) for a in xs]; y = [np.concatenate(a) for a in ys]
    from sklearn.tree import DecisionTreeRegressor
    from sklearn.dummy import DummyRegressor
    from sklearn.linear_model import LinearRegression
    reg = DecisionTreeRegressor(max_depth=12, min_samples_leaf=8, random_state=42)
    reg.fit(x[0], np.log1p(y[0]))
    nodes = reg.tree_
    tree = dict(left=nodes.children_left.tolist(),right=nodes.children_right.tolist(),
                feature=nodes.feature.tolist(),threshold=nodes.threshold.tolist(),value=nodes.value.ravel().tolist())
    coef = LinearRegression(fit_intercept=False).fit(x[0][:,:7],y[0]).coef_
    baseline = float(DummyRegressor().fit(x[0],y[0]).constant_.item())
    backend = 'scikit-learn DecisionTreeRegressor'
    metrics = {}
    for i,name in [(1,'validation'),(2,'test')]:
        metrics[name] = {}
        for candidate in ['baseline','linear','tree']:
            start = perf_counter()
            pred = np.full(len(y[i]),baseline) if candidate=='baseline' else (predict(x[i][:,:7],coef,1) if candidate=='linear' else predict_tree(x[i],tree))
            if candidate=='linear': pred[x[i][:,2]==0]=0
            elapsed = perf_counter()-start
            error = pred-y[i]
            metrics[name][candidate] = dict(mae_mm=float(np.abs(error).mean()),rmse_mm=float(np.mean(error**2)**.5),
                                            r2=float(1-error@error/np.sum((y[i]-y[i].mean())**2)),inference_s=elapsed,category_accuracy=float(np.mean(np.minimum(3,pred//25)==np.minimum(3,y[i]//25))))
    train = [r['parameters'] for r in catalog if r['partition']=='train']
    bounds = {k:[min(s[k] for s in train),max(s[k] for s in train)] for k in ['rain_mm','duration_h','saturation','drainage_mmh']}
    model = dict(territory=territory['version'], simulator=ENGINE_VERSION,index=INDEX_VERSION,features=FEATURES,
                 tree=tree,baseline=baseline,bounds=bounds,profiles=PROFILES,backend=backend,seed=42,
                 metrics=metrics,blocks=partitions,active=metrics['validation']['tree']['mae_mm']<metrics['validation']['linear']['mae_mm'] and metrics['validation']['tree']['category_accuracy']>metrics['validation']['linear']['category_accuracy'])
    model['version']='tree-'+hashlib.sha256(json.dumps([model['territory'],FEATURES,tree]).encode()).hexdigest()[:12]
    np.savez_compressed(out/'catalog.npz',maximum_mm=np.stack(labels),block=blocks)
    (out/'catalog.json').write_text(json.dumps(catalog),encoding='utf8')
    temp = out/'model.new.json'
    temp.write_text(json.dumps(model,indent=2),encoding='utf8')
    temp.replace(out/'model.json')
    print(len(catalog), metrics, model['active'])
    evaluate_saved(out, arrays, territory['version'])


if __name__=='__main__':
    main()
