# Power BI 管理儀表板頁面

所有頁面頂端加 site_id、scan_id、日期篩選器，並顯示「本機資料快照」。所有指標由 Fact 表計算，不使用已彙總平均。

| 頁面 | 視覺 | 欄位／Measure | 閱讀規則 |
|---|---|---|---|
| 盤點總覽 | 卡片、複核表、原因長條圖 | Observations、Review Observations、Review Rate、local_tree_id/review_reason | unresolved 身分只是當期樹位，不是跨期去重樹數 |
| DBH 驗證 | 有效配對卡、MAE/RMSE/Bias/MAPE 卡、散點圖、誤差表 | comparison_status=paired；X=manual_dbh_cm，Y=auto_dbh_cm，detail=observation_key | N=0 時空白 KPI；不繪假點；按 auto_method/strict_13m 分組 |
| 多期比較 | 折線或差值表 | FactGrowth tree_key/from_date/to_date/source/method/delta_dbh_cm | source 與 method 分開；不串接 App 模擬點；負增量上色待複核 |
| 資料品質 | 缺測狀態長條圖、來源與來源檔表 | comparison_status、identity_status、DimScan source_file/source_sha256 | 標準高度未確認不計精度 |
| 推估碳量 | 單掃描卡、樹高來源長條圖、推估明細 | Estimated CO2 Snapshot ton、height_source、formula_version | 多掃描不加總；顯示公式未經碳權驗證 |

估算碳量 measure 只在單個 scan_key 範圍顯示。管理者需要跨場址比較時，先定義一致日期的最新盤點選取規則，不能任意加總歷次存量。
將來源中文名稱放在視覺標題或工具提示：measured 人工實測／ai 演算法／estimated 推估。
驗收示範：16 筆觀測，16 待複核，0 有效配對；誤差與跨期視覺顯示資料不足。
