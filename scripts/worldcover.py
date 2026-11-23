"""Cobertura WorldCover del piloto, estimada por área en coordenadas métricas."""
import hashlib

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window


TILE = "ESA_WorldCover_10m_2021_v200_S18W066_Map.tif"
CLASSES = {
    0: "Sin datos", 10: "Arbolado", 20: "Matorral", 30: "Pastizal",
    40: "Cultivos", 50: "Zona construida", 60: "Suelo desnudo o vegetación escasa",
    70: "Nieve o hielo", 80: "Agua permanente", 90: "Humedal herbáceo",
    95: "Manglar", 100: "Musgos y líquenes",
}


def read_cover(path, transform, shape, crs):
    # Cada punto representa un cuadrado UTM de 5 × 5 m dentro de la celda.
    subdivisions = 50
    rows, cols = shape
    sampled = np.zeros((rows * subdivisions, cols * subdivisions), dtype=np.uint8)
    with rasterio.open(path) as src:
        tags = src.tags()
        if (tags.get("product_type"), tags.get("product_tile"), tags.get("time_start"),
                tags.get("product_version")) != ("LandCover Map", "S18W066", "2021-01-01T00:00:00Z", "V2.0.0"):
            raise ValueError("Se requiere el mapa WorldCover 2021 v200, tesela S18W066.")
        y, x = np.indices(sampled.shape)
        east, north = transform * ((x + 0.5) / subdivisions, (y + 0.5) / subdivisions)
        lon, lat = Transformer.from_crs(crs, src.crs, always_xy=True).transform(east, north)
        pixel_x, pixel_y = ~src.transform * (lon, lat)
        col = np.floor(pixel_x).astype(int)
        row = np.floor(pixel_y).astype(int)
        valid = (row >= 0) & (row < src.height) & (col >= 0) & (col < src.width)
        if valid.any():
            r, c = row[valid], col[valid]
            window = Window.from_slices((r.min(), r.max() + 1), (c.min(), c.max() + 1))
            data = src.read(1, window=window, masked=True).filled(0)
            sampled[valid] = data[r - r.min(), c - c.min()]
    if not np.isin(sampled, list(CLASSES)).all() or not sampled.any():
        raise ValueError("WorldCover sin cobertura válida o con clases desconocidas.")
    with path.open("rb") as source:
        checksum = hashlib.file_digest(source, "sha256").hexdigest()
    blocks = sampled.reshape(rows, subdivisions, cols, subdivisions)
    percentages = {code: np.count_nonzero(blocks == code, axis=(1, 3)) * 100 / subdivisions**2
                   for code in CLASSES}
    metadata = {
        "classification": "pública/modelada", "product": "ESA WorldCover 2021 v200",
        "resolution": "10 m nominales", "year": 2021, "tile": TILE, "sha256": checksum,
        "aggregation": "Porcentaje estimado por clase mediante muestreo regular UTM a 5 m "
                       "(vecino más cercano). El denominador incluye las muestras sin datos.",
        "classes": CLASSES, "license": "CC BY 4.0", "attribution": tags["copyright"],
        "url": "https://esa-worldcover.org/en/data-access",
    }
    return percentages, metadata
