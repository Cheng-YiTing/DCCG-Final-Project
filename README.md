🏭 Factory Layout Visualization System
2×3 Grid-Based Machine Layout + Loading Heatmap + Flow Path Animation

本系統為一個 基於 2×3 空間格子的工廠佈置與流程視覺化平台，
使用者可以自行設定機台擺放區塊、工件加工流程與需求量，
系統將在 3D 視覺化環境中展示：

機台在 2×3 工廠格子中的佈局

每台機台依照生產負荷（loading）呈現不同顏色熱度

工件加工流程以折線（polyline）方式連結經過的機台

工件球沿著路徑折線動態移動的動畫

本系統整合 幾何建模、流程視覺化與動態模擬，
可作為製程分析、動線規劃、設備配置教學與展示用途。

✨ 系統特色
🔶 1. 2×3 工廠佈局（Fixed Grid Layout）

工廠平面被離散成六個可配置區塊（slots），座標固定，最多可放六台機台。
使用者可以決定：

slot 1 → 想放哪一台機台  
slot 2 → 想放哪一台機台  
...  
slot 6 → 想放哪一台機台


此功能可快速模擬不同機台佈局方式。

🔶 2. Loading 熱度圖（Heatmap on Machines）

系統依據工件輸入的需求量（quantity）計算各機台的使用頻率（loading）。

loading 高 → 顏色偏紅

loading 低 → 顏色偏藍綠

使用者可快速看出瓶頸機台。

🔶 3. 加工流程折線視覺化（Flow Polyline）

工件的加工流程會轉換為一條灰色折線（polyline），
依序連結工件經過的每一個機台。

可分析：

動線長度

交叉複雜度

流程結構

🔶 4. 工件沿路徑動畫（Path Animation）

每個工件會生成一顆球（sphere），沿著 polyline 線段平滑移動。
動畫採用線性插值（interpolation），展現工件生產動態。

📁 系統結構
Final-Project/
│
├── config.html         # 使用者介面：輸入機台配置與工件流程
├── config.json         # 系統設定檔（由 config.html 產生）
│
├── grid_viewer.py      # 主視覺化程式（2×3 Grid + Heatmap + Polyline + 動畫）
├── data_structures.py  # Layout、Machine、Agent 等資料結構
├── visualize.py        # 幾何生成工具（Box、Polyline）
│
└── README.md           # 本文件

📄 config.json 格式
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
    }
  ]
}

🔧 幾何建模（Geometry Modeling）
1. Slot 位置（固定）

六個格子對應以下座標：

slot 1: (-4,  2, 0)
slot 2: ( 0,  2, 0)
slot 3: ( 4,  2, 0)
slot 4: (-4, -2, 0)
slot 5: ( 0, -2, 0)
slot 6: ( 4, -2, 0)

2. 機台 Box

放在 slot 中央

顏色依 loading 而定

名稱、Label 會顯示在 viewer 中

3. 加工折線（Polyline）

工件流程 → 一連串座標點 → polyline。
Z 軸可略微提升避免與 Box 重疊。

🎬 工件動畫（Path Animation）

每個工件一顆 sphere

根據 polyline 線段計算位置

線性插值更新座標

流程結束後可停止或循環

▶️ 使用步驟
1. 編輯 config.html

輸入：

six slots 的機台名稱

工件流程 route

工件需求量

點按按鈕產生 config.json。

2. 執行視覺化
python grid_viewer.py


即可看到：

2×3 機台佈局

loading 顏色熱圖

流程折線

工件沿線動畫
