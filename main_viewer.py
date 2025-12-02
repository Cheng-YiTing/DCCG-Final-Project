from layout import create_default_layout
from visualize import machines_to_geometry

from compas_viewer import Viewer


def main():
    # 建立工廠 layout（包含三台機台）
    layout = create_default_layout()

    # 把機台轉成 Box 幾何
    geometry = machines_to_geometry(layout)

    # 建立 Viewer
    viewer = Viewer()

    # 把每一台機台加到 scene 裡
    for name, box in geometry.items():
        # compas_viewer 2.0 的正確用法：直接把幾何物件丟進 scene.add
        viewer.scene.add(box, name=name)

    # 顯示視窗
    viewer.show()


if __name__ == "__main__":
    main()