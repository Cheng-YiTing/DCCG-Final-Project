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