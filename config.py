"""ChArUco 标定板与项目路径配置"""

from pathlib import Path

# 项目根目录
ROOT = Path(__file__).resolve().parent

# 标定结果保存路径
CALIBRATION_FILE = ROOT / "calibration.npz"
BOARD_IMAGE_FILE = ROOT / "charuco_board.png"

# ChArUco 板参数（单位：米）
# 5x7 板适合 A4 纸打印，方格 40mm，标记 30mm
SQUARES_X = 5
SQUARES_Y = 7
SQUARE_LENGTH = 0.04
MARKER_LENGTH = 0.03

# ArUco 字典
ARUCO_DICT = "DICT_6X6_250"

# 摄像头索引（若打不开可改为 1、2）
CAMERA_INDEX = 0

# Windows 下推荐使用 DirectShow 后端
CAMERA_BACKEND = "DSHOW"

# 标定采集帧数
CALIBRATION_MIN_FRAMES = 15
