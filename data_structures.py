# 機台資料結構
class Machine:
    def __init__(self, name, position, size):
        """
        name: 機台名稱 (字串)
        position: (x, y, z)
        size: (width, depth, height)
        """
        self.name = name
        self.position = position
        self.size = size

# 產品流程資料結構
class ProductFlow:
    def __init__(self, name, steps):
        """
        steps: list of dict, 每一步包含：
            {
                "machine": "加工機",
                "duration": 5   # 停留時間(秒)
            }
        """
        self.name = name
        self.steps = steps

# 工廠 Layout = 管理所有機台 & 流程
class FactoryLayout:
    def __init__(self):
        self.machines = {}
        self.flows = []

    def add_machine(self, machine: Machine):
        self.machines[machine.name] = machine

    def add_product_flow(self, flow: ProductFlow):
        self.flows.append(flow)

# 產品代理人，負責模擬產品在工廠中的流動
class ProductAgent:
    def __init__(self, name, flow: ProductFlow):
        self.name = name
        self.flow = flow
        self.step_index = 0
        self.position = [0, 0, 0]
        self.finished = False
        self.wait_time = 0
        self.is_waiting = False

    def current_step(self):
        return self.flow.steps[self.step_index]

    def move_to_next_step(self):
        # 還沒走到最後一站，就往下一站
        if self.step_index < len(self.flow.steps) - 1:
            self.step_index += 1
        # 已經在最後一站，而且還沒宣告完成，就印一次就好
        elif not self.finished:
            print(f"{self.name} 已完成所有工序")
            self.finished = True