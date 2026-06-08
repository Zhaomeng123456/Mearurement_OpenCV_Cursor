"""使用 ChArUco 板进行相机标定"""

from __future__ import annotations

import cv2

import config
import charuco_utils as cu


def run_calibration(camera_index: int = config.CAMERA_INDEX) -> bool:
    cap = cu.open_camera(camera_index)
    if not cap.isOpened():
        print("无法打开相机，请检查 Basler 连接或 config.py 中的相机配置")
        return False

    detector = cu.create_detector()
    all_obj_points: list = []
    all_img_points: list = []
    image_size = None

    print("=" * 50)
    print("ChArUco 相机标定")
    print("  将打印好的标定板放在摄像头前，缓慢移动/倾斜")
    print("  按 [空格] 采集一帧，按 [c] 完成标定，按 [q] 退出")
    print(f"  建议采集至少 {config.CALIBRATION_MIN_FRAMES} 帧")
    print("=" * 50)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        image_size = (gray.shape[1], gray.shape[0])
        corners, ids = cu.detect_charuco(gray, detector)

        display = frame.copy()
        if corners is not None:
            cv2.aruco.drawDetectedCornersCharuco(display, corners, ids, (0, 255, 0))

        cv2.putText(
            display,
            f"已采集: {len(all_obj_points)} / {config.CALIBRATION_MIN_FRAMES}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )
        cv2.imshow("Calibration", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        if key == ord(" ") and corners is not None:
            matched = cu.match_board_points(corners, ids)
            if matched is None:
                print("角点匹配失败，请调整标定板位置后重试")
                continue
            obj_pts, img_pts = matched
            all_obj_points.append(obj_pts)
            all_img_points.append(img_pts)
            print(f"采集第 {len(all_obj_points)} 帧")
        if key == ord("c"):
            if len(all_obj_points) < config.CALIBRATION_MIN_FRAMES:
                print(f"帧数不足，当前 {len(all_obj_points)}，需要至少 {config.CALIBRATION_MIN_FRAMES}")
                continue
            try:
                camera_matrix, dist_coeffs, reproj_error = cu.calibrate_from_samples(
                    all_obj_points, all_img_points, image_size
                )
                cu.save_calibration(camera_matrix, dist_coeffs)
                print(f"标定完成，重投影误差: {reproj_error:.4f} px")
                cap.release()
                cv2.destroyAllWindows()
                return True
            except ValueError as e:
                print(e)

    cap.release()
    cv2.destroyAllWindows()
    return False


if __name__ == "__main__":
    run_calibration()
