from layout import create_default_layout
from visualize import machines_to_geometry

# 建立 layout
layout = create_default_layout()

# 轉成幾何資料（Box）
geometry = machines_to_geometry(layout)

# 印出所有幾何資訊
for name, geo in geometry.items():
    print(f"{name}: {geo}")