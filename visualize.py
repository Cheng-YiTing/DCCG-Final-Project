from compas.geometry import Box, Frame
from compas.geometry import Sphere

def machines_to_geometry(layout):
    geometry = {}

    for name, machine in layout.machines.items():
        x, y, z = machine.position
        w, d, h = machine.size

        frame = Frame([x, y, z], [1, 0, 0], [0, 1, 0])

        box = Box(frame=frame, xsize=w, ysize=d, zsize=h)

        geometry[name] = box

    return geometry

def create_agent_geometry(agent):
    # 工件用球表示
    sphere = Sphere(radius=0.5, point=agent.position)
    return sphere