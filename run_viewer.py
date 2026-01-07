import os
import sys
import subprocess
import importlib.util
import traceback

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_PATH = os.path.join(PROJECT_DIR, "requirements.txt")
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.json")
VIS_SHOW_PATH = os.path.join(PROJECT_DIR, "visualization.py")


def pause_if_needed():
    """
    Windows使用者常會用雙擊執行，避免視窗一閃就關掉。
    macOS/Linux 從終端執行時不強制pause。
    """
    if sys.platform.startswith("win"):
        try:
            input("\n按 Enter 鍵結束...")
        except EOFError:
            pass


def run_cmd(cmd, cwd=PROJECT_DIR):
    """執行指令並即時輸出"""
    print(f"\n[執行指令] {' '.join(cmd)}\n")
    process = subprocess.Popen(cmd, cwd=cwd)
    return process.wait()


def ensure_python_version():
    if sys.version_info < (3, 8):
        print("Python 版本過低：建議使用 Python 3.8 以上。")
        print(f"你目前版本：{sys.version}")
        return False
    print(f"Python 版本：{sys.version.split()[0]}")
    return True


def package_installed(pkg_name):
    """
    檢查某套件是否已安裝。
    """
    return importlib.util.find_spec(pkg_name) is not None


def ensure_requirements():
    """
    檢查必要套件是否安裝，若沒安裝則自動 pip install -r requirements.txt
    """
    if not os.path.exists(REQUIREMENTS_PATH):
        print("找不到 requirements.txt，請確認檔案存在於專案根目錄。")
        return False

    required_pkgs = ["compas", "compas_viewer"]

    missing = [p for p in required_pkgs if not package_installed(p)]
    if not missing:
        print("必要套件已安裝：compas, compas_viewer")
        return True

    print("偵測到缺少套件：", ", ".join(missing))
    print("將自動安裝 requirements.txt 中的套件...")

    cmd = [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_PATH]
    code = run_cmd(cmd)

    if code != 0:
        print("套件安裝失敗，請檢查網路或權限設定。")
        print("你可以嘗試以下指令：")
        print(f"  {sys.executable} -m pip install --user -r requirements.txt")
        return False

    print("套件安裝完成。")
    return True


def ensure_config_exists():
    """
    確認 config.json 存在
    """
    if os.path.exists(CONFIG_PATH):
        print("已找到 config.json")
        return True

    print("找不到 config.json")
    print("\n請依照以下步驟產生並放回專案資料夾：")
    print("1) 打開 config.html")
    print("2) 設定機台與工件加工流程")
    print("3) 下載 config.json")
    print("4) 將下載的 config.json 移到專案根目錄（與 visualization.py 同一層）")
    return False


def ensure_visualization_exists():
    if os.path.exists(VIS_SHOW_PATH):
        print("已找到 visualization.py")
        return True

    print("找不到 visualization.py，請確認檔案存在於專案根目錄。")
    return False


def run_visualization():
    """
    直接使用同一個Python執行visualization.py
    """
    print("\n開始執行視覺化...可能需要等待幾秒鐘，請稍候...")
    cmd = [sys.executable, VIS_SHOW_PATH]
    return run_cmd(cmd)


def main():
    print("================================")
    print(" Factory Layout Viewer Launcher ")
    print("================================")

    try:
        if not ensure_python_version():
            pause_if_needed()
            return

        if not ensure_visualization_exists():
            pause_if_needed()
            return

        if not ensure_config_exists():
            pause_if_needed()
            return

        if not ensure_requirements():
            pause_if_needed()
            return

        code = run_visualization()
        if code == 0:
            print("\n視覺化程式已結束。")
        else:
            print("\n視覺化程式執行失敗，返回碼：", code)

    except Exception:
        print("\n發生未預期錯誤：")
        traceback.print_exc()

    pause_if_needed()


if __name__ == "__main__":
    main()