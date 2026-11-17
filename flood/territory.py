"""Lectura de un territorio preparado; no rellena vacíos automáticamente."""
import json
from pathlib import Path
import numpy as np


def load_territory(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    with np.load(directory / "territory.npz", allow_pickle=False) as data:
        arrays = {key: data[key].copy() for key in data.files}
    z, inf = arrays["elevation_m"], arrays["infiltration_mmh"]
    if z.shape != inf.shape or not np.isfinite(z).all() or not np.isfinite(inf).all():
        raise ValueError("Territorio incompleto: revise elevación e infiltración.")
    geo = json.loads((directory / "cells.geojson").read_text(encoding="utf-8"))
    if len(geo["features"]) != z.size:
        raise ValueError("La malla no coincide con las matrices.")
    return manifest, arrays, geo
