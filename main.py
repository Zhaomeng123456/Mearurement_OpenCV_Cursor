"""入口：图形界面 / 命令行"""

import sys

import charuco_utils as cu
from calibrate import run_calibration
from measure import DistanceMeasurer


def print_usage() -> None:
    print("用法:")
    print("  python main.py            启动图形界面（默认）")
    print("  python main.py gui        启动图形界面")
    print("  python main.py board      生成 ChArUco 标定板图片")
    print("  python main.py calibrate  相机标定（命令行）")
    print("  python main.py measure    两点测距（命令行）")
    print("  python main.py cameras    列出已连接的 Basler 相机")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gui"

    if cmd in ("gui", "run", ""):
        from gui import run_gui
        run_gui()
    elif cmd == "board":
        cu.save_board_image()
    elif cmd == "calibrate":
        run_calibration()
    elif cmd == "measure":
        DistanceMeasurer().run()
    elif cmd == "cameras":
        from camera import list_basler_devices

        devices = list_basler_devices()
        if not devices:
            print("未检测到 Basler 相机，请确认 Pylon 驱动已安装且相机已连接")
        else:
            print("已连接的 Basler 相机:")
            for i, dev in enumerate(devices):
                print(f"  [{i}] {dev['model']}  序列号: {dev['serial']}  ({dev['friendly_name']})")
    elif cmd in ("-h", "--help", "help"):
        print_usage()
    else:
        print(f"未知命令: {cmd}")
        print_usage()


if __name__ == "__main__":
    main()
