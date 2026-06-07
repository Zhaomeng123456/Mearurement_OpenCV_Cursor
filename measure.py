"""摄像头实时测距：ChArUco 矫正后测量两点距离"""

from __future__ import annotations

import cv2
import numpy as np

import config
import charuco_utils as cu


class DistanceMeasurer:
    def __init__(self) -> None:
        self.calib = cu.load_calibration()
        self.detector = cu.create_detector()
        self.points: list[tuple[int, int]] = []
        self.last_distance_mm: float | None = None
        self.reference_homography: np.ndarray | None = None
        self.window = "Measurement"

    def _on_mouse(self, event: int, x: int, y: int, _flags: int, _param) -> None:
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if len(self.points) >= 2:
            self.points.clear()
            self.last_distance_mm = None
        self.points.append((x, y))
        self._recompute_distance()

    def _draw_overlay(self, frame: np.ndarray, detection: cu.DetectionResult) -> np.ndarray:
        display = frame.copy()

        for i, pt in enumerate(self.points):
            cv2.circle(display, pt, 6, (0, 0, 255), -1)
            cv2.putText(
                display,
                f"P{i + 1}",
                (pt[0] + 8, pt[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
            )

        if len(self.points) == 2 and self.last_distance_mm is not None:
            p1, p2 = self.points
            cv2.line(display, p1, p2, (255, 0, 0), 2)
            mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
            cv2.putText(
                display,
                f"{self.last_distance_mm:.2f} mm",
                (mid[0] - 40, mid[1] - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 0, 0),
                2,
            )

        if self.reference_homography is not None:
            status = "Reference LOCKED"
            color = (0, 255, 0)
        elif detection.corner_count >= 4:
            status = "Board READY | press [l] to lock"
            color = (0, 255, 255)
        else:
            status = "Need board lock"
            color = (0, 0, 255)
        cv2.putText(display, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(
            display,
            f"markers {detection.marker_count} corners {detection.corner_count}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (220, 220, 220),
            2,
        )

        help_text = "Lock board [l] | unlock [u] | click 2 points | [r] reset | [q] quit"
        cv2.putText(
            display,
            help_text,
            (10, frame.shape[0] - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (200, 200, 200),
            1,
        )
        return display

    def _recompute_distance(self) -> None:
        if len(self.points) != 2 or self.reference_homography is None:
            self.last_distance_mm = None
            return

        board_pts = []
        for pt in self.points:
            mapped = cu.map_image_point_to_board(pt, self.reference_homography)
            if mapped is None:
                self.last_distance_mm = None
                return
            board_pts.append(mapped)

        dist_m = cu.distance_on_board_plane(board_pts[0], board_pts[1])
        self.last_distance_mm = dist_m * 1000.0

    def _lock_reference(self, detection: cu.DetectionResult) -> bool:
        if detection.corners is None or detection.ids is None:
            return False

        homography = cu.build_image_to_board_homography(
            detection.corners, detection.ids, board_size=detection.board_size
        )
        if homography is None:
            return False

        self.reference_homography = homography
        self._recompute_distance()
        return True

    def _clear_reference(self) -> None:
        self.reference_homography = None
        self.points.clear()
        self.last_distance_mm = None

    def run(self, camera_index: int = config.CAMERA_INDEX) -> None:
        if self.calib is None:
            print("未找到标定文件，请先运行: python calibrate.py")
            return

        camera_matrix, dist_coeffs = self.calib
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("无法打开摄像头")
            return

        cv2.namedWindow(self.window)
        cv2.setMouseCallback(self.window, self._on_mouse)

        print("测距程序已启动")
        print("  先将标定板放在待测物同一平面，并按 [l] 锁定参考")
        print("  锁定后可以移走标定板，但相机与被测平面必须保持不动")
        print("  鼠标左键点击两个点测量距离")
        print("  [l] 锁定参考  [u] 清除参考  [r] 清除点位  [q] 退出")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 畸变矫正
            undistorted = cv2.undistort(frame, camera_matrix, dist_coeffs)
            gray = cv2.cvtColor(undistorted, cv2.COLOR_BGR2GRAY)
            detection = cu.detect_charuco_robust(gray, self.detector)
            corners, ids = detection.corners, detection.ids
            board_detected = corners is not None

            if board_detected:
                cv2.aruco.drawDetectedCornersCharuco(undistorted, corners, ids, (0, 255, 0))

            display = self._draw_overlay(undistorted, detection)
            cv2.imshow(self.window, display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("r"):
                self.points.clear()
                self.last_distance_mm = None
            if key == ord("l"):
                if self._lock_reference(detection):
                    print("参考平面已锁定，可移走标定板继续测距")
                else:
                    print("当前未检测到足够角点，无法锁定参考")
            if key == ord("u"):
                self._clear_reference()
                print("参考平面已清除，请重新放置标定板并锁定")

        cap.release()
        cv2.destroyAllWindows()


def main() -> None:
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "board":
        cu.save_board_image()
        return

    DistanceMeasurer().run()


if __name__ == "__main__":
    main()
