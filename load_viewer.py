import json

from compas.colors import Color, ColorMap
from compas_viewer import Viewer

from data_structures import FactoryLayout, Machine
from visualize import machines_to_geometry


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_layout_from_config(config):
    """依照 config 裡的 machines 清單，沿 X 軸排機台"""
    layout = FactoryLayout()
    machines = config["machines"]

    for i, name in enumerate(machines):
        x = i * 4.0              # 機台之間距離
        position = (x, 0.0, 0.0)
        size = (2.0, 2.0, 2.0)   # 先固定機台大小
        layout.add_machine(Machine(name, position, size))

    return layout


def compute_machine_loads(config):
    """
    根據每種工件的流程 route + 需求量 quantity，
    計算『每台機台總共被使用多少次（加權）』。
    """
    machines = config["machines"]
    products = config["products"]

    loads = {m: 0.0 for m in machines}

    for p in products:
        qty = float(p.get("quantity", 0))
        route = p["route"]

        # 每經過一站，把該機台的 load 加上這個工件的需求量
        for m in route:
            if m not in loads:
                # route 裡如果打錯機台名稱，就跳過，避免 KeyError
                continue
            loads[m] += qty

    return loads


def main():
    # 1. 讀取設定檔
    config = load_config()

    # 2. 建立 layout（只看機台位置即可）
    layout = build_layout_from_config(config)

    # 3. 計算每台機台的 loading
    machine_loads = compute_machine_loads(config)

    # 4. 轉成 Box 幾何
    boxes = machines_to_geometry(layout)

    # 5. 建立顏色映射：load 小 = 冷色，load 大 = 暖色
    nonzero = [v for v in machine_loads.values()]
    if nonzero:
        min_load = min(nonzero)
        max_load = max(nonzero)
    else:
        min_load = max_load = 0.0

    # 避免所有 load 都一樣時除以 0
    if max_load == min_load:
        max_load = min_load + 1.0

    # 用藍到紅的漸層
    cmap = ColorMap.from_two_colors(Color.from_rgb255(0, 180, 255),   # 較低 load：藍綠
                                    Color.from_rgb255(255, 0, 0))     # 較高 load：紅

    # 6. 開 viewer，把機台畫出來，顏色依照 loading
    viewer = Viewer(rendermode="shaded")

    print("=== 機台 loading 分析 ===")
    for name, box in boxes.items():
        load = machine_loads.get(name, 0.0)
        color = cmap(load, minval=min_load, maxval=max_load)

        viewer.scene.add(
            box,
            name=f"{name} (load={load:.1f})",
            surfacecolor=color,
            show_lines=True,
            show_points=False,
        )

        print(f"{name}: load = {load:.1f}")

    print(f"min load = {min_load:.1f}, max load = {max_load:.1f}")
    print("顏色越偏紅代表 loading 越重\n")

    viewer.show()


if __name__ == "__main__":
    main()