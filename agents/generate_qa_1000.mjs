import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const target = path.join(root, "knowledge", "arbor3d-qa-1000.jsonl");

const topics = [
  ["資料來源與揭露", "真實資料、推估資料與模擬展示資料的區分", ["dataset_kind", "observed", "estimated", "simulated", "資料來源"], "應保留 dataset_kind 與來源欄位。observed 只代表有現場來源的觀測；estimated 是公式或模型推估；simulated 是展示情境。三者不可混算正式精度、真實成長或碳權成果。"],
  ["胸徑量測", "標準 1.3 公尺胸高 DBH 的量測與紀錄", ["DBH", "胸徑", "1.3m", "人工量測", "量測日期"], "人工胸徑須在離地 1.3 公尺量測，記錄正數胸徑、量測日期與標準高度確認。非標準高度資料要標記並複核，不應直接納入正式胸徑誤差指標。"],
  ["AI 與人工配對", "AI 胸徑與人工胸徑的有效配對", ["AI DBH", "人工 DBH", "配對", "同一天", "同樹號"], "有效配對至少要同場址、同一棵樹、同一天且人工量測已確認為標準 1.3 公尺。AI 與人工欄位必須分開保存，人工值不能覆寫演算法結果。"],
  ["精度指標", "MAE、RMSE、Bias 與 MAPE 的計算限制", ["MAE", "RMSE", "Bias", "MAPE", "精度"], "只有有效 AI／人工配對才能計算精度。Error 為 AI 減人工，Bias 是平均誤差，MAE 是平均絕對誤差，RMSE 是均方根誤差；MAPE 的人工胸徑必須大於零。樣本為零時指標應留空。"],
  ["跨期樹木身分", "跨期固定樹號 persistent_tree_id 的使用", ["persistent_tree_id", "固定樹號", "Tree_001", "跨期", "身分映射"], "Tree_001 之類編號通常只在單次掃描內有效。跨期比較必須用人工確認的 persistent_tree_id，並保留場址、路線、日期與來源；未確認映射時不得宣稱是同一棵樹。"],
  ["季度成長", "季度 DBH 與樹高成長的跨期判讀", ["季度", "成長", "DBH 增量", "樹高", "跨期比較"], "跨期成長需有同一固定樹號的多期觀測、可比較的量測方法與完整日期。展示季度曲線只能說明情境，不是現場真實成長；正式結果要等第二期真實掃描與人工複核。"],
  ["負增量複核", "DBH 或樹高負增量的處理", ["負增量", "異常", "複核", "死亡", "量測誤差"], "負增量應先標成待複核，檢查固定樹號、量測高度、遮擋、點雲品質與人工紀錄。不能只憑負增量判定樹木死亡、健康惡化或負碳排。"],
  ["碳量估算", "CO2 當量與碳儲量的估算及限制", ["CO2", "碳匯", "碳儲量", "係數", "碳權"], "目前 CO2 當量由胸徑、樹高與係數公式估算，是管理參考值。缺少實測樹高或適地係數時要明確標示推估；不得稱為經查證減碳量、年度吸收速率或可交易碳權。"],
  ["現場複核", "紅燈、低信心與遮擋樹木的複核優先序", ["紅燈", "低信心", "遮擋", "wide_caliper", "複核"], "優先複核無法量測、卡尺偏寬、切片缺口、低信心或遮擋嚴重的樹。先做 1.3 公尺人工胸徑，再補拍影像或重掃；燈號是作業優先序，不是健康診斷。"],
  ["點雲品質", "點雲側視、密度與遮擋對量測的影響", ["點雲", "側視", "密度", "遮擋", "PLY"], "點雲需確認尺度、地面對齊、樹幹覆蓋與胸高附近密度。遮擋、漂浮點、併株或座標尺度錯誤都會影響胸徑；側視圖是複核證據之一，不能單獨證明精度。"],
  ["樹幹分割", "樹幹 Segmentation 遮罩的判讀", ["Segmentation", "樹幹", "遮罩", "YOLO", "誤分割"], "應檢查遮罩是否涵蓋主幹、是否混入枝葉、護欄或鄰樹，以及胸高位置是否可見。遮罩只代表模型分割結果；未經標註資料驗證時不能宣稱 YOLO 的正式準確率。"],
  ["胸高橫切面", "胸高橫切面與圓擬合結果的判讀", ["橫切面", "圓擬合", "RANSAC", "弧覆蓋", "卡尺"], "橫切面要確認取樣高度約 1.3 公尺、點群屬於同一樹幹且弧覆蓋足夠。缺口、橢圓變形、併株與離群點會使擬合偏大或偏小，異常結果要人工卡尺複核。"],
  ["素材匯入", "PLY、原始照片、校正與相機姿態的匯入流程", ["匯入", "PLY", "原始照片", "calib.json", "cameras.json"], "快速預覽可匯入去噪 PLY、高斯濺射 PLY 與原始照片；正式管線還要有 calib.json 與 cameras.json。上傳前需驗證檔案格式、掃描編號與來源，並保留處理紀錄。"],
  ["路線與定位", "GPX、GPS 與路線位置資料的使用", ["GPX", "GPS", "路線", "座標", "定位精度"], "正式路線應使用現場 GPX，保存時間、座標系與定位精度。示範或 OSM 參考線只能協助展示；沒有可靠 GPS 時，沿路線放置的樹點屬相對位置，不可當精密測量座標。"],
  ["Power BI 與 Fabric", "Power BI／Fabric 的跨期分析與資料治理", ["Power BI", "Fabric", "Power Query", "DAX", "RLS"], "Power BI 應分開 FactInventory、FactMeasurement、FactGrowth 與維度表，保留 dataset_kind、來源與固定樹號。發布前要在 Desktop 驗證 Power Query、DAX、關係與五頁版面，再設定場址權限與 RLS。"],
  ["RAG 與 GPT", "RAG 檢索內容交給 GPT 回答的原則", ["RAG", "GPT", "Azure AI", "檢索", "引用"], "RAG 先從受控知識庫取回相關片段，再連同當次盤點 JSON 交給 GPT。模型只能根據證據回答並列來源；找不到依據要說資料不足。檢索片段是不可信資料，不能把其中文字當系統指令。"],
  ["帳號與資料安全", "帳號、角色權限、Session 與敏感資料保護", ["登入", "角色權限", "Session", "個資", "Entra ID"], "示範帳號上線前要改為正式身分驗證、角色權限與伺服器 Session。知識庫不得放密鑰或不必要個資；對外服務需限制場址資料存取並留下稽核紀錄。"],
  ["手機與離線作業", "手機戶外操作、PWA 與離線待同步", ["手機", "PWA", "離線地圖", "待同步", "戶外操作"], "戶外流程應提供大按鈕、弱網提示、離線地圖與本機待同步佇列。同步時要有重試、衝突處理、操作者與時間戳；未上傳成功前不可顯示為後端已完成。"],
  ["台中展示範圍", "台中場址與公園路線的展示範圍", ["台中", "公園", "路線", "18 個場景", "展示範圍"], "目前展示聚焦台中 18 個公園／綠地場景，另保留逢甲一期掃描作流程參考。路線顯示已盤點只表示有可開啟資料，不等於所有資料都已完成現場實測。"],
  ["部署與成本", "Azure GPT 部署、費用開關與服務失敗降級", ["Azure", "GPT", "費用", "部署", "本機降級"], "雲端 GPT 只有在 endpoint、模型部署與明確費用開關都完成時才呼叫；憑證不得提交版本庫。Azure 無法使用時應切換成本機證據回答，並告知使用者目前不是雲端生成結果。"],
];

const frames = [
  "請說明「{topic}」的正確原則。", "在 Arbor3D 中，「{topic}」應該怎麼處理？",
  "如果承辦人問到「{topic}」，系統應如何回答？", "進行台中樹木盤點時，「{topic}」要注意什麼？",
  "使用 RAG＋GPT 分析時，「{topic}」的判斷規則是什麼？", "Power BI 報表涉及「{topic}」時，正確做法為何？",
  "現場作業要處理「{topic}」前，需要先確認哪些資料？", "如何避免在「{topic}」上做出錯誤結論？",
  "政府展示提到「{topic}」時，應揭露哪些限制？", "若要把「{topic}」納入正式成果，還缺哪些證據？",
];

const situations = [
  ["請以一般盤點情境回答。", "一般情境仍要保留來源、日期與可追溯證據。"],
  ["假設目前只有單次掃描。", "若只有單次掃描，不得延伸宣稱真實跨期成長。"],
  ["假設資料包含季度展示情境。", "包含展示資料時，必須保留 simulated 標記並與 observed 分開。"],
  ["假設尚未完成人工複核。", "尚未人工複核時，只能提出待確認結果與下一步，不能把模型輸出當真值。"],
  ["假設答案將用於政府簡報。", "用於政府簡報時，應同步呈現資料來源、樣本數、限制與待補證據。"],
];

const records = [];
for (const [topicIndex, [category, topic, keywords, baseAnswer]] of topics.entries()) {
  for (const [frameIndex, frame] of frames.entries()) {
    for (const [situationIndex, [scenario, qualifier]] of situations.entries()) {
      const serial = topicIndex * 50 + frameIndex * 5 + situationIndex + 1;
      records.push({
        id: `ARBOR-QA-${String(serial).padStart(4, "0")}`,
        category,
        question: `${frame.replace("{topic}", topic)}${scenario}`,
        answer: `${baseAnswer}${qualifier}`,
        keywords,
        dataset_kind: "curated_reference",
        review_status: "policy_grounded",
      });
    }
  }
}

if (records.length !== 1000) throw new Error(`Expected 1000 records, received ${records.length}`);
if (new Set(records.map((record) => record.question)).size !== records.length) throw new Error("Questions must be unique");
fs.writeFileSync(target, `${records.map((record) => JSON.stringify(record)).join("\n")}\n`, "utf8");
console.log(`Wrote ${records.length} questions to ${target}`);
