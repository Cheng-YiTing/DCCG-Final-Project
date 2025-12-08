import json

from compas.geometry import Sphere, Translation
from compas_viewer import Viewer

from data_structures import FactoryLayout, Machine, ProductFlow, ProductAgent
from visualize import machines_to_geometry


def load_config(path="config.json"):
    """從 config.json 讀取使用者在網頁輸入的設定"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_layout_and_flows(config):
    """依照 config 建立 FactoryLayout 和 多條 ProductFlow"""
    layout = FactoryLayout()

    # 將機台沿 X 軸排開，每台間隔 4 單位
    for i, name in enumerate(config.get("machines", [])):
        x = i * 4.0
        position = (x, 0.0, 0.0)
        size = (2.0, 2.0, 2.0)
        layout.add_machine(Machine(name, position, size))

    # 建立多條產品流程
    flows = []
    for p in config.get("products", []):
        pname = p["name"]
        route = p["route"]
        duration = float(p["duration"])

        steps = [{"machine": mname, "duration": duration} for mname in route]
        flow = ProductFlow(pname, steps)
        flows.append(flow)

    return layout, flows


def main():
    # 1. 讀設定檔（使用者從 config.html 產生）
    config = load_config()

    # 2. 用設定檔建立 layout & flows
    layout, flows = build_layout_and_flows(config)

    # 3. 建立 Viewer
    viewer = Viewer()

    # 4. 把機台 Box 加到 scene 裡
    machine_geo = machines_to_geometry(layout)
    for name, box in machine_geo.items():
        viewer.scene.add(box, name=name)

    # 5. 為每一種流程建立一個工件 agent（最多 3 種）
    lane_offsets = [-1.0, 0.0, 1.0]   # Y 方向錯開，避免球疊在一起
    agents = []
    agent_objects = {}

    for i, flow in enumerate(flows):
        offset = lane_offsets[i % len(lane_offsets)]
        agent = ProductAgent(f"工件-{flow.name}", flow)

        # 一開始就放在第一個機台的前面一點
        first_machine_name = flow.steps[0]["machine"]
        first_machine = layout.machines[first_machine_name]
        start_x = first_machine.position[0] - 2.0
        start_y = first_machine.position[1] + offset
        start_z = first_machine.position[2]
        agent.position = [start_x, start_y, start_z]

        agents.append(agent)

        # 幾何：用球表示工件
        sphere = Sphere(radius=0.5, point=agent.position)
        obj = viewer.scene.add(sphere, name=agent.name)
        agent_objects[agent] = (obj, offset)

    # 6. 動畫：每 0.1 秒更新所有工件位置
    @viewer.on(interval=100)
    def update(frame):
        dt = 0.1

        for agent in agents:
            if agent.finished:
                continue

            step = agent.current_step()
            machine_name = step["machine"]
            duration = step["duration"]
            machine = layout.machines[machine_name]

            obj, offset = agent_objects[agent]

            # 目標位置：機台的位置 + lane offset
            target = [
                machine.position[0],
                machine.position[1] + offset,
                machine.position[2],
            ]

            # 若正在該站「加工 / 等待」，就只倒數時間
            if agent.is_waiting:
                agent.wait_time -= dt
                if agent.wait_time <= 0:
                    agent.is_waiting = False
                    agent.move_to_next_step()
                continue

            # 還在移動中 → 朝目標前進
            for i in range(3):
                agent.position[i] += (target[i] - agent.position[i]) * 0.15

            T = Translation.from_vector(agent.position)
            obj.transformation = T
            obj.update()

            # 判斷是否已抵達該機台
            reached = all(abs(agent.position[i] - target[i]) < 0.05 for i in range(3))
            if reached and not agent.is_waiting:
                # 抵達瞬間輸出訊息
                print(f"{agent.name} 現在位於：{machine_name}，加工時間：{duration} 秒")

                # 啟動加工等待
                agent.is_waiting = True
                agent.wait_time = duration

    viewer.show()


if __name__ == "__main__":
    main()