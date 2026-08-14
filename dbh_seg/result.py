"""DBH 計算結果的資料結構，統一給圓擬合與可見寬度法 (卡尺) 兩種方法共用。"""
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class DBHResult:
    method: str  # "circle" 或 "caliper"
    dbh_m: float
    arc_deg: float
    xc: float
    yc: float
    r: Optional[float] = None
    inlier_count: Optional[int] = None
    inlier_ratio: Optional[float] = None  # 貼合圓周的點佔整片切片的比例 (0~1)
    caliper_p1: Optional[np.ndarray] = None
    caliper_p2: Optional[np.ndarray] = None
    gap_detected: bool = False
    gap_m: float = 0.0
    caliper_kept_mask: Optional[np.ndarray] = None  # 相對 slice_pts 的布林遮罩
