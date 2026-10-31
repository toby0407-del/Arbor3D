"""Tree measurement; importing lightweight fitting does not load Open3D or YOLO."""
__all__ = ["calculate_dbh_for_segmented_tree"]


def __getattr__(name):
    if name != "calculate_dbh_for_segmented_tree":
        raise AttributeError(name)
    from .pipeline import calculate_dbh_for_segmented_tree
    return calculate_dbh_for_segmented_tree
