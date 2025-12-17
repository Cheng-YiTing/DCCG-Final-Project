import json

from compas.colors import Color, ColorMap
from compas.geometry import Box, Frame, Sphere
from compas_viewer import Viewer

from data_structures import FactoryLayout, Machine
from visualize import machines_to_geometry


# ============================================================
# 視覺設定
# ============================================================
TILE_SIZE = (2.4, 2.4, 0.08)      # 薄地板 (x, y, z)
MACHINE_SIZE = (1.6, 1.6, 1.6)    # 機台 (x, y, z)
GAP_X = 0.25                      # 欄間距（左右）
GAP_Y = 0.25                      # 列間距（上下）

# 工件球
WORKPIECE_RADIUS = 0.35
WORKPIECE_COLOR = Color.from_rgb255(255, 230, 50)

# Heatmap（柔和灰藍 → 暖紅）
HEAT_LOW = Color.from_rgb255(176, 196, 222)   # light steel blue
HEAT_HIGH = Color.from_rgb255(240, 128, 128)  # light coral
MACHINE_ALPHA = 0.40


# ============================================================
# 讀設定檔
# ============================================================

def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# Layout helper
# ============================================================

def get_types_order(config):
    """依 machines 出現順序蒐集 type，保持欄位順序穩定。"""
    types = []
    for m in config.get("machines", []):
        if isinstance(m, str):
            t = m
        else:
            t = m.get("type") or m.get("name")
        if t not in types:
            types.append(t)
    return types


def group_machines_by_type(config, types_order):
    """把 machines 分組成 {type: [machine_dict, ...]}。

    兼容兩種格式：
    - 舊格式：machines = ["加工機1", "加工機2", ...]（會把 name=type）
    - 新格式：machines = [{"name":..., "type":..., "speed":...}, ...]

    建議你現在都用「新格式」。
    """
    out = {t: [] for t in types_order}

    for m in config.get("machines", []):
        if isinstance(m, str):
            name = m
            t = m
            speed = 1.0
            out.setdefault(t, []).append({"name": name, "type": t, "speed": speed})
        else:
            name = m["name"]
            t = m.get("type") or name
            speed = float(m.get("speed", 1.0))
            out.setdefault(t, []).append({"name": name, "type": t, "speed": speed})

    # 保持每一欄由上到下順序穩定
    for t in out:
        out[t].sort(key=lambda mm: mm["name"])

    return out


def make_grid_positions(types_order, rows):
    """回傳 {(type, row_index): (x,y,0)}

    - 欄：type（由左到右）
    - 列：同一 type 的第幾台（由上到下）

    row_index = 0 代表最上面。
    """
    col_step = TILE_SIZE[0] + GAP_X
    row_step = TILE_SIZE[1] + GAP_Y

    # 讓整個網格置中
    ncols = len(types_order)
    x0 = -0.5 * (ncols - 1) * col_step
    y0 = 0.5 * (rows - 1) * row_step

    pos = {}
    for ci, t in enumerate(types_order):
        x = x0 + ci * col_step
        for r in range(rows):
            y = y0 - r * row_step
            pos[(t, r)] = (x, y, 0.0)
    return pos


def build_layout_by_type_grid(config):
    """把機台擺成「欄=機台種類，列=同種機台的第幾台(上下)」。

    回傳：layout, types_order, rows, grid_pos
    """
    layout = FactoryLayout()

    types_order = get_types_order(config)
    machines_by_type_dict = group_machines_by_type(config, types_order)

    rows = max((len(lst) for lst in machines_by_type_dict.values()), default=1)
    grid_pos = make_grid_positions(types_order, rows)

    # z：機台站在 tile 上
    tile_thickness = TILE_SIZE[2]
    machine_height = MACHINE_SIZE[2]
    machine_center_z = tile_thickness / 2.0 + machine_height / 2.0

    for t in types_order:
        machines = machines_by_type_dict.get(t, [])
        for r, m in enumerate(machines):
            x, y, _ = grid_pos[(t, r)]
            position = (x, y, machine_center_z)

            name = m["name"]
            speed = float(m.get("speed", 1.0))
            mtype = m.get("type", t)

            machine = Machine(name, position, MACHINE_SIZE, mtype=mtype, speed=speed)
            layout.add_machine(machine)

    return layout, types_order, rows, grid_pos


# ============================================================
# Heatmap loading（目前先回傳 0，之後可改成：指派次數 / 等候時間 / utilization）
# ============================================================

def compute_machine_loads_zero(layout):
    return {name: 0.0 for name in layout.machines.keys()}


# ============================================================
# 回合制工件（不管路徑重疊，直接直線移動到目標機台中心）
# ============================================================

class WorkpieceAgent:
    def __init__(self, wid, route_steps, layout, viewer, color, start_pos, move_speed=4.0):
        self.wid = wid
        self.route_steps = route_steps
        self.layout = layout
        self.viewer = viewer
        self.color = color
        self.move_speed = move_speed

        self.step_index = 0
        self.state = "need_assign"   # need_assign / moving / processing / finished
        self.current_machine = None
        self.process_remaining = 0.0

        self.pos = list(start_pos)  # [x,y,z]
        self.target_pos = list(start_pos)

        self.current_obj = None
        self._draw()

    def current_step(self):
        if self.step_index >= len(self.route_steps):
            return None
        return self.route_steps[self.step_index]

    def _draw(self):
        # COMPAS 2.15：穩定作法：移除舊物件、重建新球
        if self.current_obj is not None:
            self.viewer.scene.remove(self.current_obj)

        f = Frame((self.pos[0], self.pos[1], self.pos[2]), (1, 0, 0), (0, 1, 0))
        sphere = Sphere(radius=WORKPIECE_RADIUS, frame=f)
        self.current_obj = self.viewer.scene.add(
            sphere,
            name=f"wp_{self.wid}",
            surfacecolor=self.color,
            show_lines=True,
        )

    def try_assign(self, now, machines_by_type):
        step = self.current_step()
        if step is None:
            self.state = "finished"
            print(f"{self.wid} 完成所有工序")
            return

        target_type = step["type"]
        candidates = machines_by_type.get(target_type, [])

        chosen = None
        for m in candidates:
            if m.busy_until <= now:
                chosen = m
                break

        if chosen is None:
            return  # 本回合沒機台空

        self.current_machine = chosen

        base = float(step.get("duration", 1.0))
        actual = base / max(float(getattr(chosen, "speed", 1.0)), 1e-6)

        chosen.busy_until = now + actual
        self.process_remaining = actual

        x, y, z = chosen.position
        self.target_pos = [x, y, z + 0.1]

        print(
            f"{self.wid} 指派到：{chosen.name} "
            f"(type={chosen.type}, speed={chosen.speed})｜加工時間：{actual:.2f}s"
        )

        self.state = "moving"

    def step(self, dt, now, machines_by_type):
        if self.state == "finished":
            return

        if self.state == "need_assign":
            return

        if self.state == "moving":
            # 直線靠近 target（簡單但清楚）
            alpha = min(1.0, self.move_speed * dt)
            for i in range(3):
                self.pos[i] += (self.target_pos[i] - self.pos[i]) * alpha

            self._draw()

            if all(abs(self.pos[i] - self.target_pos[i]) < 0.03 for i in range(3)):
                self.state = "processing"
            return

        if self.state == "processing":
            self.process_remaining -= dt
            if self.process_remaining <= 0:
                self.step_index += 1
                if self.step_index >= len(self.route_steps):
                    self.state = "finished"
                    print(f"{self.wid} 完成所有工序")
                else:
                    self.state = "need_assign"
            return


# ============================================================
# 主程式
# ============================================================

def main():
    config = load_config()

    # 1) 依 type-grid 建立 layout
    layout, types_order, rows, grid_pos = build_layout_by_type_grid(config)

    # 2) 回合制派工用：machines_by_type（由上到下順序：name 排序）
    machines_by_type = {}
    for m in layout.machines.values():
        machines_by_type.setdefault(m.type, []).append(m)
    for t in machines_by_type:
        machines_by_type[t].sort(key=lambda mm: mm.name)

    # 3) heatmap loads（先全部 0）
    machine_loads = compute_machine_loads_zero(layout)

    # 4) viewer
    viewer = Viewer(rendermode="shaded")

    # --------------------------------------------------------
    # A. 畫「合併地板」：每一欄(type)一整塊，往下覆蓋 rows 格
    # --------------------------------------------------------
    row_step = TILE_SIZE[1] + GAP_Y
    merged_y = rows * TILE_SIZE[1] + (rows - 1) * GAP_Y

    for t in types_order:
        # 欄中心 x：取 (t,0) 的位置
        x, _, _ = grid_pos[(t, 0)]
        center = (x, 0.0, 0.0)

        tile = Box(
            frame=Frame(center, (1, 0, 0), (0, 1, 0)),
            xsize=TILE_SIZE[0],
            ysize=merged_y,
            zsize=TILE_SIZE[2],
        )

        viewer.scene.add(
            tile,
            name=f"Tile_{t}",
            surfacecolor=Color.from_rgb255(235, 235, 235),
            show_lines=True,
            show_points=False,
        )

    # --------------------------------------------------------
    # B. 畫機台 box（依 load 著色，可透）
    # --------------------------------------------------------
    loads_values = list(machine_loads.values())
    min_load = min(loads_values) if loads_values else 0.0
    max_load = max(loads_values) if loads_values else 1.0
    if max_load == min_load:
        max_load = min_load + 1.0

    cmap = ColorMap.from_two_colors(HEAT_LOW, HEAT_HIGH)

    machine_boxes = machines_to_geometry(layout)
    for name, box in machine_boxes.items():
        load = machine_loads.get(name, 0.0)
        color = cmap(load, minval=min_load, maxval=max_load)
        color.a = MACHINE_ALPHA

        viewer.scene.add(
            box,
            name=f"{name} (load={load:.1f})",
            surfacecolor=color,
            show_lines=True,
            show_points=False,
        )

    # --------------------------------------------------------
    # C. 產生工件（quantity 會產生多顆）
    #    起點：放在最左側一個 staging 區（不在地板上）
    # --------------------------------------------------------
    ncols = max(len(types_order), 1)
    col_step = TILE_SIZE[0] + GAP_X
    staging_x = -0.5 * (ncols - 1) * col_step - (TILE_SIZE[0] * 0.9)
    staging_z = (TILE_SIZE[2] / 2.0) + (MACHINE_SIZE[2] / 2.0) + 0.1

    agents = []
    products = config.get("products", [])

    for p in products:
        pname = p.get("name", "P")
        qty = int(p.get("quantity", 1))
        route_steps = p.get("route", [])  # [{"type":..., "duration":...}, ...]

        for k in range(qty):
            wid = f"{pname}-{k+1}"
            # y 方向稍微錯開，避免全部疊在一起（不做碰撞，只是視覺好看）
            start_pos = (staging_x, 0.4 * k, staging_z)
            agent = WorkpieceAgent(
                wid,
                route_steps,
                layout,
                viewer,
                WORKPIECE_COLOR,
                start_pos=start_pos,
                move_speed=4.0,
            )
            agents.append(agent)

    print("types_order:", types_order)
    print("rows:", rows)
    print("總工件數:", len(agents))

    # --------------------------------------------------------
    # D. 動畫更新（回合制）
    # --------------------------------------------------------
    sim_time = 0.0

    @viewer.on(interval=50)
    def update(frame):
        nonlocal sim_time
        dt = 0.05
        sim_time += dt

        # -----------------------------
        # Phase 1: 先讓正在加工的工件扣時間、完成就離開（釋放機台）
        # -----------------------------
        for a in agents:
            if a.state == "processing":
                a.step(dt, sim_time, machines_by_type)

        # -----------------------------
        # Phase 2: 再讓需要指派的工件進站（此時機台已經釋放）
        # -----------------------------
        for a in agents:
            if a.state == "need_assign":
                a.try_assign(sim_time, machines_by_type)

        # -----------------------------
        # Phase 3: 最後處理移動（畫面更新）
        # -----------------------------
        for a in agents:
            if a.state == "moving":
                a.step(dt, sim_time, machines_by_type)

        viewer.renderer.update()

    viewer.show()


if __name__ == "__main__":
    main()