"""ChArUco 标定板生成与导出（纯函数，无 GUI 依赖）"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import config
import board_params as bp

ARUCO_DICTS = {
    "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
    "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
    "DICT_4X4_250": cv2.aruco.DICT_4X4_250,
    "DICT_4X4_1000": cv2.aruco.DICT_4X4_1000,
    "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
    "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
    "DICT_5X5_250": cv2.aruco.DICT_5X5_250,
    "DICT_5X5_1000": cv2.aruco.DICT_5X5_1000,
    "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
    "DICT_6X6_100": cv2.aruco.DICT_6X6_100,
    "DICT_6X6_250": cv2.aruco.DICT_6X6_250,
    "DICT_6X6_1000": cv2.aruco.DICT_6X6_1000,
    "DICT_7X7_50": cv2.aruco.DICT_7X7_50,
    "DICT_7X7_100": cv2.aruco.DICT_7X7_100,
    "DICT_7X7_250": cv2.aruco.DICT_7X7_250,
    "DICT_7X7_1000": cv2.aruco.DICT_7X7_1000,
    "DICT_ARUCO_ORIGINAL": cv2.aruco.DICT_ARUCO_ORIGINAL,
}

PAGE_SIZES_MM = {
    "A4": (210, 297),
    "Letter": (215.9, 279.4),
    "A3": (297, 420),
    "A2": (420, 594),
}


@dataclass(frozen=True)
class BoardDefaults:
    squares_x: int
    squares_y: int
    square_length_mm: float
    marker_length_mm: float
    dict_name: str


def _meters_to_mm(length_m: float) -> float:
    return length_m * 1000.0


def defaults_from_active() -> BoardDefaults:
    """从当前运行时标定参数读取默认值（长度转为 mm）。"""
    params = bp.get()
    return BoardDefaults(
        squares_x=params.squares_x,
        squares_y=params.squares_y,
        square_length_mm=params.square_length_mm,
        marker_length_mm=params.marker_length_mm,
        dict_name=params.aruco_dict,
    )


def defaults_from_config() -> BoardDefaults:
    """兼容旧接口，实际返回当前运行时参数。"""
    return defaults_from_active()


def generate_board_from_active(dpi: int = 300) -> tuple[np.ndarray, cv2.aruco.CharucoBoard]:
    """按当前运行时参数生成标定板。"""
    defaults = defaults_from_active()
    dict_id = ARUCO_DICTS[defaults.dict_name]
    return generate_charuco_board(
        defaults.squares_x,
        defaults.squares_y,
        defaults.square_length_mm,
        defaults.marker_length_mm,
        dict_id,
        dpi=dpi,
    )


def generate_board_from_config(dpi: int = 300) -> tuple[np.ndarray, cv2.aruco.CharucoBoard]:
    """兼容旧接口。"""
    return generate_board_from_active(dpi=dpi)


def generate_charuco_board(
    board_w: int,
    board_h: int,
    sq_len_mm: float,
    mk_len_mm: float,
    dict_id: int,
    dpi: int = 300,
) -> tuple[np.ndarray, cv2.aruco.CharucoBoard]:
    """生成 ChArUco 标定板图像（BGR numpy 数组）。尺寸单位为 mm。"""
    aruco_dict = cv2.aruco.getPredefinedDictionary(dict_id)
    board = cv2.aruco.CharucoBoard(
        (board_w, board_h), sq_len_mm, mk_len_mm, aruco_dict
    )
    board_px = int(board_w * sq_len_mm * dpi / 25.4)
    board_py = int(board_h * sq_len_mm * dpi / 25.4)
    board_img = board.generateImage((board_px, board_py), marginSize=0)
    return board_img, board


def get_board_physical_size_mm(board_w: int, board_h: int, sq_len_mm: float) -> tuple[float, float]:
    """返回标定板物理尺寸 (宽 mm, 高 mm)。"""
    return board_w * sq_len_mm, board_h * sq_len_mm


def bgr_to_pil(board_img: np.ndarray) -> Image.Image:
    """BGR OpenCV 图像转 PIL RGB。"""
    if board_img.ndim == 2:
        rgb = cv2.cvtColor(board_img, cv2.COLOR_GRAY2RGB)
    else:
        rgb = cv2.cvtColor(board_img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def mm_to_px(mm_val: float, dpi: int) -> int:
    """毫米转像素。"""
    return int(mm_val / 25.4 * dpi)


def format_board_info(
    dict_name: str,
    board_w: int,
    board_h: int,
    sq_len_mm: float,
    mk_len_mm: float,
    bw_mm: float,
    bh_mm: float,
    dpi: Optional[int] = None,
) -> list[str]:
    """构建标定板说明文字行。"""
    lines = [
        "ChArUco Calibration Board",
        f"Dictionary: {dict_name}    Grid: {board_w} x {board_h} squares",
        f"Square: {sq_len_mm:.1f} mm    Marker: {mk_len_mm:.1f} mm    "
        f"Physical size: {bw_mm:.1f} x {bh_mm:.1f} mm",
    ]
    if dpi is not None:
        lines.append(f"Export DPI: {dpi}")
    return lines


def _get_font(size_px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size_px)
            except OSError:
                continue
    return ImageFont.load_default()


def compose_board_with_caption(
    board_img: np.ndarray,
    info_lines: list[str],
    dpi: int = 300,
) -> Image.Image:
    """返回带说明文字的组合 PIL 图像。"""
    pil_board = bgr_to_pil(board_img)
    board_w, board_h = pil_board.size

    font_size = max(12, mm_to_px(3.5, dpi))
    font = _get_font(font_size)
    line_gap = mm_to_px(1.5, dpi)
    margin_px = mm_to_px(4, dpi)
    line_height = font_size + line_gap

    caption_h = margin_px * 2 + line_height * len(info_lines)
    canvas = Image.new("RGB", (board_w, board_h + caption_h), "white")
    canvas.paste(pil_board, (0, 0))

    draw = ImageDraw.Draw(canvas)
    y = board_h + margin_px
    for line in info_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = max(0, (board_w - text_w) // 2)
        draw.text((x, y), line, fill="black", font=font)
        y += line_height

    return canvas


def save_image_as_pdf(
    pil_img: Image.Image,
    file_path: str,
    page_size_mm: tuple[float, float],
    dpi: int = 300,
    margin_mm: float = 10,
) -> None:
    """将 PIL 图像居中保存为 PDF。"""
    page_w_mm, page_h_mm = page_size_mm
    img_w_px, img_h_px = pil_img.size

    page_w_px = mm_to_px(page_w_mm, dpi)
    page_h_px = mm_to_px(page_h_mm, dpi)
    margin_px = mm_to_px(margin_mm, dpi)

    max_w = page_w_px - 2 * margin_px
    max_h = page_h_px - 2 * margin_px
    scale = min(max_w / img_w_px, max_h / img_h_px, 1.0)

    draw_w = int(img_w_px * scale)
    draw_h = int(img_h_px * scale)
    if (draw_w, draw_h) != pil_img.size:
        pil_img = pil_img.resize((draw_w, draw_h), Image.LANCZOS)

    page = Image.new("RGB", (page_w_px, page_h_px), "white")
    x = (page_w_px - draw_w) // 2
    y = (page_h_px - draw_h) // 2
    page.paste(pil_img, (x, y))
    page.save(file_path, "PDF", resolution=dpi)
