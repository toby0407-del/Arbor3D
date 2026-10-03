# Arbor3D Docker

此封裝包含 React production build、正式 Node API、上傳、人工量測儲存、盤點媒體及本機 RAG。預設 `full` 映像另含 Python、Open3D、CPU PyTorch、YOLO v1/v2/v3 權重及正式量測管線。`web` 映像提供介面、快速盤點、圖片產製與本機 AI，正式 YOLO 量測需要 `full`。

## Windows 啟動

首次執行會建立 D 槽資料夾並複製倉庫內的示範／實測媒體；不覆蓋後續新成果。

```powershell
.\Start-Arbor3D.cmd
# 僅建置介面版：
powershell -ExecutionPolicy Bypass -File scripts/docker-start.ps1 -Target web
```

網站：<http://localhost:8080>。可直接使用示範登入，無需 Azure 金鑰。服務預設僅開放本機；需要區域網路存取時才將 `.env.docker` 的 `ARBOR3D_BIND_ADDRESS` 設為 `0.0.0.0`。

`.env.docker` 不會進 Git 或映像；現有 `.env.local` 也不會被複製進去。雲端登入、Cosmos DB、Azure AI 需另外填入實際設定。Entra 的 `VITE_` 公開識別設定在建置時使用，修改後必須重建。

## Linux / 其他電腦

```sh
cp docker/env.example .env.docker
# 修改 ARBOR3D_STORAGE_ROOT 為本機絕對路徑，例如 /srv/arbor3d
mkdir -p /srv/arbor3d/{inbox,scans,data,cache,runtime}
cp -an app/public/scans/. /srv/arbor3d/scans/
# 映像以 uid 1000 執行，掛載資料夾須可寫入
sudo chown -R 1000:1000 /srv/arbor3d
docker compose --env-file .env.docker up -d --build --wait
```

需要 Docker Compose 2.24+（支援選用 env_file）。Dockerfile 預設最後一層為完整 CPU 量測版；可用 `docker build --target web -t arbor3d:web .` 建置介面版。完整版映像與首次建置需要數 GB 空間與下載時間。

## 永久資料

預設位置 `D:/Arbor3D-work/storage`：

| 資料夾 | 內容 |
| --- | --- |
| inbox | 上傳原始檔、工作狀態、量測輸出 |
| runtime | 人工量測與稽核資料 |
| scans | 示範媒體、新盤點 JSON／影像／模型及路徑綁定 |
| data | 正式管線建立的 3D_treedata、去噪點雲與完整高斯 |
| cache | 模型及 Matplotlib 快取 |

`ARBOR3D_DATA_ROOT=/data` 讓容器內管線使用 D 槽掛載資料，不依賴原本桌面的絕對路徑。既有大量掃描資料維持原位置；透過介面匯入新工作即可，不會把整個原始資料集塞进映像。

```powershell
docker compose --env-file .env.docker logs -f
docker compose --env-file .env.docker down
docker compose --env-file .env.docker up -d --wait
docker save -o D:\Arbor3D-work\arbor3d-image.tar arbor3d:local
```

`down`／重建不刪除這五個資料夾；備份時停止服務後備份它們與 `.env.docker`。登入 Session 在記憶體，重啟後需重新登入。CPU 量測比 GPU 慢；本封裝不包含 GPU 訓練環境。

## 本機環境限制（2026-10-03）

這台 Windows 電腦偵測到 `VirtualizationFirmwareEnabled=False`、`HypervisorPresent=False`，原本亦未安裝 WSL。Linux 容器需要先在 BIOS/UEFI 啟用 Intel VT-x／AMD SVM，再啟用 WSL 2；BIOS 設定無法由一般 Windows 程式直接完成。

Docker Desktop 安裝檔位於 `D:\Arbor3D-work\installers`。安裝與 WSL 虛擬磁碟應指定 D 槽：

```powershell
# 硬體虛擬化啟用後，管理員 PowerShell 執行：
wsl --install --no-distribution
# 需要時重新啟動，再安裝：
Start-Process 'D:\Arbor3D-work\installers\Docker Desktop Installer.exe' -Wait -ArgumentList 'install','--user','--quiet','--accept-license','--backend=wsl-2','--installation-dir=D:\DockerDesktop','--wsl-default-data-root=D:\DockerData'
```

官方前置需求與安裝參數：<https://docs.docker.com/desktop/setup/install/windows-install/>。
