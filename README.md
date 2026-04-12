# VisionAOI

[閱讀繁體中文版](#繁體中文版) | [Read in English](#english-version)

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)

---

<div id="繁體中文版"></div>

## 繁體中文版

VisionAOI 是一個簡單地模擬製造業產線設計的自動光學檢測（AOI）監控平台。本專案將深度學習推論引擎與視覺化面板結合，旨在協助產線端執行即時影像檢測、產出定位熱力圖，並讓品管單位能有效量化與覆判過殺（Overkill）與漏檢（Escape）指標。

### 核心特色
* **多重角色權限管控**：嚴格劃分 IT 管理員（帳號管理）、品管主管（類別與覆判管理）與線上操作員（執行推論）的工作區。
* **多樣化檢測類別支援**：開箱即用，支援 15 種標準 MVTec AD 檢測類別。
* **即時推論與熱力圖**：即時執行影像推論，並提供原始影像與瑕疵定位熱力圖的並排比對。
* **過殺與漏檢分析**：自動追蹤誤報與漏檢，並透過戰情面板視覺化呈現。
* **報表生成**：一鍵匯出檢測紀錄 (CSV) 與統計分佈圖表 (PNG)。
* **容器化部署**：提供隨插即用的 Docker 設定，確保環境一致性。
* **雲端資料集整合**：將龐大的原始影像與 `.pt`/`.pth` 權重檔分離，託管於 Hugging Face。

### 系統需求
* **Python**: 3.9 或以上版本 (用於本機端執行)
* **Docker**: Docker Engine 20.x 或以上版本 / Docker Desktop
* **作業系統**: macOS, Linux, 或 Windows (建議使用 WSL2)

**驗證環境：**
```bash
python3 --version       # 應 >= 3.9
docker --version        # 應輸出 Docker 版本
docker compose version  # 應輸出 Compose V2 版本
```

### 系統功能與角色權限
本系統將操作層級分為三類：
* **IT 管理員 (Admin)**：負責新增系統帳號、設定初始密碼與分配員工職位，不干涉產線運作 (`admin.html`)。
* **品管主管 (Manager)**：負責新增產品檢測類別、處理影像辨識模型誤判報表的覆判作業（確認為真瑕疵或過殺放行） (`manager.html`)。
* **線上操作員 (Operator)**：負責機台前端系統操作。執行單次或自動連續抽樣，即時監控推論信心分數、原圖與瑕疵熱力圖比對，並可匯出當前檢測報表 (`index.html`)。

### 系統架構與特色
* **多樣化檢測類別支援**：系統內建相容 15 種標準 MVTec AD 檢測類別（包含 Bottle, Cable, Hazelnut, Transistor 等）。
* **前後端分離架構**：
  * **前端**：無須編譯的原生 HTML/JS 搭配 TailwindCSS，輕量且易於維護。
  * **後端**：基於 FastAPI 開發的非同步 API，具備高併發處理能力。
* **內建 AI 訓練管線**：提供完整的 `train.py` 與 `testing.py` 腳本，方便後續進行模型微調與權重更新。

### 目錄結構
```text
.
├── app/
│   ├── backend/         # 模型推論與訓練腳本
│   ├── frontend/        # 前端靜態頁面 (操作員/主管/IT)
│   ├── results/         # 推論熱力圖與結果暫存區
│   ├── database.py      # 資料庫連線與 Table 定義
│   └── main.py          # FastAPI 路由入口
├── dataset/             # 原始測試影像資料集
├── weights/             # 模型權重檔
├── Dockerfile           
└── docker-compose.yml   
```

> **資料集與權重說明**：為維持版控系統效能， `dataset/` 與 `weights/` 資料夾已設定忽略上傳。在本機端啟動前，請務必手動將影像與模型權重檔放回對應目錄。
> 
> 下載連結如下：
> [[Link](https://huggingface.co/datasets/Lucas0611/Vision_AOI/tree/main/)]

### 資料庫與環境配置
本系統預設採用輕量級 SQLite 作為資料庫。若需部署至正式環境並切換為 PostgreSQL 或 MySQL，請修改 `app/database.py` 中的連線設定，或在專案根目錄建立 `.env` 檔來覆寫環境變數。

### 快速啟動

**Docker 容器化部署**
```bash
docker-compose up -d --build
```
啟動後，請開啟瀏覽器造訪 `http://localhost:8000` 進入系統，或前往 `http://localhost:8000/docs` 檢視 API 說明文件。

### 清理與解除安裝
如果您想從系統中完全移除本專案、資料庫與 Docker 容器：
```bash
# 停止並移除容器、網路與儲存區 (volumes)
docker compose down -v

# 移除建置的映像檔 (選用)
docker rmi visionaoi-vision-aoi-app

# 刪除專案資料夾
cd ..
rm -rf Code  # 或您自訂的專案資料夾名稱
```

### 常見問題排除

**"Cannot Login / User Not Found" (無法登入 / 找不到使用者)**
* **問題**：您手動將使用者寫入 SQLite 資料庫，但密碼未經過 Bcrypt 加密。
* **解決方案**：請務必使用 IT 管理後台 (`admin.html`) 來建立使用者，以便後端能正確對密碼進行加密處理。

**"Port 8000 Already in Use" (Port 8000 已被佔用)**
* **問題**：其他服務正在佔用 FastAPI 的 Port。
* **解決方案**：終止使用 port 8000 的處理程序 (在 Mac/Linux 系統上使用 `lsof -ti:8000 | xargs kill -9`)，或更改 `docker-compose.yml` 中的對應設定 (例如改為 `"8080:8000"`)。

**"No Images Found for Category" (找不到該類別的影像)**
* **問題**：系統找不到用於推論的影像。
* **解決方案**：請確認您已從 Hugging Face 下載資料集，並將其精確地放置在 `./dataset/<類別名稱>/` 的目錄結構中。

---
Built with FastAPI, Docker, and vanilla JS.

</div>

---

<div id="english-version"></div>

## English Version

VisionAOI is an Automated Optical Inspection (AOI) monitoring platform that simply simulates manufacturing production line designs. This project combines a deep learning inference engine with a visual dashboard, aiming to assist the production line in executing real-time image inspection, generating defect localization heatmaps, and enabling the quality assurance department to effectively quantify and review Overkill and Escape metrics.

### Features
* **Multi-Role Access Control**: Strictly segregated workspaces for IT Admins (account management), QA Managers (category & review management), and Line Operators (inference execution).
* **Multi-Class Support**: Out-of-the-box support for 15 standard MVTec AD defect categories.
* **Real-time Inference & Heatmaps**: Instant execution with side-by-side original raw image and defect locating heatmap comparisons.
* **Overkill & Escape Analysis**: Automated tracking and dashboard visualization of false alarms and missed defects.
* **Report Generation**: One-click CSV export for inspection logs and PNG export for statistical distribution charts.
* **Containerized Deployment**: Ready-to-run Docker setup ensures environment consistency.
* **Cloud Dataset Integration**: Heavy raw images and `.pt`/`.pth` weights are decoupled and hosted on Hugging Face.

### System Requirements
* **Python**: Version 3.9 or higher (for local execution)
* **Docker**: Docker Engine 20.x or higher / Docker Desktop
* **Operating System**: macOS, Linux, or Windows (WSL2 recommended)

**Verify Environment:**
```bash
python3 --version       # Should be >= 3.9
docker --version        # Should output Docker version
docker compose version  # Should output Compose V2 version
```

### System Features & Role Permissions
This system divides operational levels into three categories:
* **IT Administrator (Admin)**: Responsible for adding system accounts, setting initial passwords, and assigning employee roles, without interfering with production line operations (`admin.html`).
* **QA Manager (Manager)**: Responsible for adding new product inspection categories and handling the review process of image recognition model misjudgment reports (confirming true defects or releasing overkill alarms) (`manager.html`).
* **Line Operator (Operator)**: Responsible for frontend machine system operations. Executes single or automated continuous sampling, monitors real-time inference confidence scores, compares original images with defect heatmaps, and can export current inspection reports (`index.html`).

### System Architecture & Features
* **Diverse Inspection Category Support**: The system has built-in compatibility for 15 standard MVTec AD inspection categories (including Bottle, Cable, Hazelnut, Transistor, etc.).
* **Decoupled Frontend/Backend Architecture**:
  * **Frontend**: Native HTML/JS with TailwindCSS, requiring no compilation, lightweight and easy to maintain.
  * **Backend**: Asynchronous API developed with FastAPI, featuring high concurrency processing capabilities.
* **Built-in AI Training Pipeline**: Provides complete `train.py` and `testing.py` scripts to facilitate subsequent model fine-tuning and weight updates.

### Directory Structure
```text
.
├── app/
│   ├── backend/         # Model inference and training scripts
│   ├── frontend/        # Frontend static pages (Operator/Manager/IT)
│   ├── results/         # Temp storage for inference heatmaps and results
│   ├── database.py      # Database connection and table definitions
│   └── main.py          # FastAPI application entry point
├── dataset/             # Raw test image dataset
├── weights/             # Model weight files
├── Dockerfile           
└── docker-compose.yml   
```

> **Note on Data & Weights**: To maintain version control system performance, the `dataset/` and `weights/` directories have been ignored for upload. Before starting locally, please ensure you manually place the images and model weight files back into their respective directories.
> 
> **Download Links:**
> [[Link](https://huggingface.co/datasets/Lucas0611/Vision_AOI/tree/main/)]

### Database & Environment Configuration
The system uses lightweight SQLite as the default database. If you need to deploy to a production environment and switch to PostgreSQL or MySQL, please modify the connection settings in `app/database.py`, or create a `.env` file in the project root directory to override the environment variables.

### Quick Start

**Docker Container Deployment**
```bash
docker-compose up -d --build
```
After starting, please open your browser and visit `http://localhost:8000` to access the system, or go to `http://localhost:8000/docs` to view the API documentation.

### Cleanup and Uninstallation
If you want to completely remove the project, database, and Docker containers from your system:
```bash
# Stop and remove containers, networks, and volumes
docker compose down -v

# Remove the built image (optional)
docker rmi visionaoi-vision-aoi-app

# Delete the project directory
cd ..
rm -rf Code  # Or whatever your project folder is named
```

### Troubleshooting

**"Cannot Login / User Not Found"**
* **Problem**: You manually inserted a user into the SQLite database, but the password wasn't Bcrypt-hashed.
* **Solution**: Always use the Admin dashboard (`admin.html`) to create users so the backend can properly hash the passwords.

**"Port 8000 Already in Use"**
* **Problem**: Another service is occupying the FastAPI port.
* **Solution**: Kill the process using port 8000 (`lsof -ti:8000 | xargs kill -9` on Mac/Linux), or change the mapping in `docker-compose.yml` (e.g., `"8080:8000"`).

**"No Images Found for Category"**
* **Problem**: The system cannot find the images for inference.
* **Solution**: Ensure you have downloaded the dataset from Hugging Face and placed it precisely in the `./dataset/<category_name>/` structure.

---
Built with FastAPI, Docker, and vanilla JS.

</div>
