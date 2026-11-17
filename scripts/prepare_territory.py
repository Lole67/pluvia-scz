"""Preparar zona piloto georreferenciada usando la tesela oficial FABDEM."""
from pathlib import Path
import hashlib
import json
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/S18W064_FABDEM_V1-2.tif"
OUT = ROOT / "data/pilot-v1"


def main():
    if not SOURCE.exists():
        raise SystemExit(f"Falta DEM público: {SOURCE}. No se generará relieve inventado.")
    # Piloto de 6 × 6 km centrado cerca del centro urbano; reporte interior 4 × 4 km.
    project = Transformer.from_crs(4326, 32720, always_xy=True)
    geographic = Transformer.from_crs(32720, 4326, always_xy=True)
    cx, cy = project.transform(-63.18, -17.78)
    west = round(cx / 250) * 250 - 3000
    north = round(cy / 250) * 250 + 3000
    transform = from_origin(west, north, 250, 250)
    z = np.full((24, 24), np.nan, dtype=np.float64)
    with rasterio.open(SOURCE) as src:
        if src.crs is None:
            raise ValueError("DEM sin CRS.")
        source_info = {"crs": str(src.crs), "bounds": list(src.bounds),
                       "pixel_size": list(src.res), "nodata": src.nodata}
        reproject(rasterio.band(src, 1), z, src_transform=src.transform,
                  src_crs=src.crs, src_nodata=src.nodata, dst_transform=transform,
                  dst_crs="EPSG:32720", dst_nodata=np.nan, resampling=Resampling.average)
    if not np.isfinite(z).all():
        raise ValueError("El DEM deja celdas vacías; no se sustituyen por cero.")
    dy, dx = np.gradient(z, 250, 250)
    slope = np.hypot(dx, dy)
    mask = np.zeros(z.shape, dtype=bool)
    mask[4:-4, 4:-4] = True
    features = []
    for row in range(24):
        for col in range(24):
            x, y = west + col * 250, north - row * 250
            ring = [geographic.transform(px, py) for px, py in
                    [(x, y), (x + 250, y), (x + 250, y - 250), (x, y - 250), (x, y)]]
            features.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                             "properties": {"cell_id": f"UTM20S-{int(x)}-{int(y)}", "row": row,
                                            "col": col, "report": bool(mask[row, col]),
                                            "elevation_m": float(z[row, col]),
                                            "infiltration_mmh": 5.0, "infiltration_origin": "sintética provisional"}})
    sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    manifest = {"version": "pilot-fabdem-v1-" + sha[:12], "cell_m": 250, "shape": [24, 24],
                "crs": "EPSG:32720", "domain_area_km2": 36, "report_area_km2": 16,
                "origin_west_north": [west, north], "boundary": "closed",
                "source_sha256": sha, "source_metadata": source_info,
                "elevation_min_m": float(z.min()), "elevation_max_m": float(z.max()),
                "sources": {"elevation": {"classification": "pública/modelada", "product": "FABDEM V1-2",
                    "resolution": "1 segundo de arco (~30 m)", "aggregation": "promedio a 250 m",
                    "url": "https://data.bris.ac.uk/datasets/s5hqmjcdj8yo2ibzi9b4ew3sn/",
                    "doi": "10.5523/bris.s5hqmjcdj8yo2ibzi9b4ew3sn", "license": "CC BY-NC-SA 4.0"},
                    "slope": {"classification": "derivada", "method": "gradiente del DEM agregado"},
                    "infiltration": {"classification": "sintética provisional", "value_mmh": 5,
                                     "coverage": "uniforme; cobertura/SoilGrids pendientes"}},
                "warnings": ["Zona piloto parcial, no toda Santa Cruz.",
                    "Cobertura y SoilGrids no incorporados; infiltración uniforme sintética de 5 mm/h.",
                    "Borde exterior cerrado; buffer de 1 km no validado como cuenca ni aislamiento suficiente.",
                    "No modela desbordamiento del Piraí ni red municipal de drenaje.",
                    "Resultados exploratorios sin validación observacional."]}
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "territory.npz", elevation_m=z, slope=slope,
                        infiltration_mmh=np.full(z.shape, 5.0), report_mask=mask)
    (OUT / "cells.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    with rasterio.open(OUT / "elevation_250m.tif", "w", driver="GTiff", height=24, width=24,
                       count=1, dtype="float64", crs="EPSG:32720", transform=transform) as dst:
        dst.write(z, 1)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
