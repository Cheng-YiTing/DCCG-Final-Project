# Factory Layout Visualization System  
## 2×3 Grid-Based Machine Layout + Loading Heatmap + Flow Path Animation

本系統是一個 **基於 2×3 空間格子的工廠佈置與流程視覺化平台**。  
使用者可以自行設定：

- 每個區塊放置的機台
- 各種工件的加工流程（經過哪些機台）
- 每種工件的需求量（Loads）

系統會在 3D 視覺化環境中展示：

- 機台在 2×3 工廠格子中的佈局
- 每台機台依照生產負荷（loading）呈現不同顏色熱度
- 工件加工流程以折線（polyline）方式連結經過的機台
- 工件球沿著路徑折線動態移動的動畫

本專案結合 **幾何建模（geometric modeling）**、  
**流程視覺化（flow visualization）** 與 **動態模擬（animation）**，  
可用於課程示範、作業研究與工廠配置教學。

---

## 1. System Overview / 系統簡介

### 1.1 功能摘要

- 📦 **2×3 工廠佈局（Fixed Grid Layout）**  
  - 工廠平面被離散成 6 個可配置區塊（slots），座標固定。  
  - 每個 slot 可放 0–1 台機台，最多 6 台機台。

- 🌡 **Loading 熱度圖（Heatmap on Machines）**  
  - 根據工件需求量與流程，計算每台機台的 loading。  
  - loading 越高，機台 Box 顏色越接近紅色；loading 低則偏藍綠。

- 🔗 **加工流程折線視覺化（Flow Polyline）**  
  - 工件流程 route 會被轉換為一條折線，  
    依序連結經過的機台位置，顯示動線長度與交錯情形。

- ⚙️ **工件沿路徑動畫（Path Animation）**  
  - 每個工件對應一顆球（sphere），沿折線逐段移動。  
  - 透過線性插值（interpolation）展示工件在工廠中的流動。

---

## 2. File Structure / 專案檔案結構

```text
Final-Project/
│
├── config.html         # 使用者網頁介面：輸入機台配置與工件流程，產生 config.json
├── config.json         # 系統設定檔，由 config.html 產生
│
├── grid_viewer.py      # 主視覺化程式：2×3 佈局 + Heatmap + Polyline + 動畫
├── data_structures.py  # FactoryLayout、Machine、ProductAgent 等資料結構
├── visualize.py        # 幾何生成工具：Box、Polyline 等
│
└── README.md           # 本說明文件
