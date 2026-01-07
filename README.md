# DCCG 工廠配置視覺化專案（DCCG Final Project）

本專案旨在將工廠中的機台配置與工件加工流程視覺化，協助使用者快速理解工件在不同機台之間的加工順序、排程行為與資源使用情形。使用者可透過圖形化介面設定機台類型、台數與加工速度，以及工件加工路線並生成設定檔，進一步以 3D 動態模擬方式呈現工件流動與機台效率差異，提升流程規劃、產線溝通與配置決策的效率。
---

## 1. 專案內容概覽

專案根目錄主要檔案如下：

- `config.html`：工廠設定介面（設定機台與工件流程，下載 `config.json`）
- `config.json`：工廠配置檔（由 `config.html` 下載，需放回專案根目錄）
- `visualization.py`：視覺化模擬主程式（讀取 `config.json` 並顯示動畫）
- `run_viewer.py`：跨平台啟動器（自動檢查環境、安裝套件、執行 viewer）
- `requirements.txt`：Python 套件需求清單（compas, compas_viewer）

---

## 2. 環境需求

- Windows 10 / 11 或 macOS
- Python 3（建議 3.8 以上）
- 需要網路連線（第一次安裝套件會用到）

---

## 3. 使用流程（最重要）

### Step 1：下載專案

請從 GitHub 下載並解壓縮，資料夾名稱例如：

`DCCG-Final-Project-main`

---

### Step 2：用 `config.html` 設定工廠並下載 `config.json`

1. 打開 `config.html`
2. 設定以下內容：
   - 機台種類、台數、速度 speed
   - 工件（產品）與加工流程 route
3. 點選「下載 config.json」

#### speed 說明

- speed 越大表示加工越快
- 視覺化會用顏色呈現：藍色較慢、紅色較快

---

### Step 3：把 `config.json` 放回專案根目錄

請將下載到電腦「下載資料夾」的 `config.json` 移動到：

`DCCG-Final-Project-main/`

也就是和 `visualization.py`、`run_viewer.py` 同一層。

---

## 4. 啟動方式（命令列，推薦）

> 本專案採用命令列啟動，確保 Windows/macOS 都能穩定運行，並避免 bat 腳本在部分環境被阻擋。  
> 建議直接在專案資料夾內「右鍵開啟終端機」後執行指令。

---

### 4.1 Windows：在專案資料夾右鍵開啟終端機執行

1. 進入 `DCCG-Final-Project-main` 專案資料夾
2. 在資料夾內空白處 **右鍵**
3. 選擇以下其中一種（依你的 Windows 版本顯示不同）：
   - **在終端機開啟（Open in Terminal）**
   - **在 PowerShell 視窗中開啟（Open PowerShell window here）**
   - **在此處開啟命令提示字元（Open Command Prompt here）**
4. 在終端機中輸入：

```bash
py -3 run_viewer.py
