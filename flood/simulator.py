"""Balance conservativo explícito; no representa hidráulica de tuberías."""
from dataclasses import dataclass
import math
import numpy as np

ENGINE_VERSION = "balance-d4-0.1.0"
INDEX_VERSION = "max-mm-linear-100-v1"
CELL_M = 250.0


@dataclass(frozen=True)
class Scenario:
    rain_mm: float
    duration_h: float
    saturation: float
    drainage_mmh: float

    @classmethod
    def from_dict(cls, payload):
        if not isinstance(payload, dict):
            raise ValueError("Envíe una configuración JSON con los cuatro campos.")
        bounds = {"rain_mm": (0, 300), "duration_h": (0.1, 24),
                  "saturation": (0, 1), "drainage_mmh": (0, 100)}
        unknown = set(payload) - set(bounds)
        if unknown:
            raise ValueError("Campos no admitidos: " + ", ".join(sorted(unknown)))
        values = {}
        for key, (low, high) in bounds.items():
            value = payload.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{key}: ingrese un número entre {low} y {high}.")
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"{key}: debe estar entre {low} y {high}.")
            values[key] = float(value)
        return cls(**values)


def index_from_max(max_mm):
    """Referencia fija provisional: 100 mm = 100 puntos; no probabilidad."""
    return np.clip(np.asarray(max_mm), 0, 100)


def simulate(elevation_m, infiltration_mmh, scenario, dt_s=30.0,
             initial_mm=None, boundary="closed", mobility_m2_s=20.0):
    """D4 por carga z+h. Conductancia sintética, tasas en m²/s.

    Bordes cerrados para piloto: no hay aportes externos al dominio fijo.
    Cada cara transfiere una vez; limitación conjunta por agua del donante.
    La ventana es la duración de lluvia, sin recesión posterior.
    """
    scenario = Scenario.from_dict(vars(scenario))
    z = np.asarray(elevation_m, dtype=float)
    inf = np.broadcast_to(np.asarray(infiltration_mmh, dtype=float), z.shape)
    if z.ndim != 2 or min(z.shape) < 2 or not np.isfinite(z).all():
        raise ValueError("El DEM debe ser una matriz 2D completa de al menos 2 × 2.")
    if not np.isfinite(inf).all() or (inf < 0).any():
        raise ValueError("La infiltración requiere valores finitos no negativos.")
    if boundary != "closed":
        raise ValueError("Esta versión solo implementa borde cerrado.")
    if not math.isfinite(dt_s) or not 0 < dt_s <= 60:
        raise ValueError("El paso debe estar entre 0 y 60 segundos.")
    if not math.isfinite(mobility_m2_s) or not 0 <= mobility_m2_s <= 20:
        raise ValueError("Conductancia fuera del rango de esta versión.")
    h = np.zeros(z.shape) if initial_mm is None else np.array(initial_mm, dtype=float) / 1000
    if h.shape != z.shape or not np.isfinite(h).all() or (h < 0).any():
        raise ValueError("Almacenamiento inicial inválido.")
    area = CELL_M ** 2
    start = float(h.sum() * area)
    maximum = h.copy()
    duration = scenario.duration_h * 3600
    steps = math.ceil(duration / dt_s)
    step = duration / steps  # Serie constante; integración exacta del total.
    rain_step = scenario.rain_mm / steps / 1000
    rain_total = inf_total = drain_total = 0.0
    ledger = []
    effective_inf = inf * (1 - scenario.saturation)
    for n in range(steps):
        h += rain_step
        rain_total += rain_step * z.size * area
        removed_inf = np.minimum(h, effective_inf * step / 3600 / 1000)
        h -= removed_inf
        removed_drain = np.minimum(h, scenario.drainage_mmh * step / 3600 / 1000)
        h -= removed_drain
        inf_total += float(removed_inf.sum() * area)
        drain_total += float(removed_drain.sum() * area)
        maximum = np.maximum(maximum, h)

        head = z + h
        # Flujo firmado: positivo derecha / abajo; valores en metros de lámina.
        qx = mobility_m2_s * step / area * (head[:, :-1] - head[:, 1:])
        qy = mobility_m2_s * step / area * (head[:-1, :] - head[1:, :])
        outgoing = np.zeros_like(h)
        outgoing[:, :-1] += np.maximum(qx, 0)
        outgoing[:, 1:] += np.maximum(-qx, 0)
        outgoing[:-1, :] += np.maximum(qy, 0)
        outgoing[1:, :] += np.maximum(-qy, 0)
        scale = np.minimum(1, np.divide(h, outgoing, out=np.ones_like(h), where=outgoing > 0))
        qx *= np.where(qx >= 0, scale[:, :-1], scale[:, 1:])
        qy *= np.where(qy >= 0, scale[:-1, :], scale[1:, :])
        h[:, :-1] -= qx
        h[:, 1:] += qx
        h[:-1, :] -= qy
        h[1:, :] += qy
        if h.min() < -1e-12:
            raise ArithmeticError("Almacenamiento negativo: ejecución inválida.")
        # No se recorta agua silenciosamente. Redondeo de máquina se conserva.
        maximum = np.maximum(maximum, h)
        stored = float(h.sum() * area)
        residual = start + rain_total - inf_total - drain_total - stored
        tolerance = max(1e-6, (start + rain_total) * 1e-10)
        if abs(residual) > tolerance:
            raise ArithmeticError("El residuo de masa supera la tolerancia.")
        ledger.append({"time_s": (n + 1) * step, "rain_m3": rain_total,
                       "infiltration_m3": inf_total, "drainage_m3": drain_total,
                       "stored_m3": stored, "residual_m3": residual})
    return {"maximum_mm": maximum * 1000, "final_mm": h * 1000,
            "index": index_from_max(maximum * 1000), "ledger": ledger,
            "step_s": step, "steps": steps, "initial_m3": start,
            "tolerance_m3": max(1e-6, (start + rain_total) * 1e-10)}
