"""Geometry helpers load their dependencies only when actually used.

Circle fitting and section diagnostics require NumPy only. Heavy point-cloud,
projection and visualization dependencies remain available through the same API.
"""
from importlib import import_module

_MODULES = {'compute_ground_transform': 'ground', 'apply_ground_transform': 'ground', 'remove_ground_and_align': 'ground_align', 'fit_circle_lsq': 'circle_fit', 'robust_circle_fit': 'circle_fit', 'ransac_circle_fit': 'ransac_circle', 'apply_depth_buffer_filter': 'occlusion', 'keep_largest_cluster': 'clustering', 'largest_cluster_indices': 'clustering', 'create_ground_grid': 'viz', 'arc_coverage_deg': 'arc_coverage', 'circle_inlier_mask': 'arc_coverage', 'pca_visible_width': 'pca_width', 'view_aligned_width': 'pca_width', 'largest_contiguous_segment': 'gap_split', 'build_camera_model': 'projection', 'apply_c2w_pose': 'projection', 'project_points': 'projection', 'points_in_mask': 'projection'}
__all__ = list(_MODULES)


def __getattr__(name):
    module = _MODULES.get(name)
    if module is None:
        raise AttributeError(name)
    value = getattr(import_module("." + module, __name__), name)
    globals()[name] = value
    return value
