"""Preparar y auditar la textura superficial antes de activar una versión territorial."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window


ROOT = Path(__file__).resolve().parents[1]
BASE = "https://files.isric.org/soilgrids/latest/data"
PROPERTIES = ("sand", "clay")


def source_url(prop):
    return f"{BASE}/{prop}/{prop}_0-5cm_mean.vrt"


def sample_layer(source, x, y, crs):
    """Leer solo la ventana que contiene los centros, conservando la máscara nativa."""
    with rasterio.open(source) as ds:
        if ds.crs is None or ds.count != 1:
            raise ValueError(f"Se esperaba una banda con CRS en {source}.")
        east, north = Transformer.from_crs(crs, ds.crs, always_xy=True).transform(x, y)
        col, row = ~ds.transform * (east, north)
        row = np.floor(row).astype(int)
        col = np.floor(col).astype(int)
        inside = (row >= 0) & (row < ds.height) & (col >= 0) & (col < ds.width)
        if not inside.any():
            raise ValueError(f"La capa no se superpone con el piloto: {source}")
        r, c = row[inside], col[inside]
        win = Window.from_slices((r.min(), r.max() + 1), (c.min(), c.max() + 1))
        block = ds.read(1, window=win, masked=True).astype(float).filled(np.nan)
        values = np.full(len(x), np.nan)
        values[inside] = block[r - r.min(), c - c.min()]
        valid = np.isfinite(values)
        if np.any((values[valid] < 0) | (values[valid] > 1000)):
            raise ValueError(f"Valor fuera del rango 0–1000 g/kg en {source}.")
        return values / 10


def prepare(pilot, local_sources=None):
    manifest = json.loads((pilot / "manifest.json").read_bytes())
    geo = json.loads((pilot / "cells.geojson").read_bytes())
    cells = [feature["properties"] for feature in geo["features"]]
    west, north = manifest["origin_west_north"]
    size = manifest["cell_m"]
    x = np.array([west + (p["col"] + 0.5) * size for p in cells])
    y = np.array([north - (p["row"] + 0.5) * size for p in cells])
    layers = {}
    for prop in PROPERTIES:
        source = (local_sources / f"{prop}_0-5cm_mean.tif" if local_sources is not None
                  else "/vsicurl/" + source_url(prop))
        layers[prop] = sample_layer(source, x, y, manifest["crs"])
    records = []
    valid_cells = 0
    for cell, sand, clay in zip(cells, layers["sand"], layers["clay"], strict=True):
        record = {"cell_id": cell["cell_id"], "row": cell["row"], "col": cell["col"],
                  "sand_pct": float(sand) if np.isfinite(sand) else None,
                  "clay_pct": float(clay) if np.isfinite(clay) else None,
                  "soil_ksat_mmh": None}
        if not np.isfinite(sand) or not np.isfinite(clay):
            record["status"] = "sin_datos"
        elif sand + clay > 100:
            record["status"] = "textura_inconsistente"
        else:
            record["status"] = "valida"
            exponent = -0.60 + 0.0126 * sand - 0.0064 * clay
            record["soil_ksat_mmh"] = round(float(25.4 * 10 ** exponent), 4)
            valid_cells += 1
        records.append(record)
    content = json.dumps(records, sort_keys=True, allow_nan=False).encode()
    return {"territory_version": manifest["version"], "cell_size_m": size,
            "dataset": "SoilGrids 2.0 · ISRIC", "depth_cm": [0, 5], "statistic": "mean",
            "license": "CC BY 4.0", "sources": {p: source_url(p) for p in PROPERTIES},
            "input_mode": "local" if local_sources is not None else "ISRIC WebDAV",
            "method": "Centro de celda en CRS nativo. g/kg dividido por 10 para porcentaje.",
            "soil_ksat_method": "Cosby et al. (1984). Conductividad saturada estimada del suelo mineral en mm/h.",
            "method_reference": "https://doi.org/10.1029/WR020i006p00682",
            "cells_sha256": hashlib.sha256(content).hexdigest(),
            "counts": {"total": len(cells), "valid": valid_cells,
                       "missing": sum(r["status"] == "sin_datos" for r in records),
                       "inconsistent": sum(r["status"] == "textura_inconsistente" for r in records)},
            "cells": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, help="Directorio con los GeoTIFF locales de ISRIC.")
    args = parser.parse_args()
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_CONNECTTIMEOUT="8",
                      GDAL_HTTP_TIMEOUT="40", GDAL_HTTP_MAX_RETRY="1"):
        report = prepare(ROOT / "data/pilot-v1", args.source_dir)
    path = ROOT / "work/soilgrids/pilot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    out = NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False)
    temp = Path(out.name)
    try:
        with out:
            json.dump(report, out, ensure_ascii=False, allow_nan=False)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    print(f"{path}\n{report['counts']}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
        raise SystemExit(f"No se pudo preparar SoilGrids: {exc}") from exc
