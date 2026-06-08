"""运行时 ChArUco 标定板参数（标定、检测、生成共用）"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import config

PARAMS_FILE: Path = config.ROOT / "board_params.json"


@dataclass
class BoardParams:
    squares_x: int = config.SQUARES_X
    squares_y: int = config.SQUARES_Y
    square_length_m: float = config.SQUARE_LENGTH
    marker_length_m: float = config.MARKER_LENGTH
    aruco_dict: str = config.ARUCO_DICT

    @property
    def square_length_mm(self) -> float:
        return self.square_length_m * 1000.0

    @property
    def marker_length_mm(self) -> float:
        return self.marker_length_m * 1000.0

    def summary(self) -> str:
        return (
            f"{self.squares_x}×{self.squares_y}  "
            f"方格 {self.square_length_mm:.1f} mm  "
            f"标记 {self.marker_length_mm:.1f} mm  "
            f"{self.aruco_dict}"
        )


_active: BoardParams | None = None


def _defaults_from_config() -> BoardParams:
    return BoardParams(
        squares_x=config.SQUARES_X,
        squares_y=config.SQUARES_Y,
        square_length_m=config.SQUARE_LENGTH,
        marker_length_m=config.MARKER_LENGTH,
        aruco_dict=config.ARUCO_DICT,
    )


def load() -> BoardParams:
    if not PARAMS_FILE.exists():
        return _defaults_from_config()
    try:
        data = json.loads(PARAMS_FILE.read_text(encoding="utf-8"))
        return BoardParams(
            squares_x=int(data["squares_x"]),
            squares_y=int(data["squares_y"]),
            square_length_m=float(data["square_length_m"]),
            marker_length_m=float(data["marker_length_m"]),
            aruco_dict=str(data["aruco_dict"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return _defaults_from_config()


def get() -> BoardParams:
    global _active
    if _active is None:
        _active = load()
    return _active


def save(params: BoardParams) -> None:
    PARAMS_FILE.write_text(
        json.dumps(asdict(params), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def update(params: BoardParams, persist: bool = True) -> None:
    global _active
    _active = params
    if persist:
        save(params)


def from_mm_values(
    squares_x: int,
    squares_y: int,
    square_length_mm: float,
    marker_length_mm: float,
    aruco_dict: str,
) -> BoardParams:
    return BoardParams(
        squares_x=squares_x,
        squares_y=squares_y,
        square_length_m=square_length_mm / 1000.0,
        marker_length_m=marker_length_mm / 1000.0,
        aruco_dict=aruco_dict,
    )
