"""從 calib.json 建立相機投影模型，並判斷 3D 點落在 2D 遮罩的哪個像素上。

這是 dbh_seg/isolate.py 跟 gaussian_prune/prune.py 共用的核心數學：兩者都要
把 3D 點 (一個是去噪點雲，一個是高斯球中心) 投影到同一張相機拍的 2D 遮罩上，
抽出來共用可以避免同一套投影邏輯散落在兩個地方各寫一份。

⚠️ 重要：這台 JMK6 相機是魚眼鏡頭 (calib.json 裡 camera_model 標示為
"fisheyeKB"，即 Kannala-Brandt 魚眼模型)，視角遠超過一般針孔相機能處理的
範圍。所以這裡改用 cv2.fisheye.projectPoints，而不是一般的
cv2.projectPoints——後者是為視角遠小於 180 度的針孔相機設計的透視投影
公式，直接套用在魚眼鏡頭上，離畫面中心越遠的點，算出來的像素座標誤差
會越離譜 (甚至完全錯誤)，這很可能是先前一連串詭異幾何結果背後的根本
原因之一。
"""
import cv2
import numpy as np


def build_camera_model(calib_data):
    """從 calib.json 解析出相機內外參，回傳一個 dict 方便後續函式使用。"""
    left_info = calib_data["camera_info"]["left"]
    K = np.array(left_info["K"], dtype=np.float64).reshape(3, 3)
    # cv2.fisheye 系列函式要求畸變係數是 (4, 1) 的 float64 陣列
    dist_coeffs = np.array(left_info["coeff"], dtype=np.float64).reshape(4, 1)

    extrinsic_c2w = np.array(
        calib_data["out_put"]["left"]["transform_matrix"], dtype=np.float64
    ).reshape(4, 4)
    extrinsic_w2c = np.linalg.inv(extrinsic_c2w)
    R_matrix = extrinsic_w2c[:3, :3]
    T_vector = extrinsic_w2c[:3, 3]
    rvec, _ = cv2.Rodrigues(R_matrix)

    return {
        "K": K,
        "dist_coeffs": dist_coeffs,
        "R": R_matrix,
        "T": T_vector,
        "rvec": rvec,
        "tvec": T_vector,
        "width": int(left_info["image_width"]),
        "height": int(left_info["image_height"]),
    }


def apply_c2w_pose(cam, position, rotation_c2w):
    """用 cameras.json 的單幀世界姿態覆寫 cam 的外參（內參不變）。

    rotation_c2w: 3x3，相機座標 → 世界座標（與 RayStudio cameras.json 一致）
    position: 相機中心在世界座標
    """
    R_c2w = np.asarray(rotation_c2w, dtype=np.float64)
    C = np.asarray(position, dtype=np.float64).reshape(3)
    R_w2c = R_c2w.T
    T_w2c = -R_w2c @ C
    rvec, _ = cv2.Rodrigues(R_w2c)
    cam = dict(cam)
    cam["R"] = R_w2c
    cam["T"] = T_w2c
    cam["rvec"] = rvec
    cam["tvec"] = T_w2c
    return cam


def project_points(points_3d, cam):
    """把 3D 點投影到相機影像座標，回傳 (u, v, depth, valid_math)。

    用 cv2.fisheye.projectPoints (Kannala-Brandt 魚眼模型) 對應
    calib.json 裡 camera_model="fisheyeKB" 的畸變係數。
    """
    points_3d = np.asarray(points_3d, dtype=np.float64)
    points_cam = (cam["R"] @ points_3d.T).T + cam["T"]
    depth = points_cam[:, 2]

    obj_points = points_3d.reshape(-1, 1, 3)
    points_2d, _ = cv2.fisheye.projectPoints(
        obj_points, cam["rvec"], cam["tvec"], cam["K"], cam["dist_coeffs"]
    )
    points_2d = np.nan_to_num(points_2d, nan=-1.0, posinf=-1.0, neginf=-1.0)
    u_float, v_float = points_2d[:, 0, 0], points_2d[:, 0, 1]
    valid_math = (u_float != -1.0) & (v_float != -1.0)

    # 少數退化的高斯球座標會投影出誇張到超出 int 範圍的有限浮點數
    # (不是 NaN/Inf，nan_to_num 抓不到)，直接轉型會跳出 RuntimeWarning。
    # 先夾在一個遠超影像範圍、但 int 絕對裝得下的區間，這些點之後一定會
    # 被邊界檢查濾掉，夾範圍只是讓轉型過程乾淨、不再跳警告。
    safe_u = np.clip(u_float, -1e6, 1e6)
    safe_v = np.clip(v_float, -1e6, 1e6)

    u = np.zeros(len(points_3d), dtype=int)
    v = np.zeros(len(points_3d), dtype=int)
    u[valid_math] = np.round(safe_u[valid_math]).astype(int)
    v[valid_math] = np.round(safe_v[valid_math]).astype(int)
    return u, v, depth, valid_math


def points_in_mask(points_3d, cam, mask, depth_min, depth_max):
    """整合投影 + 深度裁切 + 邊界檢查 + 遮罩比對，回傳 (is_in_mask, u, v, depth)。"""
    u, v, depth, valid_math = project_points(points_3d, cam)
    valid_depth = (depth > depth_min) & (depth < depth_max)
    valid_boundary = (
        valid_math
        & valid_depth
        & (u >= 0) & (u < cam["width"])
        & (v >= 0) & (v < cam["height"])
    )

    is_in_mask = np.zeros(len(points_3d), dtype=bool)
    is_in_mask[valid_boundary] = mask[v[valid_boundary], u[valid_boundary]]
    return is_in_mask, u, v, depth
