
import json
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from compas.colors import Color, ColorMap
from compas.geometry import Box, Frame, Sphere
from compas_viewer import Viewer

# ============================================================
# Settings
# ============================================================
TILE_SIZE = (2.6, 1.8, 0.08)      # (x, y, z)
MACHINE_SIZE = (1.4, 1.4, 1.4)

COL_GAP_X = 0.6
ROW_GAP_Y = 0.3

WAIT_GAP_Y = 0.9
MOVE_SPEED = 4.0

DT = 0.05
UPDATE_MS = int(DT * 1000)

PRODUCT_COLORS = [
    Color.from_rgb255(255, 203, 96),
    Color.from_rgb255(144, 224, 239),
    Color.from_rgb255(255, 140, 157),
    Color.from_rgb255(167, 255, 174),
    Color.from_rgb255(199, 180, 255),
    Color.from_rgb255(255, 230, 160),
    Color.from_rgb255(173, 216, 230),
    Color.from_rgb255(255, 182, 193),
    Color.from_rgb255(152, 251, 152),
    Color.from_rgb255(221, 160, 221),
]

# ============================================================
# Data
# ============================================================
@dataclass
class Machine:
    name: str
    mtype: str
    speed: float
    position: Tuple[float, float, float]
    current_wp: Optional[str] = None  # occupied by which workpiece id


@dataclass
class RouteStep:
    mtype: str
    duration: float


# ============================================================
# Config
# ============================================================
def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_machines(config) -> List[Dict]:
    """
    Support:
      - machines: [{name,type,speed}, ...]
      - machine_types: [{type,count,speeds:[...] or speed}, ...]
    """
    if "machines" in config and config["machines"]:
        out = []
        for m in config["machines"]:
            out.append({
                "name": m["name"],
                "type": m.get("type", m["name"]),
                "speed": float(m.get("speed", 1.0))
            })
        return out

    out = []
    for mt in config.get("machine_types", []):
        t = mt["type"]
        count = int(mt.get("count", 1))
        speeds = mt.get("speeds", None)
        base_speed = float(mt.get("speed", 1.0))
        for i in range(count):
            s = float(speeds[i]) if speeds and i < len(speeds) else base_speed
            out.append({"name": f"{t}_{i+1}", "type": t, "speed": s})
    return out


def get_types_order(machines: List[Dict], products: List[Dict]) -> List[str]:
    order = []
    for p in products:
        for st in p.get("route", []):
            t = st["type"]
            if t not in order:
                order.append(t)
    for m in machines:
        if m["type"] not in order:
            order.append(m["type"])
    return order


# ============================================================
# Layout
# ============================================================
def build_layout(machines: List[Dict], types_order: List[str]):
    machines_by_type_raw: Dict[str, List[Dict]] = {t: [] for t in types_order}
    for m in machines:
        machines_by_type_raw.setdefault(m["type"], []).append(m)

    for t in machines_by_type_raw:
        machines_by_type_raw[t].sort(key=lambda x: x["name"])

    rows = max((len(machines_by_type_raw.get(t, [])) for t in types_order), default=1)

    tile_w, tile_h, _ = TILE_SIZE
    col_dx = tile_w + COL_GAP_X
    row_dy = tile_h + ROW_GAP_Y

    grid_pos: Dict[Tuple[str, int], Tuple[float, float, float]] = {}
    for ci, t in enumerate(types_order):
        x = ci * col_dx
        for r in range(rows):
            y = -r * row_dy
            grid_pos[(t, r)] = (x, y, 0.0)

    # machine z: stand on tile
    tile_th = TILE_SIZE[2]
    mch = MACHINE_SIZE[2]
    machine_center_z = tile_th / 2 + mch / 2

    layout: Dict[str, Machine] = {}
    for t in types_order:
        lst = machines_by_type_raw.get(t, [])
        for r, md in enumerate(lst):
            x, y, _ = grid_pos[(t, r)]
            pos = (x, y, machine_center_z)
            layout[md["name"]] = Machine(
                name=md["name"],
                mtype=md["type"],
                speed=float(md["speed"]),
                position=pos
            )

    return layout, machines_by_type_raw, rows, grid_pos


def machines_to_boxes(layout: Dict[str, Machine]):
    boxes = {}
    for name, m in layout.items():
        x, y, z = m.position
        frame = Frame((x, y, z), (1, 0, 0), (0, 1, 0))
        boxes[name] = Box(frame=frame, xsize=MACHINE_SIZE[0], ysize=MACHINE_SIZE[1], zsize=MACHINE_SIZE[2])
    return boxes


def add_merged_tiles(viewer: Viewer, types_order, machines_by_type_raw, grid_pos):
    """
    One merged tile per type, spanning all machines of that type vertically.
    """
    for t in types_order:
        n = max(1, len(machines_by_type_raw.get(t, [])))
        x0, y0, _ = grid_pos[(t, 0)]
        x1, y1, _ = grid_pos[(t, n - 1)]

        cx = x0
        cy = (y0 + y1) / 2
        span_y = abs(y0 - y1)

        big_x = TILE_SIZE[0]
        big_y = TILE_SIZE[1] + span_y

        tile = Box(
            frame=Frame((cx, cy, 0.0), (1, 0, 0), (0, 1, 0)),
            xsize=big_x,
            ysize=big_y,
            zsize=TILE_SIZE[2]
        )
        viewer.scene.add(
            tile,
            name=f"Tile_{t}",
            surfacecolor=Color.from_rgb255(235, 235, 235),
            show_lines=True
        )


# ============================================================
# Agent (Exit-Then-Enter in the same tick)
# ============================================================
class WorkpieceAgent:
    def __init__(self, wid, product_name, route_steps: List[RouteStep],
                 viewer: Viewer, color: Color,
                 wait_anchor, wait_index, finish_anchor, finish_index=0):
        self.wid = wid
        self.product_name = product_name
        self.route = route_steps
        self.viewer = viewer
        self.color = color

        self.step_index = 0
        self.state = "waiting"   # waiting / moving_in / processing / moving_out / finished
        self.machine: Optional[Machine] = None
        self.process_remaining = 0.0

        self.finish_anchor = finish_anchor
        self.finish_index = int(finish_index) if finish_index is not None else 0
        self.finish_gap = 0.9  # 完成區間距

        self.pos = [wait_anchor[0], wait_anchor[1] - wait_index * WAIT_GAP_Y, wait_anchor[2]]
        self.target_pos = self.pos[:]
        self.exit_target = None

        self.obj = None
        self._draw()

    def _draw(self):
        if self.obj is not None:
            self.viewer.scene.remove(self.obj)

        f = Frame((self.pos[0], self.pos[1], self.pos[2]), (1, 0, 0), (0, 1, 0))
        sph = Sphere(radius=0.32, frame=f)
        self.obj = self.viewer.scene.add(sph, name=self.wid, surfacecolor=self.color)

    def current_step(self):
        if self.step_index >= len(self.route):
            return None
        return self.route[self.step_index]

    def _move_towards(self, target, dt):
        alpha = min(1.0, MOVE_SPEED * dt)
        for i in range(3):
            self.pos[i] += (target[i] - self.pos[i]) * alpha
        self._draw()
        return all(abs(self.pos[i] - target[i]) < 0.03 for i in range(3))

    # ---------- Phase A: release / exit ----------
    def phase_release(self, dt):
        if self.state == "processing":
            self.process_remaining -= dt
            if self.process_remaining <= 0:
                self.state = "moving_out"

                if self.step_index >= len(self.route) - 1:
                    self.exit_target = [
                        self.finish_anchor[0],
                        self.finish_anchor[1] - self.finish_index * self.finish_gap,
                        self.finish_anchor[2],
                    ]
                else:
                    mx, my, mz = self.machine.position
                    self.exit_target = [mx + (TILE_SIZE[0] / 2 + 0.9), my, mz + 0.1]

        elif self.state == "moving_out":
            reached = self._move_towards(self.exit_target, dt)
            if reached:
                # free machine immediately
                if self.machine is not None:
                    self.machine.current_wp = None
                self.machine = None
                self.step_index += 1

                if self.step_index >= len(self.route):
                    self.state = "finished"
                    print(f"{self.wid} 完成所有工序")
                else:
                    self.state = "waiting"

    # ---------- Phase B: assign + enter ----------
    def phase_assign_and_move(self, dt, machines_by_type: Dict[str, List[Machine]]):
        if self.state == "finished":
            return

        if self.state == "waiting":
            step = self.current_step()
            if step is None:
                self.state = "finished"
                return

            candidates = machines_by_type.get(step.mtype, [])
            chosen = None
            for m in candidates:
                if m.current_wp is None:
                    chosen = m
                    break

            if chosen is None:
                return

            # reserve
            chosen.current_wp = self.wid
            self.machine = chosen

            actual = step.duration / max(chosen.speed, 1e-6)
            self.process_remaining = actual

            mx, my, mz = chosen.position
            self.target_pos = [mx, my, mz + 0.1]
            self.state = "moving_in"

            print(f"{self.wid} 指派到：{chosen.name} (type={chosen.mtype}, speed={chosen.speed})｜加工時間：{actual:.2f}s")

        if self.state == "moving_in":
            reached = self._move_towards(self.target_pos, dt)
            if reached:
                self.state = "processing"


# ============================================================
# Main
# ============================================================
def main():
    config = load_config()
    machines_raw = normalize_machines(config)
    products = config.get("products", [])

    types_order = get_types_order(machines_raw, products)
    layout, machines_by_type_raw, rows, grid_pos = build_layout(machines_raw, types_order)

    # convert to Machine objects
    machines_by_type: Dict[str, List[Machine]] = {t: [] for t in types_order}
    for t in types_order:
        for md in machines_by_type_raw.get(t, []):
            machines_by_type[t].append(layout[md["name"]])

    viewer = Viewer(rendermode="shaded")

    # merged floor tiles
    add_merged_tiles(viewer, types_order, machines_by_type_raw, grid_pos)

    # machine color by speed
    speeds = [m.speed for m in layout.values()] or [1.0]
    minv, maxv = min(speeds), max(speeds)
    if maxv == minv:
        maxv = minv + 1.0

    cmap = ColorMap.from_two_colors(
        Color.from_rgb255(176, 196, 222),
        Color.from_rgb255(240, 128, 128),
    )

    for name, box in machines_to_boxes(layout).items():
        m = layout[name]
        c = cmap(m.speed, minval=minv, maxval=maxv)
        c.a = 0.35
        viewer.scene.add(box, name=name, surfacecolor=c, show_lines=True)

    # anchors
    xs = [p[0] for p in grid_pos.values()] or [0.0]
    ys = [p[1] for p in grid_pos.values()] or [0.0]
    min_x, max_x = min(xs), max(xs)
    max_y = max(ys)

    wait_anchor = (min_x - 4.0, max_y + 0.5, 1.0)
    finish_anchor = (max_x + 4.0, 0.0, 1.0)

    # agents
    agents: List[WorkpieceAgent] = []
    product_color_map: Dict[str, Color] = {}

    wait_index = 0
    finish_counter = 0
    color_idx = 0

    for p in products:
        pname = p.get("name", f"Product{color_idx + 1}")
        if pname not in product_color_map:
            product_color_map[pname] = PRODUCT_COLORS[color_idx % len(PRODUCT_COLORS)]
            color_idx += 1

        qty = int(p.get("quantity", 1))
        route_steps = [RouteStep(mtype=st["type"], duration=float(st["duration"])) for st in p.get("route", [])]

        for k in range(qty):
            wid = f"{pname}-{k+1}"
            agents.append(
                WorkpieceAgent(
                    wid=wid,
                    product_name=pname,
                    route_steps=route_steps,
                    viewer=viewer,
                    color=product_color_map[pname],
                    wait_anchor=wait_anchor,
                    wait_index=wait_index,
                    finish_anchor=finish_anchor,
                    finish_index=finish_counter,
                )
            )
            wait_index += 1
            finish_counter += 1

    print("總工件數:", len(agents))

    @viewer.on(interval=UPDATE_MS)
    def update(_frame):
        # Phase A: exit first (later steps first)
        for a in sorted(agents, key=lambda x: x.step_index, reverse=True):
            a.phase_release(DT)

        # Phase B: then assign and enter (earlier steps first)
        for a in sorted(agents, key=lambda x: x.step_index):
            a.phase_assign_and_move(DT, machines_by_type)

        viewer.renderer.update()

    viewer.show()


if __name__ == "__main__":
    main()
