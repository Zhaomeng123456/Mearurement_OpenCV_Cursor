"""独立入口：ChArUco 标定板生成器"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from board_gui import open_board_generator

if __name__ == "__main__":
    open_board_generator()
