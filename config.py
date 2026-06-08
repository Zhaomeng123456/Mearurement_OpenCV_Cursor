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

# 相机类型: "basler" 使用 Basler 工业相机, "opencv" 使用普通 USB 摄像头
CAMERA_TYPE = "basler"

# --- Basler 工业相机配置 ---
# 序列号留空则自动连接第一台相机；多台相机时请填写目标序列号
BASLER_SERIAL_NUMBER = ""
# 曝光模式: "Off" / "Once" / "Continuous"；设为 None 且下方曝光时间为 None 时保持相机默认
BASLER_EXPOSURE_AUTO = "Continuous"
# 手动曝光时间（微秒），仅在 BASLER_EXPOSURE_AUTO = "Off" 时生效
BASLER_EXPOSURE_TIME_US = None
# 增益，None 表示使用相机默认值
BASLER_GAIN = None
# 像素格式，常见值: "BGR8", "Mono8", "RGB8"
BASLER_PIXEL_FORMAT = "BGR8"
# 分辨率，None 表示使用相机当前默认值
BASLER_WIDTH = None
BASLER_HEIGHT = None
# 目标帧率，None 表示不限制
BASLER_FRAME_RATE = None
# 取图超时（毫秒）
BASLER_GRAB_TIMEOUT_MS = 5000

# --- OpenCV USB 摄像头配置（CAMERA_TYPE = "opencv" 时生效）---
CAMERA_INDEX = 0
# Windows 下推荐使用 DirectShow 后端
CAMERA_BACKEND = "DSHOW"
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

# 标定采集帧数
CALIBRATION_MIN_FRAMES = 15
