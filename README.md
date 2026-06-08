# Measurement OpenCV Cursor

基于 OpenCV 与 ChArUco 标定板的桌面测量项目，用于完成相机标定、平面两点测距，以及标定板图片生成。

## 项目简介

本项目主要面向以下使用场景：

- 使用摄像头识别 ChArUco 标定板
- 采集多帧图像完成相机标定
- 在与标定板同一平面上点击两个点，计算实际距离
- 通过图形界面完成标定、测量和标定板生成
- 通过命令行快速执行常见功能

项目默认使用 **Basler 工业相机**（通过 pypylon），也支持切换回普通 USB 摄像头。测量结果依赖于标定质量，以及待测点与标定板是否处于同一平面。

## 主要功能

- 图形界面模式
  - 实时预览相机画面（Basler 工业相机 / USB 摄像头）
  - 切换距离测量 / 相机标定 / 标定板工具
  - 点击画面中的两个点进行平面距离测量
- 命令行模式
  - 生成 ChArUco 标定板
  - 运行标定流程
  - 运行测距流程
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
- Basler 工业相机 + [Basler Pylon SDK](https://www.baslerweb.com/en/downloads/software-downloads/)（默认）
- 或支持 OpenCV 的本地 USB 摄像头（将 `CAMERA_TYPE` 改为 `"opencv"`）
- 推荐在 Windows 或 Linux 桌面环境下运行

主项目依赖如下：

- `opencv-contrib-python>=4.8.0`
- `numpy>=1.24.0`
- `Pillow>=9.0.0`
- `pypylon>=3.0.0`（Basler 相机）

## 安装依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

使用 Basler 相机前，还需安装 Basler Pylon 运行时（与 pypylon 版本匹配），可从 [Basler 官网](https://www.baslerweb.com/en/downloads/software-downloads/) 下载。

连接相机后，可运行以下命令确认设备是否被识别：

```bash
python main.py cameras
```

如果要使用独立标定板生成器，也可以安装其目录下依赖：

```bash
pip install -r CreatChArUcoboard/requirements.txt
```

## 快速开始

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
python main.py cameras    # 列出 Basler 相机
python main.py --help     # 查看帮助
```

## 关键配置

配置文件位于 `config.py`，主要参数包括：

- `SQUARES_X` / `SQUARES_Y`：标定板网格数量
- `SQUARE_LENGTH`：棋盘格边长，单位米
- `MARKER_LENGTH`：ArUco 标记边长，单位米
- `ARUCO_DICT`：ArUco 字典类型
- `CAMERA_TYPE`：相机类型，`"basler"` 或 `"opencv"`
- `BASLER_SERIAL_NUMBER`：Basler 相机序列号（留空则连接第一台）
- `BASLER_EXPOSURE_AUTO` / `BASLER_EXPOSURE_TIME_US`：曝光设置
- `BASLER_GAIN` / `BASLER_PIXEL_FORMAT`：增益与像素格式
- `CAMERA_INDEX` / `CAMERA_BACKEND`：USB 摄像头索引与后端（`opencv` 模式）
- `CALIBRATION_MIN_FRAMES`：最少标定帧数

默认配置为：

- 5 x 7 ChArUco 板
- 方格边长 40 mm
- 标记边长 30 mm
- `DICT_6X6_250`

如果 Basler 相机无法打开：

1. 运行 `python main.py cameras` 查看已连接设备
2. 在 Pylon Viewer 中确认相机可正常取图
3. 多台相机时，在 `config.py` 中设置正确的 `BASLER_SERIAL_NUMBER`

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

- 打印标定板时不要缩放，否则实际尺寸会失真
- 测距前必须完成标定并加载 `calibration.npz`
- 测量时标定板与待测点应保持同一平面
- 光照、清晰度和标定板占画面比例会显著影响检测效果

## 后续可扩展方向

- 增加标定结果可视化
- 增加测量结果保存功能
- 支持更多标定板参数配置
- 支持批量图片标定与离线测量
