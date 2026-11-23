"""Predicción tabular de la acumulación máxima del simulador."""
import heapq
import numpy as np

FEATURES = ['constant', 'excess', 'rain', 'duration', 'excess_x_relief', 'excess_x_slope', 'rain_x_front']
FEATURES += ['spill_depth', 'downhill_drop', 'upstream_cells', 'soil_loss']
PROFILES = [None, [70, 30], [30, 70]]


def features(arrays, scenario):
    z = arrays['elevation_m']
    neighbors = np.pad(z, 1, mode='edge')
    relief = (neighbors[:-2,1:-1]+neighbors[2:,1:-1]+neighbors[1:-1,:-2]+neighbors[1:-1,2:])/4-z
    excess = np.maximum(0, scenario.rain_mm - scenario.duration_h *
                        (arrays['infiltration_mmh']*(1-scenario.saturation)+scenario.drainage_mmh))
    front = 0 if scenario.rain_profile is None else scenario.rain_profile[0]/100-.5
    rows, cols = z.shape
    spill = np.full(z.shape, np.inf)
    queue = []
    for r,c in np.ndindex(z.shape):
        if r in (0,rows-1) or c in (0,cols-1):
            spill[r,c] = z[r,c]
            heapq.heappush(queue,(z[r,c],r,c))
    def adjacent(r,c):
        return [(i,j) for i,j in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if 0<=i<rows and 0<=j<cols]
    while queue:
        level,r,c = heapq.heappop(queue)
        for i,j in adjacent(r,c):
            if np.isinf(spill[i,j]):
                spill[i,j] = max(level,z[i,j])
                heapq.heappush(queue,(spill[i,j],i,j))
    upstream = np.ones(z.shape)
    drop = np.zeros(z.shape)
    for cell in np.argsort(z.ravel())[::-1]:
        r,c = np.unravel_index(cell,z.shape)
        i,j = min(adjacent(r,c),key=lambda rc:z[rc])
        if z[i,j]<z[r,c]:
            upstream[i,j] += upstream[r,c]
            drop[r,c] = z[r,c]-z[i,j]
    return np.column_stack([np.broadcast_to(v,z.shape).ravel() for v in
                            (1, excess, scenario.rain_mm, scenario.duration_h, excess*relief,
                             excess*arrays['slope'], scenario.rain_mm*front, spill-z, drop, upstream,
                             arrays['infiltration_mmh']*(1-scenario.saturation)+scenario.drainage_mmh)])


def predict(matrix, coefficients, rain):
    if rain == 0:
        return np.zeros(len(matrix))
    return np.maximum(0, matrix @ coefficients)


def predict_tree(matrix, tree):
    left, right, feature, threshold, value = [np.asarray(tree[k]) for k in ('left','right','feature','threshold','value')]
    node = np.zeros(len(matrix),dtype=int)
    while True:
        pending = np.flatnonzero(left[node]>=0)
        if not len(pending):
            break
        parent = node[pending]
        node[pending] = np.where(matrix[pending,feature[parent]] <= threshold[parent],left[parent],right[parent])
    return np.where(matrix[:,2]==0,0,np.maximum(0,np.expm1(value[node])))
