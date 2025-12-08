import json

from compas.colors import Color, ColorMap
from compas.geometry import Box, Frame, Polyline, Sphere
from compas_viewer import Viewer

from data_structures import FactoryLayout, Machine
from visualize import machines_to_geometry


# ------------------------------------------------------------
# 讀設定檔
# ------------------------------------------------------------
def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------
# 2×3 slot 固定座標（中心點）
# 編號方式：
#   1  2  3
#   4  5  6
# ------------------------------------------------------------
SLOT_POSITIONS = {
    "1": (-3.0,  1.5, 0.0),
    "2": ( 0.0,  1.5, 0.0),
    "3": ( 3.0,  1.5, 0.0),
    "4": (-3.0, -1.5, 0.0),
    "5": ( 0.0, -1.5, 0.0),
    "6": ( 3.0, -1.5, 0.0),
}

# 扁扁地板格子（tile）大小 & 機台 box 大小
TILE_SIZE = (2.4, 2.4, 0.08)      # 很薄的地板
MACHINE_SIZE = (1.6, 1.6, 1.6)    # 你設定的正方體機台


# ------------------------------------------------------------
# 根據 config["machines"] 建立 2×3 佈局的 FactoryLayout
# 機台中心放在 tile 上方（站在地板上）
# ------------------------------------------------------------
def build_layout_2x3(config):
    layout = FactoryLayout()

    machines = config.get("machines", [])

    tile_center_z = 0.0
    tile_thickness = TILE_SIZE[2]
    machine_height = MACHINE_SIZE[2]

    # 機台中心 z = tile 上表面 + 機台高度一半
    machine_center_z = tile_center_z + tile_thickness / 2.0 + machine_height / 2.0

    # 最多 6 台，多的先忽略
    for i, name in enumerate(machines[:6]):
        slot_index = str(i + 1)
        tile_pos = SLOT_POSITIONS[slot_index]

        # 機台位置：x、y 跟 tile 一樣，z 提高
        position = (tile_pos[0], tile_pos[1], machine_center_z)

        machine = Machine(name, position, MACHINE_SIZE)
        layout.add_machine(machine)

    return layout


# ------------------------------------------------------------
# loading 計算：根據 route + quantity
# ------------------------------------------------------------
def compute_machine_loads(config):
    machines = config.get("machines", [])
    products = config.get("products", [])

    loads = {m: 0.0 for m in machines}

    for p in products:
        qty = float(p.get("quantity", 0))
        route = p.get("route", [])

        for m in route:
            if m not in loads:
                continue
            loads[m] += qty

    return loads


# ------------------------------------------------------------
# 將每個 product 的 route 轉成：
#   - points：沿流程的 3D 座標（用來給工件方塊跑）
#   - polyline：用來畫灰色流程線
# 灰線「穿過機台中心」（z = 機台中心高度）
# ------------------------------------------------------------
def build_route_polylines(config, layout):
    products = config.get("products", [])

    machine_positions = {
        name: m.position for name, m in layout.machines.items()
    }

    polylines = []

    for idx, p in enumerate(products):
        name = p.get("name", f"product_{idx}")
        route = p.get("route", [])

        points = []

        for m_name in route:
            if m_name not in machine_positions:
                # route 裡如果有打錯機台名稱就略過
                continue

            x, y, z_center = machine_positions[m_name]

            # 讓流程線穿過機台中間
            z = z_center
            points.append([x, y, z])

        if len(points) >= 2:
            poly = Polyline(points)
            polylines.append((name, points, poly))

    return polylines


# ------------------------------------------------------------
# 沿折線移動的工件 Agent（COMPAS 2.15：每幀重新建立 Box）
# ------------------------------------------------------------
class PathAgent:
    def __init__(self, name, points, viewer, color, speed=0.2):
        self.name = name
        self.points = points
        self.viewer = viewer
        self.color = color
        self.speed = speed

        self.segment_index = 0
        self.t = 0.0
        self.finished = False

        # 在路徑起點建立第一個球（稍微抬高一點）
        x, y, z = self.points[0]
        z += 0.1
        origin_frame = Frame((x, y, z), (1, 0, 0), (0, 1, 0))

        sphere = Sphere(radius=0.35, frame=origin_frame)

        self.current_obj = self.viewer.scene.add(
            sphere,
            name=f"agent_{self.name}",
            surfacecolor=self.color,
        )

    def step(self, dt):
        if self.finished:
            return

        if self.segment_index >= len(self.points) - 1:
            self.finished = True
            return

        p0 = self.points[self.segment_index]
        p1 = self.points[self.segment_index + 1]

        self.t += self.speed * dt

        if self.t >= 1.0:
            self.t = 0.0
            self.segment_index += 1

            if self.segment_index >= len(self.points) - 1:
                self.finished = True
                return

            p0 = self.points[self.segment_index]
            p1 = self.points[self.segment_index + 1]

        x = (1 - self.t) * p0[0] + self.t * p1[0]
        y = (1 - self.t) * p0[1] + self.t * p1[1]
        z = (1 - self.t) * p0[2] + self.t * p1[2] + 0.1

        # 移除舊物件
        self.viewer.scene.remove(self.current_obj)

        # 建立新球
        new_frame = Frame((x, y, z), (1, 0, 0), (0, 1, 0))
        new_sphere = Sphere(radius=0.35, frame=new_frame)

        self.current_obj = self.viewer.scene.add(
            new_sphere,
            name=f"agent_{self.name}",
            surfacecolor=self.color,
        )

# ------------------------------------------------------------
# 主程式
# ------------------------------------------------------------
def main():
    # 1. 讀設定檔
    config = load_config()

    # 2. 建立 2×3 佈局
    layout = build_layout_2x3(config)

    # 3. loading（heatmap 用）
    machine_loads = compute_machine_loads(config)

    # 4. Viewer
    viewer = Viewer(rendermode="shaded")

    # --------------------------------------------------------
    # 4-1. 畫出 6 塊扁扁灰格子（當地板）
    # --------------------------------------------------------
    for slot_index, pos in SLOT_POSITIONS.items():
        frame = Frame(pos, [1, 0, 0], [0, 1, 0])
        tile = Box(
            frame=frame,
            xsize=TILE_SIZE[0],
            ysize=TILE_SIZE[1],
            zsize=TILE_SIZE[2],
        )

        viewer.scene.add(
            tile,
            name=f"Slot {slot_index}",
            surfacecolor=Color.from_rgb255(235, 235, 235),
            show_lines=True,
            show_points=False,
        )

    # --------------------------------------------------------
    # 4-2. 準備 loading 熱度圖顏色（方案 B：柔和灰藍 → 暖紅）
    # --------------------------------------------------------
    loads_values = list(machine_loads.values())
    if loads_values:
        min_load = min(loads_values)
        max_load = max(loads_values)
    else:
        min_load = max_load = 0.0

    if max_load == min_load:
        max_load = min_load + 1.0

    cmap = ColorMap.from_two_colors(
        Color.from_rgb255(176, 196, 222),   # light steel blue
        Color.from_rgb255(240, 128, 128),   # light coral
    )

    # --------------------------------------------------------
    # 4-3. 畫出機台 box（顏色依 loading）
    # --------------------------------------------------------
    machine_boxes = machines_to_geometry(layout)

    for name, box in machine_boxes.items():
        load = machine_loads.get(name, 0.0)
        color = cmap(load, minval=min_load, maxval=max_load)

        viewer.scene.add(
            box,
            name=f"{name} (load={load:.1f})",
            surfacecolor=color,
            show_lines=True,
            show_points=False,
        )

    # --------------------------------------------------------
    # 4-4. 畫出每種工件的流程折線（灰色，穿過機台中間）
    # --------------------------------------------------------
    routes = build_route_polylines(config, layout)

    for pname, points, poly in routes:
        viewer.scene.add(
            poly,
            name=f"Route: {pname}",
            linecolor=Color.from_rgb255(150, 150, 150),
            linewidth=3,
        )

    # --------------------------------------------------------
    # 4-5. 建立沿路徑移動的工件方塊 Agent
    # --------------------------------------------------------
    agents = []

    for idx, (pname, points, poly) in enumerate(routes):
        if not points:
            continue

        # 直接用機台中心的路徑點（PathAgent 裡面自己加 0.1 的高度）
        agent_points = points

        col = Color.from_rgb255(255, 230, 50)  # 亮黃，清楚易見

        agent = PathAgent(pname, agent_points, viewer, col, speed=0.2)
        agents.append(agent)

    print(f"建立了 {len(agents)} 個工件 Agent")

    # --------------------------------------------------------
    # 動畫更新：每 50ms 執行一次
    # --------------------------------------------------------
    @viewer.on(interval=50)
    def update(frame):
        dt = 0.05
        for agent in agents:
            agent.step(dt)
        # 強制刷新畫面
        viewer.renderer.update()

    # --------------------------------------------------------
    # 印出佈局資訊（這段只要在 show 之前跑一次，不要放進 update）
    # --------------------------------------------------------
    print("2×3 佈局：")
    for slot_index, pos in SLOT_POSITIONS.items():
        found = [
            mname for mname, m in layout.machines.items()
            if abs(m.position[0] - pos[0]) < 1e-6 and abs(m.position[1] - pos[1]) < 1e-6
        ]
        if found:
            print(f"Slot {slot_index}: {found[0]}  (load={machine_loads.get(found[0], 0):.1f})")
        else:
            print(f"Slot {slot_index}: （空）")

    # --------------------------------------------------------
    # 啟動 viewer（放在最後一句）
    # --------------------------------------------------------
    viewer.show()


if __name__ == "__main__":
    main()