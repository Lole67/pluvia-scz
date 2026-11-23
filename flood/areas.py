"""Áreas de intersección en coordenadas de cuadrícula (una unidad = 250 m)."""
import numpy as np


def clip(points, axis, edge, sign):
    output = []
    for a, b in zip(points[-1:] + points[:-1], points):
        inside_a = sign * (a[axis] - edge) >= 0
        inside_b = sign * (b[axis] - edge) >= 0
        if inside_a != inside_b:
            t = (edge - a[axis]) / (b[axis] - a[axis])
            output.append([a[k] + t * (b[k] - a[k]) for k in (0, 1)])
        if inside_b:
            output.append(b)
    return output


def fractions(polygon, shape):
    weights = np.zeros(shape)
    for row, col in np.ndindex(shape):
        part = polygon
        for axis, edge, sign in ((0,col,1),(0,col+1,-1),(1,row,1),(1,row+1,-1)):
            part = clip(part, axis, edge, sign)
        twice = sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(part, part[1:]+part[:1]))
        weights[row,col] = min(1, abs(twice)/2)
    return weights


def summarize(result, weights):
    index, peak = result['index'], result['maximum_mm']
    categories = np.minimum(3, np.floor(index / 25))
    names = ['baja','media','alta','muy_alta']
    return dict(max_mm=float(peak[weights>0].max()), mean_max_mm=float(np.average(peak,weights=weights)),
                mean_index=float(np.average(index,weights=weights)), report_km2=float(weights.sum()*.0625),
                category_area_km2={name:float(weights[categories==i].sum()*.0625) for i,name in enumerate(names)})
