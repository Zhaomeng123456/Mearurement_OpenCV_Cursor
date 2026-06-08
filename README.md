# Measurement OpenCV Cursor

基于 OpenCV 与 ChArUco 标定板的桌面测量项目，用于完成相机标定、平面两点测距，以及标定板图片生成。

## 项目简介

本项目主要面向以下使用场景：

- 使用 **Basler 工业相机**（默认）或 USB 摄像头识别 ChArUco 标定板
- 采集多帧图像完成相机标定
- 在与标定板同一平面上点击两个点，计算实际距离
- 通过图形界面完成标定、测量和标定板生成
- 通过命令行快速执行常见功能

项目默认使用 **Basler 工业相机**（通过 `pypylon`），也支持切换回普通 USB 摄像头。测量结果依赖于标定质量，以及待测点与标定板是否处于同一平面。

## 主要功能

- 图形界面模式
  - 实时预览 Basler 工业相机 / USB 摄像头画面
  - 切换距离测量 / 相机标定 / 标定板工具
  - 点击画面中的两个点进行平面距离测量
- 命令行模式
  - 列出已连接的 Basler 相机
  - 生成 ChArUco 标定板
  - 运行标定流程
  - 运行测距流程
- 相机模块（`camera.py`）
  - `BaslerCamera`：基于 pypylon 的工业相机取图
  - `OpenCVCamera`：基于 OpenCV 的 USB 摄像头取图
  - 统一 `read()` / `isOpened()` / `release()` 接口
- ChArUco 工具模块
  - 标定板创建
  - 多策略检测与角点匹配
  - 相机标定结果保存与加载
  - 位姿估计与图像点反投影到板平面
- 独立标定板生成器
  - 位于 `CreatChArUcoboard/`
  - 支持预览并导出 PNG / PDF 标定板

## 项目结构

```text
.
├── README.md                    # 项目说明
├── main.py                      # 主入口，支持 GUI / 命令行
├── gui.py                       # 图形界面
├── calibrate.py                 # 命令行标定流程
├── measure.py                   # 命令行测距流程
├── charuco_utils.py             # ChArUco 检测、标定与测量工具
├── camera.py                    # 相机抽象层（Basler / OpenCV）
├── config.py                    # 项目配置
├── requirements.txt             # 主项目依赖
└── CreatChArUcoboard/
    ├── main.py                  # 独立标定板生成器 GUI
    └── requirements.txt         # 生成器依赖
```

## 运行环境

- Python 3.10 及以上
- **Basler 工业相机** + [Basler Pylon SDK](https://www.baslerweb.com/en/downloads/software-downloads/)（默认）
- 或支持 OpenCV 的本地 USB 摄像头（将 `CAMERA_TYPE` 改为 `"opencv"`）
- 推荐在 Windows 或 Linux 桌面环境下运行

主项目依赖如下：

- `opencv-contrib-python>=4.8.0`
- `numpy>=1.24.0`
- `Pillow>=9.0.0`
- `pypylon>=3.0.0`（Basler 相机）

## 安装依赖

### 1. 安装 Basler Pylon（默认相机模式）

从 [Basler 官网](https://www.baslerweb.com/en/downloads/software-downloads/) 下载并安装 Pylon 运行时，版本需与 `pypylon` 匹配。安装后可用 **Pylon Viewer** 验证相机能否正常取图。

### 2. 安装 Python 依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

### 3. 确认相机连接

```bash
python main.py cameras
```

输出示例：

```text
已连接的 Basler 相机:
  [0] acA2440-20gc  序列号: 40123456  (Basler acA2440-20gc)
```

若未检测到设备，请检查网线/USB 连接、驱动安装及相机供电。

### 4. 独立标定板生成器（可选）

```bash
pip install -r CreatChArUcoboard/requirements.txt
```

## 快速开始

### 0. 配置相机（首次使用）

编辑 `config.py`，按需调整 Basler 参数。常见场景：

| 场景 | 建议配置 |
|------|----------|
| 单台相机，自动曝光 | 保持默认即可 |
| 多台相机 | 设置 `BASLER_SERIAL_NUMBER` 为目标序列号 |
| 固定光照环境 | `BASLER_EXPOSURE_AUTO = "Off"`，设置 `BASLER_EXPOSURE_TIME_US` |
| 黑白工业相机 | `BASLER_PIXEL_FORMAT = "Mono8"`（程序自动转 BGR） |
| 切换回 USB 摄像头 | `CAMERA_TYPE = "opencv"` |

### 1. 启动图形界面

```bash
python main.py
```

或：

```bash
python main.py gui
```

图形界面提供三个模式：

- 距离测量
- 相机标定
- 标定板工具

### 2. 生成标定板

```bash
python main.py board
```

程序会在项目根目录生成：

- `charuco_board.png`

建议将该图片按实际尺寸打印，并贴在平整硬板上使用。

### 3. 进行相机标定

```bash
python main.py calibrate
```

标定时建议：

- 采集不少于 15 帧
- 从不同角度、不同距离观察标定板
- 保证光照均匀、对焦清晰
- 标定板尽量覆盖画面较大区域
- 工业相机建议先通过 Pylon Viewer 调好曝光与对焦

标定完成后会生成：

- `calibration.npz`

### 4. 进行距离测量

```bash
python main.py measure
```

使用说明：

- 先保证已经完成相机标定
- 将标定板与待测物体放在同一平面
- 在开始时使用标定板锁定一次参考平面
- 锁定后可以移走标定板，但相机与被测平面必须保持不动
- 鼠标点击两个点后读取距离结果

## 命令行参数

`main.py` 支持以下命令：

```bash
python main.py            # 默认启动图形界面
python main.py gui        # 启动图形界面
python main.py board      # 生成 ChArUco 标定板图片
python main.py calibrate  # 相机标定（命令行）
python main.py measure    # 两点测距（命令行）
python main.py cameras    # 列出已连接的 Basler 相机
python main.py --help     # 查看帮助
```

## 关键配置

配置文件位于 `config.py`。

### ChArUco 标定板

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SQUARES_X` / `SQUARES_Y` | 5 / 7 | 标定板网格数量 |
| `SQUARE_LENGTH` | 0.04 | 棋盘格边长（米） |
| `MARKER_LENGTH` | 0.03 | ArUco 标记边长（米） |
| `ARUCO_DICT` | `DICT_6X6_250` | ArUco 字典类型 |
| `CALIBRATION_MIN_FRAMES` | 15 | 最少标定帧数 |

### Basler 工业相机（`CAMERA_TYPE = "basler"`）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CAMERA_TYPE` | `"basler"` | 相机类型 |
| `BASLER_SERIAL_NUMBER` | `""` | 序列号，留空则连接第一台 |
| `BASLER_EXPOSURE_AUTO` | `"Continuous"` | 曝光模式：`"Off"` / `"Once"` / `"Continuous"` |
| `BASLER_EXPOSURE_TIME_US` | `None` | 手动曝光时间（微秒），仅 `ExposureAuto = "Off"` 时生效 |
| `BASLER_GAIN` | `None` | 增益，`None` 为相机默认值 |
| `BASLER_PIXEL_FORMAT` | `"BGR8"` | 像素格式，常见：`"BGR8"` / `"Mono8"` / `"RGB8"` |
| `BASLER_WIDTH` / `BASLER_HEIGHT` | `None` | 分辨率，`None` 为相机默认值 |
| `BASLER_FRAME_RATE` | `None` | 目标帧率，`None` 为不限制 |
| `BASLER_GRAB_TIMEOUT_MS` | `5000` | 取图超时（毫秒） |

### USB 摄像头（`CAMERA_TYPE = "opencv"`）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CAMERA_INDEX` | `0` | 摄像头设备索引 |
| `CAMERA_BACKEND` | `"DSHOW"` | OpenCV 后端（Windows 推荐 DirectShow） |
| `CAMERA_WIDTH` / `CAMERA_HEIGHT` | 1280 / 720 | 请求分辨率 |

### 故障排查

如果 Basler 相机无法打开：

1. 运行 `python main.py cameras` 查看已连接设备
2. 在 Pylon Viewer 中确认相机可正常取图
3. 多台相机时，在 `config.py` 中设置正确的 `BASLER_SERIAL_NUMBER`
4. 确认 Pylon 运行时版本与 `pypylon` 兼容

如需切换回 USB 摄像头，将 `CAMERA_TYPE` 改为 `"opencv"`，并视情况调整 `CAMERA_INDEX`。

## 输出文件

程序运行过程中可能生成以下文件：

- `charuco_board.png`：打印用标定板图片
- `calibration.npz`：相机标定参数

## 测量原理说明

项目通过以下流程完成测量：

1. 检测 ChArUco 标定板角点
2. 根据多帧样本进行相机标定，得到内参与畸变参数
3. 在测量阶段估计标定板位姿
4. 将图像中的点击点反投影到标定板所在平面
5. 计算两个平面点之间的欧氏距离

因此，测量结果适用于与标定板共面的目标，不适用于脱离该平面的三维空间直接测距。

## 独立标定板生成器

`CreatChArUcoboard/` 目录下包含一个独立 GUI 工具，用于：

- 选择不同 ArUco 字典
- 自定义板尺寸和格子数量
- 预览标定板
- 导出 PNG
- 导出 PDF

运行方式：

```bash
python CreatChArUcoboard/main.py
```

## 注意事项

- 更换相机（Basler ↔ USB 或不同型号）后需重新标定
- 打印标定板时不要缩放，否则实际尺寸会失真
- 测距前必须完成标定并加载 `calibration.npz`
- 测量时标定板与待测点应保持同一平面
- 光照、曝光、清晰度和标定板占画面比例会显著影响检测效果
- 工业相机建议使用固定支架，避免测量过程中相机位移

## 后续可扩展方向

- 增加标定结果可视化
- 增加测量结果保存功能
- 支持更多标定板参数配置
- 支持批量图片标定与离线测量
- 支持通过 GUI 直接调整 Basler 曝光与增益
