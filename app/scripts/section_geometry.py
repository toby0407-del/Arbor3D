"""Diagnostic robust circle support; never a calibrated accuracy acceptance."""
import numpy as np


def _refine(p):
    """Centred algebraic least squares; reject rank-deficient line segments."""
    origin = np.mean(p,axis=0)
    v = p-origin
    matrix = np.column_stack((2*v,np.ones(len(v))))
    params, _, rank, _ = np.linalg.lstsq(matrix,np.sum(v*v,axis=1),rcond=None)
    radius2 = params[2]+params[:2]@params[:2]
    if rank < 3 or radius2 <= 0:
        return None
    return params[:2]+origin,float(np.sqrt(radius2))


def fit_section(points):
    p = np.asarray(points, dtype=float)
    result = dict(supported=False, point_count=len(p), center=None, radius=None,
                  candidate_dbh_cm=None, arc_deg=None, inliers=[])
    if p.ndim != 2 or p.shape[1] < 2 or len(p) < 8 or not np.isfinite(p).all():
        return result
    p = p[:, :2]
    origin = np.mean(p, axis=0)
    v = p-origin
    rng = np.random.default_rng(42)
    best = None
    for _ in range(512):
        a,b,c = v[rng.choice(len(v),3,replace=False)]
        matrix = 2*np.array([b-a,c-a])
        if abs(np.linalg.det(matrix)) < 1e-8:
            continue
        center = np.linalg.solve(matrix,np.array([b@b-a@a,c@c-a@a]))
        radius = np.linalg.norm(a-center)
        if not .03 <= radius <= .7:
            continue
        residual = np.abs(np.linalg.norm(v-center,axis=1)-radius)
        mask = residual <= .015
        score = (int(mask.sum()), -float(np.median(residual[mask])) if mask.any() else -1)
        if best is None or score > best[0]:
            best = (score,center,radius,mask)
    if best is None:
        return result
    _, center, radius, mask = best
    for _ in range(3):
        refined = _refine(v[mask]) if mask.sum() >= 8 else None
        if refined is None:
            break
        next_center,next_radius = refined
        if not .03 <= next_radius <= .7:
            break
        next_mask = np.abs(np.linalg.norm(v-next_center,axis=1)-next_radius) <= .015
        if next_mask.sum() < mask.sum():
            break
        center,radius,mask=next_center,next_radius,next_mask
    support_count = int(mask.sum())
    ratio = support_count/len(p)
    if support_count < 8 or ratio < .4:
        return result
    # A minority surface may be surrounded by clutter. Require independently
    # refitted support subsets to agree before using it as a diagnostic candidate.
    if ratio < .65:
        if support_count < 16:
            return result
        indices = np.random.default_rng(17).permutation(support_count)
        support_points = v[mask]
        tolerance = max(.005,radius*.08)
        for subset in (indices[::2],indices[1::2]):
            check = _refine(support_points[subset])
            if check is None or np.linalg.norm(check[0]-center)>tolerance or abs(check[1]-radius)>tolerance:
                return result
    support = v[mask]-center
    distances = np.linalg.norm(support,axis=1)
    jac = np.column_stack((-support/np.maximum(distances[:,None],1e-12),-np.ones(len(support))))
    if np.linalg.cond(jac) > 1000:
        return result
    angles = np.sort(np.mod(np.degrees(np.arctan2(support[:,1],support[:,0])),360))
    if len(np.unique((angles/5).astype(int))) < 8:
        return result
    gaps = np.diff(np.r_[angles,angles[0]+360])
    return dict(supported=True, point_count=len(p), center=(center+origin).tolist(),radius=float(radius),
                candidate_dbh_cm=float(radius*200),arc_deg=float(360-max(gaps)),inliers=mask.tolist(),
                support_ratio=ratio, support_count=support_count)
