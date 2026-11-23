import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts.prepare_soilgrids import prepare


def test_soilgrids_units_locations_and_missing_data(tmp_path):
    pilot = Path(__file__).resolve().parents[1] / "data/pilot-v1"
    grid = json.loads((pilot / "manifest.json").read_bytes())
    height, width = grid["shape"]
    size = grid["cell_m"]
    transform = from_origin(*grid["origin_west_north"], size, size)
    # La última columna queda fuera del raster de prueba.
    for prop, normal in (("sand", 400), ("clay", 200)):
        layer = np.full((height, width - 1), normal, dtype=np.int16)
        if prop == "sand":
            layer[0, :3] = [-32768, 0, 900]
        with rasterio.open(tmp_path / f"{prop}_0-5cm_mean.tif", "w", driver="GTiff",
                           width=width - 1, height=height, count=1, dtype="int16",
                           transform=transform, crs=grid["crs"], nodata=-32768) as ds:
            ds.write(layer, 1)
    result = prepare(pilot, tmp_path)
    cells = {(r["row"], r["col"]): r for r in result["cells"]}
    assert result["counts"] == {"total": 576, "valid": 550, "missing": 25, "inconsistent": 1}
    assert cells[0, 0]["sand_pct"] is None and cells[0, 0]["clay_pct"] == 20
    assert cells[0, 1]["sand_pct"] == 0 and cells[0, 1]["status"] == "valida"
    assert cells[0, 2]["soil_ksat_mmh"] is None
    assert cells[0, width - 1]["status"] == "sin_datos"
    assert cells[1, 0]["sand_pct"] == 40
    assert cells[1, 0]["soil_ksat_mmh"] == pytest.approx(25.4 * 10**(-0.224), abs=0.00005)
    assert prepare(pilot, tmp_path)["cells_sha256"] == result["cells_sha256"]
