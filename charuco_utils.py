"""ChArUco 板创建、检测与标定工具"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

import config
import board_params as bp


@dataclass
class DetectionResult:
    corners: Optional[np.ndarray]
    ids: Optional[np.ndarray]
    marker_count: int = 0
    corner_count: int = 0
    board_size: Tuple[int, int] = (0, 0)
    hint: str = ""

    def __post_init__(self) -> None:
        if self.board_size == (0, 0):
            params = bp.get()
            self.board_size = (params.squares_x, params.squares_y)


def get_aruco_dict(dict_name: str | None = None) -> cv2.aruco.Dictionary:
    name = dict_name or bp.get().aruco_dict
    dict_id = getattr(cv2.aruco, name)
    return cv2.aruco.getPredefinedDictionary(dict_id)


def create_board(
    squares_x: int | None = None,
    squares_y: int | None = None,
) -> cv2.aruco.CharucoBoard:
    params = bp.get()
    sx = squares_x if squares_x is not None else params.squares_x
    sy = squares_y if squares_y is not None else params.squares_y
    return cv2.aruco.CharucoBoard(
        (sx, sy),
        params.square_length_m,
        params.marker_length_m,
        get_aruco_dict(params.aruco_dict),
    )


def create_detector_params() -> cv2.aruco.DetectorParameters:
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    params.detectInvertedMarker = True
    params.minMarkerPerimeterRate = 0.01
    params.maxMarkerPerimeterRate = 4.0
    params.adaptiveThreshWinSizeMin = 3
    params.adaptiveThreshWinSizeMax = 23
    params.adaptiveThreshConstant = 7
    params.minCornerDistanceRate = 0.01
    params.minDistanceToBorder = 1
    return params


def create_charuco_params() -> cv2.aruco.CharucoParameters:
    params = cv2.aruco.CharucoParameters()
    params.tryRefineMarkers = True
    params.minMarkers = 1
    return params


def create_detector(
    board: cv2.aruco.CharucoBoard | None = None,
) -> cv2.aruco.CharucoDetector:
    if board is None:
        board = create_board()
    return cv2.aruco.CharucoDetector(
        board,
        charucoParams=create_charuco_params(),
        detectorParams=create_detector_params(),
    )


def preprocess_for_detection(gray: np.ndarray) -> list[tuple[np.ndarray, float]]:
    """生成多种预处理图像，返回 (图像, 缩放系数)。"""
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    bases = [gray, clahe.apply(gray), clahe.apply(cv2.GaussianBlur(gray, (3, 3), 0))]

    variants: list[tuple[np.ndarray, float]] = []
    for base in bases:
        variants.append((base, 1.0))
        h, w = base.shape[:2]
        if max(h, w) < 1080:
            up = cv2.resize(base, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
            variants.append((up, 1.5))
        if max(h, w) < 720:
            up = cv2.resize(base, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
            variants.append((up, 2.0))

    seen: set[tuple[int, int, float]] = set()
    unique: list[tuple[np.ndarray, float]] = []
    for img, scale in variants:
        key = (img.shape[1], img.shape[0], scale)
        if key not in seen:
            seen.add(key)
            unique.append((img, scale))
    return unique


def open_camera(index: int = config.CAMERA_INDEX):
    """打开相机（Basler 工业相机或 OpenCV USB 摄像头，由 config.CAMERA_TYPE 决定）。"""
    from camera import open_camera as _open_camera

    return _open_camera(index)


def save_board_image(path=None, dpi: int = 300) -> None:
    """生成可打印的 ChArUco 标定板图像"""
    from board_generator import generate_board_from_active

    path = path or config.BOARD_IMAGE_FILE
    board_img, _ = generate_board_from_active(dpi=dpi)
    cv2.imwrite(str(path), board_img)
    print(f"标定板已保存: {path} ({board_img.shape[1]}x{board_img.shape[0]} px)")


def _scale_corners_back(
    corners: Optional[np.ndarray],
    scale: float,
) -> Optional[np.ndarray]:
    if corners is None or scale == 1.0:
        return corners
    scaled = corners.copy().astype(np.float32)
    scaled /= scale
    return scaled


def _detect_once(
    gray: np.ndarray,
    detector: cv2.aruco.CharucoDetector,
    scale: float = 1.0,
) -> tuple[Optional[np.ndarray], Optional[np.ndarray], int]:
    corners, ids, _, marker_ids = detector.detectBoard(gray)
    marker_count = 0 if marker_ids is None else len(marker_ids)
    corner_count = 0 if ids is None else len(ids)
    if ids is None or corner_count < 4:
        return None, None, marker_count
    return _scale_corners_back(corners, scale), ids, marker_count


def detect_charuco(
    gray: np.ndarray,
    detector: cv2.aruco.CharucoDetector,
) -> tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    result = detect_charuco_robust(gray, detector)
    return result.corners, result.ids


def detect_charuco_robust(
    gray: np.ndarray,
    detector: cv2.aruco.CharucoDetector | None = None,
) -> DetectionResult:
    """多策略检测 ChArUco 板，并返回调试信息。"""
    params = bp.get()
    best = DetectionResult(None, None, 0, 0, (params.squares_x, params.squares_y), "")
    board_sizes = [
        (params.squares_x, params.squares_y),
        (params.squares_y, params.squares_x),
    ]

    for squares_x, squares_y in board_sizes:
        board = create_board(squares_x, squares_y)
        current_detector = detector if (
            detector is not None
            and squares_x == params.squares_x
            and squares_y == params.squares_y
        ) else create_detector(board)

        max_markers = 0
        best_corners = None
        best_ids = None
        best_corners_count = 0

        for variant, scale in preprocess_for_detection(gray):
            corners, ids, marker_count = _detect_once(variant, current_detector, scale)
            max_markers = max(max_markers, marker_count)
            corner_count = 0 if ids is None else len(ids)
            if corner_count > best_corners_count:
                best_corners = corners
                best_ids = ids
                best_corners_count = corner_count

        if best_corners_count > best.corner_count:
            best = DetectionResult(
                best_corners,
                best_ids,
                max_markers,
                best_corners_count,
                (squares_x, squares_y),
                "",
            )

    best.hint = _build_detection_hint(best)
    return best


def _build_detection_hint(result: DetectionResult) -> str:
    params = bp.get()
    if result.corner_count >= 4:
        if result.board_size != (params.squares_x, params.squares_y):
            return "已识别（检测到旋转方向不同的标定板，请按程序生成的方向打印）"
        return "标定板识别正常"

    if result.marker_count > 0:
        return "已识别部分 ArUco 标记，但未形成足够角点。请调整距离、对焦和光照"

    return (
        "未识别到 ArUco 标记。请确认：\n"
        "1) 使用本程序生成的 charuco_board.png 打印\n"
        "2) 打印时不要缩放，贴平硬板\n"
        "3) 标定板占画面 1/3 以上，光线充足、对焦清晰"
    )


def match_board_points(
    charuco_corners: np.ndarray,
    charuco_ids: np.ndarray,
    board: cv2.aruco.CharucoBoard | None = None,
    board_size: Optional[Tuple[int, int]] = None,
) -> tuple[np.ndarray, np.ndarray] | None:
    """将检测到的角点映射为板坐标系下的三维点与图像二维点"""
    if board is None:
        if board_size is not None:
            board = create_board(board_size[0], board_size[1])
        else:
            board = create_board()
    obj_pts, img_pts = board.matchImagePoints(charuco_corners, charuco_ids)
    if obj_pts is None or len(obj_pts) < 4:
        return None
    return obj_pts, img_pts


def calibrate_from_samples(
    all_obj_points: list[np.ndarray],
    all_img_points: list[np.ndarray],
    image_size: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray, float]:
    """根据多帧 ChArUco 角点进行相机标定（OpenCV 4.7+ 推荐方式）"""
    if len(all_obj_points) < 1:
        raise ValueError("没有有效的标定样本")

    flags = cv2.CALIB_RATIONAL_MODEL
    ret, camera_matrix, dist_coeffs, _, _ = cv2.calibrateCamera(
        all_obj_points,
        all_img_points,
        image_size,
        None,
        None,
        flags=flags,
    )
    return camera_matrix, dist_coeffs, ret


def save_calibration(
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    path=None,
) -> None:
    path = path or config.CALIBRATION_FILE
    np.savez(str(path), camera_matrix=camera_matrix, dist_coeffs=dist_coeffs)
    print(f"标定数据已保存: {path}")


def load_calibration(path=None) -> tuple[np.ndarray, np.ndarray] | None:
    path = path or config.CALIBRATION_FILE
    if not path.exists():
        return None
    data = np.load(str(path))
    return data["camera_matrix"], data["dist_coeffs"]


def estimate_board_pose(
    charuco_corners: np.ndarray,
    charuco_ids: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    board_size: Optional[Tuple[int, int]] = None,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """估计标定板位姿，用于将图像点映射到板平面（米）"""
    matched = match_board_points(charuco_corners, charuco_ids, board_size=board_size)
    if matched is None:
        return None, None

    obj_pts, img_pts = matched
    success, rvec, tvec = cv2.solvePnP(
        obj_pts,
        img_pts,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_IPPE,
    )
    if not success:
        return None, None
    return rvec, tvec


def build_image_to_board_homography(
    charuco_corners: np.ndarray,
    charuco_ids: np.ndarray,
    board_size: Optional[Tuple[int, int]] = None,
) -> np.ndarray | None:
    """
    根据检测到的 ChArUco 角点，构建图像像素坐标到标定板平面坐标的单应矩阵。

    该映射适用于相机、被测平面和场景保持不动的情况。锁定一次参考后，
    后续可以在没有标定板出现在画面中的情况下继续进行平面测量。
    """
    matched = match_board_points(charuco_corners, charuco_ids, board_size=board_size)
    if matched is None:
        return None

    obj_pts, img_pts = matched
    if len(obj_pts) < 4 or len(img_pts) < 4:
        return None

    img_xy = np.asarray(img_pts, dtype=np.float32).reshape(-1, 2)
    obj_xy = np.asarray(obj_pts, dtype=np.float32).reshape(-1, 3)[:, :2]
    homography, _ = cv2.findHomography(img_xy, obj_xy, method=0)
    return homography


def map_image_point_to_board(
    point: tuple[float, float],
    homography: np.ndarray,
) -> np.ndarray | None:
    """使用已锁定的单应矩阵，将图像点映射到标定板平面坐标。"""
    if homography is None:
        return None

    src = np.array([[[float(point[0]), float(point[1])]]], dtype=np.float32)
    mapped = cv2.perspectiveTransform(src, homography)
    if mapped is None:
        return None

    result = mapped[0, 0].astype(np.float64)
    if not np.isfinite(result).all():
        return None
    return result


def image_point_to_board_plane(
    point: tuple[float, float],
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    rvec: np.ndarray,
    tvec: np.ndarray,
) -> np.ndarray | None:
    """
    将图像像素点反投影到 ChArUco 板平面 (Z=0)，返回板坐标系下的 (x, y) 米。
    """
    src = np.array([[point]], dtype=np.float32)
    undistorted = cv2.undistortPoints(src, camera_matrix, dist_coeffs, P=camera_matrix)

    fx = camera_matrix[0, 0]
    fy = camera_matrix[1, 1]
    cx = camera_matrix[0, 2]
    cy = camera_matrix[1, 2]
    u, v = undistorted[0, 0]
    ray_cam = np.array([(u - cx) / fx, (v - cy) / fy, 1.0], dtype=np.float64)

    R, _ = cv2.Rodrigues(rvec)
    # 板坐标 -> 相机坐标: P_cam = R @ P_board + t
    # 板平面 Z_board = 0，求射线与平面交点
    ray_dir_board = R.T @ ray_cam
    origin_board = -R.T @ tvec.flatten()

    if abs(ray_dir_board[2]) < 1e-9:
        return None

    scale = -origin_board[2] / ray_dir_board[2]
    if scale < 0:
        return None

    intersection = origin_board + scale * ray_dir_board
    return intersection[:2]


def distance_on_board_plane(p1: np.ndarray, p2: np.ndarray) -> float:
    return float(np.linalg.norm(p1 - p2))
