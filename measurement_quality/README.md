# 品質感知量測與校準

`core.py` 僅依賴 NumPy；`dbh_seg` 現會評估圓擬合及可見寬度兩種候選，不再以 120° 決定正式 DBH。圖中的示意值未轉成程式精度門檻。

新輸出保留 `candidate_dbh_cm`、`measurement_quality` 與 `quality_candidates`。只有尺度、姿態、胸高與方法可識別條件成立，且有適用範圍內、經獨立驗證的校準模型達標時，才將結果放入 `dbh_cm`／`DBH_cm`。其他情況為 null 並保留複核入口。歷史 JSON 不會被自動重新標定。

## 真值校準

在 App 品質分頁輸入實際人工胸徑、日期及胸高確認，匯出全園校準證據。舊資料若沒有品質特徵，需由原始素材重新處理取得，不能從圖片猜點數／像素數。

匯出 JSON 的 `rows` 每筆須含：

- `source="observed"`、`scan_id`、`tree_id`、人工確認的 `persistent_tree_id`。
- `split` 為 `train`、`calibration` 或 `test`，同棵樹的全部期別與衍生樣本只能在同一集合。測試每樹／方法僅一個事先選定觀測，避免重掃灌大獨立樣本量。
- `candidate_dbh_cm`、`manual_dbh_cm` 為正公分數；`scan_date` 與 `manual_date` 同日、`strict_13m=true`。
- `features`：`effective_points`（2 mm 固定平面去重後點數）、`occupied_fraction`（5° 固定分箱占用比例）、`max_gap_deg`、`residual_m`、`condition_number`、`trunk_width_px`。影像寬度須從實際胸高影像記錄。
- `context`：`scale_verified`、`pose_verified`、`breast_height_verified`；卡尺另需 `view_direction_verified`、`left_boundary_visible`、`right_boundary_visible`、`near_circular_verified` 均為 true，且 `cropped=false`。這些是有證據的人工／系統確認，不可為了通過任意勾選。
- bundle 的 `scope={"sensor_id":"設備版本","protocol_id":"校正與前處理版本"}` 必須與每筆 context 相符。單一模型只能用在相同範圍。

```powershell
python -m measurement_quality calibrate evidence.json --out quality-model.json --tolerance-cm 1 --target 0.95
```

1 cm 與 0.95 是可配置的研究目標，不是已達效能。工具用訓練集合估計正則化 logistic、校準集合估計 sigmoid，再鎖定規則使用獨立測試集合。訓練與校準各需成功及失敗資料；模擬、重複觀測、同樹跨集合與資料缺失會拒絕。

模型會輸出方法個別與最終「合格方法中機率最高」政策的接受數、涵蓋率與 Wilson 95% 下限，方法與最終政策均須達預設目標才能啟用。測試不足或表現不佳時會產出停用模型；不得反覆用同一測試集合調參後再稱獨立驗證。這是初步研究工具，跨場域群聚、機率校準曲線與充分外部驗證仍需正式實驗。

## 接入新掃描

```powershell
$env:ARBOR3D_QUALITY_MODEL='C:\data\quality-model.json'
$env:ARBOR3D_QUALITY_CONTEXT='C:\data\quality-context.json'
python run_full_park_pipeline.py --scan_id YOUR_SCAN_ID
```

context 檔以樹號為鍵，例如 `{"Tree_001":{"sensor_id":"JMK6-v1","protocol_id":"protocol-v1","scale_verified":true,"pose_verified":true,"breast_height_verified":true,"trunk_width_px":80}}`。上例只示範格式，80 不是最低有效像素，且未提供卡尺所需確認。品質模組不替代完整管線的 Open3D／YOLO／Torch 依賴。

所有幾何小數防呆（3 個點、條件數上限、2 mm 去重、5° 分箱）是工程定義，不是精度實驗所得邊界。資料支持範圍只防止外推，不能當作普適最低點數、角度或像素。

## 補掃

App 的方向與效益是操作者規劃值，以安全、可達為硬條件；未知狀態不排序。分數為規劃補足角度／作業秒數，`precision_gain` 不填假機率。預算 0 時明示人工複核；補掃後必須匯入實際新觀測重新計算。此版本不控制無人機，也尚未學得實測精度增益模型。
