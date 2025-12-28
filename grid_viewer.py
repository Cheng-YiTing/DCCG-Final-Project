# grid_viewer.py
# ------------------------------------------------------------
# 完整支援 machine_types 的版本
# 1) config.json 可用 machine_types（type, count, speed 或 speeds）
# 2) 會自動展開成 machines: [{name, type, speed}]
# 3) grid：type 為欄（左到右），同 type 多台為列（上到下）
# 4) 工件：回合制派工 +「後站先出、前站再進」(Exit then Enter) 的視覺順序
# ------------------------------------------------------------

import json
from copy import deepcopy

from compas.colors import Color, ColorMap
from compas.geometry import Box, Frame, Sphere
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
# 視覺大小 / 間距
# ------------------------------------------------------------
TILE_SIZE = (2.4, 2.4, 0.08)
MACHINE_SIZE = (1.6, 1.6, 1.6)

COL_GAP = 3.2
ROW_GAP = 3.2


# ------------------------------------------------------------
# config 轉換：machine_types -> machines
# 支援 speed / speeds
# ------------------------------------------------------------
def expand_machine_types(config):
    cfg = deepcopy(config)

    # 已有 machines 就直接用
    if cfg.get("machines"):
        return cfg

    machine_types = cfg.get("machine_types", [])
    machines = []

    for mt in machine_types:
        t = mt.get("type")
        count = int(mt.get("count", 0))
        if not t or count <= 0:
            continue

        speeds = mt.get("speeds")  # list
        default_speed = float(mt.get("speed", 1.0))

        for i in range(1, count + 1):
            name = f"{t}_{i}"
            if isinstance(speeds, list) and len(speeds) >= i:
                sp = float(speeds[i - 1])
            else:
                sp = default_speed
            machines.append({"name": name, "type": t, "speed": sp})

    cfg["machines"] = machines
    return cfg


# ------------------------------------------------------------
# type 順序：優先用 products.route 的順序
# ------------------------------------------------------------
def get_types_order(config):
    types = []
    for p in config.get("products", []):
        for step in p.get("route", []):
            t = step.get("type")
            if t and t not in types:
                types.append(t)

    for m in config.get("machines", []):
        t = m.get("type")
        if t and t not in types:
            types.append(t)

    return types


def group_machines_by_type(config, types_order):
    machines_by_type = {t: [] for t in types_order}
    for m in config.get("machines", []):
        t = m.get("type", m.get("name"))
        machines_by_type.setdefault(t, []).append(m)
    return machines_by_type


def make_grid_positions(types_order, rows):
    grid_pos = {}
    if not types_order:
        return grid_pos

    total_w = (len(types_order) - 1) * COL_GAP
    x0 = -total_w / 2.0
    y0 = (rows - 1) * ROW_GAP / 2.0

    for ci, t in enumerate(types_order):
        x = x0 + ci * COL_GAP
        for ri in range(rows):
            y = y0 - ri * ROW_GAP
            grid_pos[(t, ri)] = (x, y, 0.0)

    return grid_pos


def build_layout_by_type_grid(config):
    layout = FactoryLayout()

    types_order = get_types_order(config)
    machines_by_type = group_machines_by_type(config, types_order)

    rows = max((len(lst) for lst in machines_by_type.values()), default=1)
    grid_pos = make_grid_positions(types_order, rows)

    tile_thickness = TILE_SIZE[2]
    machine_height = MACHINE_SIZE[2]
    machine_center_z = tile_thickness / 2.0 + machine_height / 2.0

    for t in types_order:
        machines = machines_by_type.get(t, [])
        for r, m in enumerate(machines):
            if (t, r) not in grid_pos:
                continue

            x, y, _ = grid_pos[(t, r)]
            position = (x, y, machine_center_z)

            name = m["name"]
            speed = float(m.get("speed", 1.0))
            mtype = m.get("type", t)

            machine = Machine(name, position, MACHINE_SIZE, mtype=mtype, speed=speed)
            layout.add_machine(machine)

    return layout, types_order, rows, grid_pos


# ------------------------------------------------------------
# loading（先保留簡版 0）
# ------------------------------------------------------------
def compute_machine_loads(config):
    machine_names = [m["name"] for m in config.get("machines", [])]
    return {name: 0.0 for name in machine_names}


# ------------------------------------------------------------
# 工件 Agent：Exit then Enter
# ------------------------------------------------------------
class WorkpieceAgent:
    def __init__(
        self,
        wid,
        route_steps,
        layout,
        viewer,
        color,
        move_speed=3.5,
        wait_anchor=(-6.0, 0.0, 1.0),
        wait_index=0,
    ):
        self.wid = wid
        self.route_steps = route_steps
        self.layout = layout
        self.viewer = viewer
        self.color = color
        self.move_speed = move_speed

        self.step_index = 0
        self.state = "need_assign"  # need_assign / moving / processing / finished
        self.current_machine = None
        self.process_remaining = 0.0
        self.target_pos = None

        # waiting queue position
        self.pos = [wait_anchor[0], wait_anchor[1] - wait_index * 0.8, wait_anchor[2]]

        self.current_obj = None
        self._draw()

    def _draw(self):
        if self.current_obj is not None:
            self.viewer.scene.remove(self.current_obj)

        f = Frame((self.pos[0], self.pos[1], self.pos[2]), (1, 0, 0), (0, 1, 0))
        sphere = Sphere(radius=0.35, frame=f)
        self.current_obj = self.viewer.scene.add(
            sphere, name=f"wp_{self.wid}", surfacecolor=self.color
        )

    def current_step(self):
        if self.step_index >= len(self.route_steps):
            return None
        return self.route_steps[self.step_index]

    # Phase A: release (backward)
    def phase_release(self, dt, now):
        if self.state != "processing":
            return

        self.process_remaining -= dt
        if self.process_remaining > 0:
            return

        # release machine immediately
        if self.current_machine is not None:
            self.current_machine.busy_until = now
            self.current_machine.current_wp = None
            self.current_machine.busy_until = now
            self.current_machine = None

        # next step
        self.step_index += 1
        if self.step_index >= len(self.route_steps):
            self.state = "finished"
            self.pos[2] = 0.8
            self._draw()
            print(f"{self.wid} 完成所有工序")
        else:
            self.state = "need_assign"

    # Phase B: assign + move (forward)
    def phase_assign_and_move(self, dt, now, machines_by_type):
        if self.state == "finished":
            return

        if self.state == "need_assign":
            step = self.current_step()
            if step is None:
                self.state = "finished"
                return

            target_type = step["type"]
            candidates = machines_by_type.get(target_type, [])

            chosen = None
            for m in candidates:
                if m.busy_until <= now and (m.current_wp is None):
                    chosen = m
                    break

            if chosen is None:
                return

            self.current_machine = chosen
            chosen.current_wp = self.wid

            base = float(step.get("duration", 1.0))
            actual = base / max(chosen.speed, 1e-6)

            chosen.busy_until = now + actual
            self.process_remaining = actual

            x, y, z = chosen.position
            self.target_pos = [x, y, z + 0.1]

            print(
                f"{self.wid} 指派到：{chosen.name} (type={chosen.type}, speed={chosen.speed})｜加工時間：{actual:.2f}s"
            )
            self.state = "moving"

        if self.state == "moving":
            if self.target_pos is None:
                self.state = "need_assign"
                return

            alpha = min(1.0, self.move_speed * dt)
            for i in range(3):
                self.pos[i] += (self.target_pos[i] - self.pos[i]) * alpha

            self._draw()

            reached = all(abs(self.pos[i] - self.target_pos[i]) < 0.03 for i in range(3))
            if reached:
                self.state = "processing"
            return


# ------------------------------------------------------------
# 主程式
# ------------------------------------------------------------
def main():
    raw_config = load_config()
    config = expand_machine_types(raw_config)

    if not config.get("machines"):
        raise ValueError("config.json 需要 machines 或 machine_types。")

    layout, types_order, rows, grid_pos = build_layout_by_type_grid(config)

    if not grid_pos:
        raise ValueError("type 列表為空：請確認 products.route 或 machines 有填 type。")

    # machines_by_type
    machines_by_type = {}
    for m in layout.machines.values():
        machines_by_type.setdefault(m.type, []).append(m)
    for t in machines_by_type:
        machines_by_type[t].sort(key=lambda mm: mm.name)

    machine_loads = compute_machine_loads(config)

    viewer = Viewer(rendermode="shaded")

    # draw tiles
    for t in types_order:
        for r in range(rows):
            pos = grid_pos[(t, r)]
            frame = Frame(pos, (1, 0, 0), (0, 1, 0))
            tile = Box(frame=frame, xsize=TILE_SIZE[0], ysize=TILE_SIZE[1], zsize=TILE_SIZE[2])
            viewer.scene.add(
                tile,
                name=f"Tile_{t}_{r+1}",
                surfacecolor=Color.from_rgb255(235, 235, 235),
                show_lines=True,
                show_points=False,
            )

    # colormap
    loads_values = list(machine_loads.values())
    min_load = min(loads_values) if loads_values else 0.0
    max_load = max(loads_values) if loads_values else 1.0
    if max_load == min_load:
        max_load = min_load + 1.0

    cmap = ColorMap.from_two_colors(
        Color.from_rgb255(176, 196, 222),
        Color.from_rgb255(240, 128, 128),
    )

    # draw machines
    machine_boxes = machines_to_geometry(layout)
    for name, box in machine_boxes.items():
        load = machine_loads.get(name, 0.0)
        color = cmap(load, minval=min_load, maxval=max_load)
        color.a = 0.35
        viewer.scene.add(
            box,
            name=f"{name}",
            surfacecolor=color,
            show_lines=True,
            show_points=False,
        )

    # build workpieces
    agents = []
    products = config.get("products", [])

    min_x = min([p[0] for p in grid_pos.values()])
    wait_anchor = (min_x - 4.0, 0.0, 1.0)

    idx_counter = 0
    for p in products:
        pname = p["name"]
        qty = int(p.get("quantity", 1))
        route_steps = p["route"]

        for k in range(qty):
            wid = f"{pname}-{k+1}"
            col = Color.from_rgb255(255, 230, 50)
            agent = WorkpieceAgent(
                wid,
                route_steps,
                layout,
                viewer,
                col,
                move_speed=4.0,
                wait_anchor=wait_anchor,
                wait_index=idx_counter,
            )
            idx_counter += 1
            agents.append(agent)

    print("總工件數:", len(agents))

    # loop
    sim_time = 0.0
    DT = 0.05

    @viewer.on(interval=50)
    def update(frame):
        nonlocal sim_time
        sim_time += DT

        for a in sorted(agents, key=lambda x: x.step_index, reverse=True):
            a.phase_release(DT, sim_time)

        for a in sorted(agents, key=lambda x: x.step_index):
            a.phase_assign_and_move(DT, sim_time, machines_by_type)

        viewer.renderer.update()

    viewer.show()


if __name__ == "__main__":
    main()
