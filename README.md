🏭 Factory Layout Visualization System
2×3 Grid-Based Machine Layout + Loading Heatmap + Flow Path Animation

本系統為一個 基於 2×3 空間格子的工廠佈置與流程視覺化平台，使用者可以自行設定機台擺放區塊、工件加工流程與需求量，系統將在 3D 視覺化環境中展示：

機台在 2×3 工廠格子中的佈局

每台機台依照生產負荷（loading）呈現不同顏色熱度

工件加工流程以折線（polyline）方式連結經過的機台

工件球沿著路徑折線動態移動的動畫

此系統整合 幾何建模、流程視覺化與動態模擬，可作為製程分析、動線規劃、設備配置教學與示範用途。

✨ 系統特色
🔶 1. 2×3 工廠佈局（Fixed Grid Layout）

工廠平面被離散成六個可配置區塊（slots），座標固定，最多可放六台機台。
使用者可以決定：

slot 1 → 想放哪一台機台
slot 2 → 想放哪一台機台
...
slot 6 → 想放哪一台機台


這讓使用者可以快速測試不同佈局。

🔶 2. Loading 熱度圖（Heatmap on Machines）

系統會根據使用者輸入的工件需求量（quantity），計算每台機台的使用頻率。

loading 高 → 顏色偏紅

loading 低 → 顏色偏藍綠

可快速確認哪個機台最繁忙、哪裡可能是瓶頸。

🔶 3. 加工流程折線視覺化（Flow Polyline）

工件的加工順序以灰色折線呈現（polyline），依序連結加工過的機台。
不同工件類型可使用不同顏色或高度，避免重疊。

🔶 4. 工件沿路徑動畫（Path Animation）

每個工件會生成一顆小球，沿折線路徑移動（使用線段插值），形式類似流程模擬：

依照 route 的節點逐段移動

平滑插值（interpolation）

到達一站後換下一站

流程結束後可選擇停止或循環

🔧 技術架構（Modules）
Final-Project/
│
├── config.html         # 使用者介面，產生 config.json
├── config.json         # 儲存機台佈局、流程、需求量的設定檔
│
├── grid_viewer.py      # 主程式，顯示 2×3 佈局 + loading + 折線 + 動畫
├── data_structures.py  # Layout、Machine、ProductAgent 等資料結構
├── visualize.py        # 幾何生成工具（Box、Polyline 等）
│
└── README.md           # 本文件

📁 config.json 格式說明

config.html 會自動產生符合下列格式的設定檔：

{
  "slots": {
    "1": "前處理機",
    "2": "射出成型機",
    "3": "原料乾燥機",
    "4": "",
    "5": "組裝機",
    "6": "品檢機"
  },
  "products": [
    {
      "name": "杯子",
      "route": [
        "前處理機",
        "射出成型機",
        "原料乾燥機",
        "品檢機"
      ],
      "duration": 2,
      "quantity": 300
    },
    {
      "name": "樂高",
      "route": [
        "射出成型機",
        "組裝機",
        "品檢機"
      ],
      "duration": 3,
      "quantity": 150
    }
  ]
}

欄位功能：
欄位	說明
slots	2×3 六個格子放的機台名稱
products	工件種類的設定
route	加工流程依序經過的機台
quantity	該工件在分析中的需求量，用於 loading 計算
duration	每站加工時間（目前不影動畫速度，但保留未來用）
🧱 幾何建模邏輯（Geometry Modeling）
1. Slot 空間座標（固定）

系統預設 6 個固定位置：

slot 1: (-4,  2, 0)
slot 2: ( 0,  2, 0)
slot 3: ( 4,  2, 0)
slot 4: (-4, -2, 0)
slot 5: ( 0, -2, 0)
slot 6: ( 4, -2, 0)


每個 slot 是一個立方體框（淡色），用來表示可放置區域。

2. 機台 Box

使用者輸入哪一格要放什麼機台後：

在該 slot 顯示一個機台 Box（立方體）

Box 的名稱會標記為該機台名稱

Box 的顏色依 loading 而變化

3. Flow Polyline（加工路徑）

工件路徑 route：

["前處理機", "射出成型機", "原料乾燥機", "品檢機"]


會被轉成一串點：

[(x1, y1, 0.2), (x2, y2, 0.2), ...]


再畫成一條折線。

4. Loading Heatmap

依照所有工件的需求量計算每台機台 loading：

loading[machine] = Σ 各工件 quantity（每經過一次就加一次）


mapping 方式：

min → 藍綠

max → 紅

中間做線性插值

🎬 動畫邏輯（工件小球沿線移動）

動畫使用 Viewer 的 interval callback：

每個工件都有一顆球（sphere geometry）

球會根據路徑線段逐段前進

使用線性插值技術計算球座標

更新 transformation 後立即顯示

路徑完成後可停止或重複循環

此動畫讓整個工廠佈局更容易理解其物料流向。

▶️ 執行步驟
1. 打開 config.html

輸入：

slot1–slot6 要放哪些機台

工件名稱、流程、需求量

產生 config.json

2. 執行視覺化
python grid_viewer.py


系統將自動：

顯示 6 格佈局

上色機台 loading

畫出加工折線

播放工件沿線動畫

📌 未來可擴充方向（可寫進報告）

自動計算最佳佈局（利用 Load–Distance 最佳化）

加上機台尺寸、障礙物、通道寬度等更真實之設計

流量強度加上箭頭或動態粒子模擬（vector field）

比較不同 layout 的成本與效率
