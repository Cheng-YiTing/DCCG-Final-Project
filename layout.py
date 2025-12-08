from data_structures import FactoryLayout, Machine
from data_structures import ProductFlow

def create_default_layout():
    layout = FactoryLayout()

    # 定義三台機台：加工 → 檢查 → 包裝
    machines = [
        Machine("加工機", (0, 0, 0), (2, 2, 2)),
        Machine("檢查機", (5, 0, 0), (2, 2, 2)),
        Machine("包裝機", (10, 0, 0), (2, 2, 2)),
    ]

    for m in machines:
        layout.add_machine(m)

    return layout

def create_default_flow():
    flow = ProductFlow(
        "產品A",
        steps=[
            {"machine": "加工機", "duration": 2},
            {"machine": "檢查機", "duration": 2},
            {"machine": "包裝機", "duration": 2},
        ]
    )
    return flow