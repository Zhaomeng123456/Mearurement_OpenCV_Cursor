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
    print("  python main.py calibrate  摄像头标定（命令行）")
    print("  python main.py measure    两点测距（命令行）")


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
    elif cmd in ("-h", "--help", "help"):
        print_usage()
    else:
        print(f"未知命令: {cmd}")
        print_usage()


if __name__ == "__main__":
    main()
