"""ChArUco 测距系统 - 图形界面"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageTk

import config
import charuco_utils as cu
import board_params as bp
import board_generator as bg
from board_gui import open_board_generator


class MeasurementGUI(tk.Tk):
    DISPLAY_WIDTH = 960
    DISPLAY_HEIGHT = 540

    def __init__(self) -> None:
        super().__init__()
        self.title("ChArUco 测距系统")
        self.geometry("1200x720")
        self.minsize(1000, 640)

        self.cap = None
        self.detector = cu.create_detector()
        self._last_detection = cu.DetectionResult(None, None)
        self.mode = tk.StringVar(value="measure")
        self._photo: Optional[ImageTk.PhotoImage] = None
        self._frame_size: Tuple[int, int] = (640, 480)
        self._scale = (1.0, 1.0)

        # 标定状态
        self._calib_obj_points: list = []
        self._calib_img_points: list = []
        self._reproj_error: Optional[float] = None

        # 测距状态
        self._measure_points: list = []
        self._distance_mm: Optional[float] = None
        self._camera_matrix: Optional[np.ndarray] = None
        self._dist_coeffs: Optional[np.ndarray] = None
        self._measure_homography: Optional[np.ndarray] = None

        self._build_ui()
        self._ensure_board_image()
        self._load_calibration()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._start_camera()

    def _build_ui(self) -> None:
        main = ttk.Frame(self, padding=8)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main, width=260)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left.pack_propagate(False)

        ttk.Label(left, text="ChArUco 测距", font=("Microsoft YaHei UI", 16, "bold")).pack(
            anchor=tk.W, pady=(0, 12)
        )

        ttk.Label(left, text="功能选择", font=("Microsoft YaHei UI", 10, "bold")).pack(anchor=tk.W)
        ttk.Radiobutton(
            left, text="距离测量", variable=self.mode, value="measure", command=self._on_mode_change
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(
            left, text="相机标定", variable=self.mode, value="calibrate", command=self._on_mode_change
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(
            left, text="标定板工具", variable=self.mode, value="board", command=self._on_mode_change
        ).pack(anchor=tk.W, pady=2)

        ttk.Separator(left).pack(fill=tk.X, pady=12)

        self.status_var = tk.StringVar(value="正在启动相机...")
        ttk.Label(left, text="状态", font=("Microsoft YaHei UI", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(left, textvariable=self.status_var, wraplength=230, justify=tk.LEFT).pack(
            anchor=tk.W, pady=4
        )

        self.info_var = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.info_var, wraplength=230, justify=tk.LEFT).pack(
            anchor=tk.W, pady=4
        )

        self.board_params_frame = ttk.LabelFrame(left, text="标定板参数", padding=6)
        self._build_board_params_controls(self.board_params_frame)

        ttk.Separator(left).pack(fill=tk.X, pady=12)
        self.action_frame = ttk.Frame(left)
        self.action_frame.pack(fill=tk.X)

        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            right,
            width=self.DISPLAY_WIDTH,
            height=self.DISPLAY_HEIGHT,
            bg="#1e1e1e",
            highlightthickness=1,
            highlightbackground="#444",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        self.distance_var = tk.StringVar(value="距离: -- mm")
        ttk.Label(
            right, textvariable=self.distance_var, font=("Microsoft YaHei UI", 18, "bold")
        ).pack(pady=(8, 0))

        self._rebuild_actions()
        self._toggle_board_params_panel()

    def _build_board_params_controls(self, parent: ttk.LabelFrame) -> None:
        params = bp.get()
        row = 0

        ttk.Label(parent, text="字典:").grid(row=row, column=0, sticky="w", pady=2)
        self.bp_dict_var = tk.StringVar(value=params.aruco_dict)
        ttk.Combobox(
            parent,
            textvariable=self.bp_dict_var,
            values=list(bg.ARUCO_DICTS.keys()),
            state="readonly",
            width=18,
        ).grid(row=row, column=1, sticky="ew", pady=2)
        row += 1

        ttk.Label(parent, text="方格 X:").grid(row=row, column=0, sticky="w", pady=2)
        self.bp_x_var = tk.IntVar(value=params.squares_x)
        ttk.Spinbox(parent, from_=2, to=20, textvariable=self.bp_x_var, width=8).grid(
            row=row, column=1, sticky="w", pady=2
        )
        row += 1

        ttk.Label(parent, text="方格 Y:").grid(row=row, column=0, sticky="w", pady=2)
        self.bp_y_var = tk.IntVar(value=params.squares_y)
        ttk.Spinbox(parent, from_=2, to=20, textvariable=self.bp_y_var, width=8).grid(
            row=row, column=1, sticky="w", pady=2
        )
        row += 1

        ttk.Label(parent, text="方格 (mm):").grid(row=row, column=0, sticky="w", pady=2)
        self.bp_sq_var = tk.DoubleVar(value=params.square_length_mm)
        ttk.Spinbox(
            parent, from_=5.0, to=200.0, increment=1.0, textvariable=self.bp_sq_var, width=8
        ).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        ttk.Label(parent, text="标记 (mm):").grid(row=row, column=0, sticky="w", pady=2)
        self.bp_mk_var = tk.DoubleVar(value=params.marker_length_mm)
        ttk.Spinbox(
            parent, from_=2.0, to=190.0, increment=1.0, textvariable=self.bp_mk_var, width=8
        ).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        ttk.Button(parent, text="应用参数", command=self._apply_board_params_from_ui).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(6, 0)
        )
        parent.columnconfigure(1, weight=1)

    def _load_board_params_ui(self) -> None:
        params = bp.get()
        self.bp_dict_var.set(params.aruco_dict)
        self.bp_x_var.set(params.squares_x)
        self.bp_y_var.set(params.squares_y)
        self.bp_sq_var.set(params.square_length_mm)
        self.bp_mk_var.set(params.marker_length_mm)

    def _apply_board_params_from_ui(self) -> None:
        sq_len = float(self.bp_sq_var.get())
        mk_len = float(self.bp_mk_var.get())
        if mk_len >= sq_len:
            messagebox.showwarning("无效尺寸", "标记边长必须小于方格边长。")
            return

        bp.update(
            bp.from_mm_values(
                self.bp_x_var.get(),
                self.bp_y_var.get(),
                sq_len,
                mk_len,
                self.bp_dict_var.get(),
            )
        )
        self._on_board_params_changed(show_message=True)

    def _refresh_board_detector(self) -> None:
        self.detector = cu.create_detector()
        self._last_detection = cu.DetectionResult(None, None)
        self._measure_homography = None
        self._reset_measure()

    def _on_board_params_changed(self, show_message: bool = False) -> None:
        self._load_board_params_ui()
        if self._calib_obj_points:
            self._clear_calib_frames()
            self.status_var.set("标定板参数已更新，已清空标定帧，请重新采集")
        else:
            self.status_var.set("标定板参数已更新")
        self._refresh_board_detector()
        self._update_info()
        if show_message:
            messagebox.showinfo("完成", "标定板参数已应用到标定/测距模块。")

    def _toggle_board_params_panel(self) -> None:
        if self.mode.get() in ("calibrate", "board"):
            self.board_params_frame.pack(fill=tk.X, pady=(0, 8))
            self._load_board_params_ui()
        else:
            self.board_params_frame.pack_forget()

    def _rebuild_actions(self) -> None:
        for child in self.action_frame.winfo_children():
            child.destroy()

        mode = self.mode.get()
        if mode == "measure":
            ttk.Button(self.action_frame, text="清除测量点", command=self._reset_measure).pack(
                fill=tk.X, pady=3
            )
            ttk.Button(self.action_frame, text="锁定当前参考", command=self._lock_measure_reference).pack(
                fill=tk.X, pady=3
            )
            ttk.Button(self.action_frame, text="清除参考", command=self._clear_measure_reference).pack(
                fill=tk.X, pady=3
            )
            ttk.Button(self.action_frame, text="重新加载标定", command=self._load_calibration).pack(
                fill=tk.X, pady=3
            )
            ttk.Label(
                self.action_frame,
                text=(
                    "先将标定板放入画面并锁定参考平面。\n"
                    "锁定后可以移走标定板继续测距，\n"
                    "但相机与被测平面必须保持不动。"
                ),
                wraplength=230,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=6)
        elif mode == "calibrate":
            ttk.Button(self.action_frame, text="采集当前帧", command=self._capture_calib_frame).pack(
                fill=tk.X, pady=3
            )
            ttk.Button(self.action_frame, text="完成标定", command=self._finish_calibration).pack(
                fill=tk.X, pady=3
            )
            ttk.Button(self.action_frame, text="清空已采集", command=self._clear_calib_frames).pack(
                fill=tk.X, pady=3
            )
            ttk.Label(
                self.action_frame,
                text=f"建议采集至少 {config.CALIBRATION_MIN_FRAMES} 帧，\n多角度移动标定板。",
                wraplength=230,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=6)
        else:
            ttk.Button(
                self.action_frame, text="打开标定板生成器", command=self._open_board_generator
            ).pack(fill=tk.X, pady=3)
            ttk.Button(self.action_frame, text="打开标定板目录", command=self._open_board_folder).pack(
                fill=tk.X, pady=3
            )
            ttk.Label(
                self.action_frame,
                text=(
                    "在生成器中调节参数、预览标定板，\n"
                    "保存 PDF/PNG 时会自动同步到左侧标定参数。"
                ),
                wraplength=230,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=6)

    def _on_mode_change(self) -> None:
        self._toggle_board_params_panel()
        self._rebuild_actions()
        if self.mode.get() == "measure":
            self._load_calibration()
        self._update_info()

    def _load_calibration(self) -> None:
        calib = cu.load_calibration()
        self._measure_homography = None
        self._reset_measure()
        if calib is None:
            self._camera_matrix = None
            self._dist_coeffs = None
            self.status_var.set("未标定：请先在「相机标定」中完成标定")
        else:
            self._camera_matrix, self._dist_coeffs = calib
            self.status_var.set("标定数据已加载，请先锁定参考平面")
        self._update_info()

    def _update_info(self) -> None:
        mode = self.mode.get()
        if mode == "calibrate":
            det = self._last_detection
            self.info_var.set(
                f"已采集: {len(self._calib_obj_points)} / {config.CALIBRATION_MIN_FRAMES} 帧\n"
                f"{bp.get().summary()}\n"
                f"标记 {det.marker_count} | 角点 {det.corner_count}"
            )
            if det.hint and det.corner_count < 4:
                self.status_var.set(det.hint.split("\n")[0])
        elif mode == "measure":
            det = self._last_detection
            det_line = f"标记 {det.marker_count} | 角点 {det.corner_count}"
            params_line = bp.get().summary()
            if self._camera_matrix is None:
                self.info_var.set(f"缺少标定文件\n{params_line}\n{det_line}")
                self.status_var.set("未标定：请先在「相机标定」中完成标定")
            else:
                pts = len(self._measure_points)
                ref_line = "参考平面: 已锁定" if self._measure_homography is not None else "参考平面: 未锁定"
                self.info_var.set(f"{ref_line}\n{params_line}\n已选点数: {pts} / 2\n{det_line}")
                if self._measure_homography is not None:
                    self.status_var.set("参考平面已锁定，可移走标定板继续测距")
                elif det.corner_count >= 4:
                    self.status_var.set("检测到标定板，请点击「锁定当前参考」")
                else:
                    self.status_var.set("请先将标定板放入画面，并锁定参考平面")
        else:
            exists = "已生成" if config.BOARD_IMAGE_FILE.exists() else "未生成"
            self.info_var.set(f"标定板图片: {exists}\n{bp.get().summary()}")

    def _ensure_board_image(self) -> None:
        if not config.BOARD_IMAGE_FILE.exists():
            try:
                cu.save_board_image()
                self.status_var.set("已自动生成标定板图片，请打印后使用")
            except Exception as exc:
                self.status_var.set(f"标定板生成失败: {exc}")

    def _start_camera(self) -> None:
        self.cap = cu.open_camera(config.CAMERA_INDEX)
        if not self.cap.isOpened():
            self.status_var.set("无法打开相机，请检查连接")
            hint = (
                "无法打开 Basler 相机，请确认：\n"
                "1) 已安装 Basler Pylon 驱动与 pypylon\n"
                "2) 相机已连接并被 Pylon Viewer 识别\n"
                "3) config.py 中 BASLER_SERIAL_NUMBER 配置正确\n"
                "4) 关闭 Pylon Viewer 或其他占用相机的程序后重试"
                if config.CAMERA_TYPE.lower() == "basler"
                else "无法打开摄像头，请检查设备或修改 config.py 中的 CAMERA_INDEX"
            )
            messagebox.showerror("错误", hint)
            return
        self._update_frame()

    def _update_frame(self) -> None:
        if self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.after(30, self._update_frame)
            return

        self._frame_size = (frame.shape[1], frame.shape[0])
        display = self._process_frame(frame)
        self._show_frame(display)
        self._update_info()
        self.after(30, self._update_frame)

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        mode = self.mode.get()

        # 已标定时在矫正后的画面上检测，保证角点与点击坐标一致
        if mode == "measure" and self._camera_matrix is not None:
            display = cv2.undistort(frame, self._camera_matrix, self._dist_coeffs)
            detect_gray = cv2.cvtColor(display, cv2.COLOR_BGR2GRAY)
        else:
            display = frame.copy()
            detect_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        detection = cu.detect_charuco_robust(detect_gray, self.detector)
        self._last_detection = detection
        corners, ids = detection.corners, detection.ids
        board_ok = corners is not None

        if mode == "measure":
            if board_ok:
                cv2.aruco.drawDetectedCornersCharuco(display, corners, ids, (0, 255, 0))
            display = self._draw_measure_overlay(display, detection)
        elif mode == "calibrate":
            if board_ok:
                cv2.aruco.drawDetectedCornersCharuco(display, corners, ids, (0, 255, 0))
            cv2.putText(
                display,
                f"Frames: {len(self._calib_obj_points)}/{config.CALIBRATION_MIN_FRAMES}",
                (12, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 255),
                2,
            )
            self._draw_detection_debug(display, detection, y=64)
        else:
            if board_ok:
                cv2.aruco.drawDetectedCornersCharuco(display, corners, ids, (0, 255, 0))
            self._draw_detection_debug(display, detection, y=32)

        return display

    def _draw_measure_overlay(self, frame: np.ndarray, detection: cu.DetectionResult) -> np.ndarray:
        display = frame.copy()
        for i, pt in enumerate(self._measure_points):
            cv2.circle(display, pt, 7, (0, 0, 255), -1)
            cv2.putText(
                display,
                f"P{i + 1}",
                (pt[0] + 10, pt[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )

        if len(self._measure_points) == 2 and self._distance_mm is not None:
            p1, p2 = self._measure_points
            cv2.line(display, p1, p2, (255, 128, 0), 2)
            mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
            cv2.putText(
                display,
                f"{self._distance_mm:.2f} mm",
                (mid[0] - 50, mid[1] - 14),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (255, 128, 0),
                2,
            )
            self.distance_var.set(f"距离: {self._distance_mm:.2f} mm")
        else:
            self.distance_var.set("距离: -- mm")

        if self._measure_homography is not None:
            status = "Reference LOCKED | board can be removed"
            color = (0, 255, 0)
        elif detection.corner_count >= 4:
            status = "Board READY | click lock reference"
            color = (0, 255, 255)
        else:
            status = "Need board lock before measuring"
            color = (0, 0, 255)

        debug = f"markers {detection.marker_count} corners {detection.corner_count}"
        cv2.putText(display, status, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.72, color, 2)
        cv2.putText(
            display,
            debug,
            (12, 62),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (220, 220, 220),
            2,
        )
        return display

    def _draw_detection_debug(
        self, display: np.ndarray, detection: cu.DetectionResult, y: int
    ) -> None:
        board_ok = detection.corner_count >= 4
        if board_ok:
            status = f"Board OK | markers {detection.marker_count} corners {detection.corner_count}"
            color = (0, 255, 0)
        else:
            status = f"No Board | markers {detection.marker_count} corners {detection.corner_count}"
            color = (0, 0, 255)
        cv2.putText(display, status, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
        if not board_ok and detection.hint:
            self.status_var.set(detection.hint.split("\n")[0])

    def _lock_measure_reference(self) -> None:
        if self._camera_matrix is None:
            messagebox.showwarning("提示", "请先完成相机标定")
            return

        detection = self._last_detection
        if detection.corners is None or detection.ids is None:
            messagebox.showwarning("提示", "请先将标定板放入画面，再锁定参考平面")
            return

        homography = cu.build_image_to_board_homography(
            detection.corners, detection.ids, board_size=detection.board_size
        )
        if homography is None:
            messagebox.showwarning("提示", "参考平面锁定失败，请调整标定板位置后重试")
            return

        self._measure_homography = homography
        self._recompute_distance_from_reference()
        self.status_var.set("参考平面已锁定，可移走标定板继续测距")
        self._update_info()

    def _clear_measure_reference(self) -> None:
        self._measure_homography = None
        self._reset_measure()
        self.status_var.set("参考平面已清除，请重新放置标定板并锁定")
        self._update_info()

    def _recompute_distance_from_reference(self) -> None:
        if len(self._measure_points) != 2 or self._measure_homography is None:
            self._distance_mm = None
            return

        board_pts = []
        for pt in self._measure_points:
            mapped = cu.map_image_point_to_board(pt, self._measure_homography)
            if mapped is None:
                self._distance_mm = None
                return
            board_pts.append(mapped)

        dist_m = cu.distance_on_board_plane(board_pts[0], board_pts[1])
        self._distance_mm = dist_m * 1000.0

    def _show_frame(self, frame: np.ndarray) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        scale = min(self.DISPLAY_WIDTH / w, self.DISPLAY_HEIGHT / h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        self._scale = (w / new_w, h / new_h)

        resized = cv2.resize(rgb, (new_w, new_h))
        image = Image.fromarray(resized)
        self._photo = ImageTk.PhotoImage(image=image)

        self.canvas.delete("all")
        x = (self.DISPLAY_WIDTH - new_w) // 2
        y = (self.DISPLAY_HEIGHT - new_h) // 2
        self.canvas.create_image(x, y, anchor=tk.NW, image=self._photo)
        self._canvas_offset = (x, y)
        self._canvas_size = (new_w, new_h)

    def _canvas_to_image(self, cx: int, cy: int) -> Optional[Tuple[int, int]]:
        if not hasattr(self, "_canvas_offset"):
            return None
        ox, oy = self._canvas_offset
        cw, ch = self._canvas_size
        if cx < ox or cy < oy or cx >= ox + cw or cy >= oy + ch:
            return None
        ix = int((cx - ox) * self._scale[0])
        iy = int((cy - oy) * self._scale[1])
        return ix, iy

    def _on_canvas_click(self, event: tk.Event) -> None:
        if self.mode.get() != "measure":
            return
        if self._camera_matrix is None:
            messagebox.showwarning("提示", "请先完成相机标定")
            return
        if self._measure_homography is None:
            messagebox.showwarning("提示", "请先锁定参考平面，再进行测量")
            return

        mapped = self._canvas_to_image(event.x, event.y)
        if mapped is None:
            return

        if len(self._measure_points) >= 2:
            self._measure_points.clear()
            self._distance_mm = None

        self._measure_points.append(mapped)
        self._recompute_distance_from_reference()

    def _reset_measure(self) -> None:
        self._measure_points.clear()
        self._distance_mm = None
        self.distance_var.set("距离: -- mm")

    def _capture_calib_frame(self) -> None:
        if self.cap is None:
            return
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("错误", "无法读取相机画面")
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detection = cu.detect_charuco_robust(gray, self.detector)
        corners, ids = detection.corners, detection.ids
        if corners is None:
            messagebox.showwarning("提示", detection.hint or "未检测到标定板，请调整位置后重试")
            return

        matched = cu.match_board_points(corners, ids, board_size=detection.board_size)
        if matched is None:
            messagebox.showwarning("提示", "角点匹配失败，请重试")
            return

        obj_pts, img_pts = matched
        self._calib_obj_points.append(obj_pts)
        self._calib_img_points.append(img_pts)
        self.status_var.set(f"已采集第 {len(self._calib_obj_points)} 帧")

    def _clear_calib_frames(self) -> None:
        self._calib_obj_points.clear()
        self._calib_img_points.clear()
        self.status_var.set("已清空采集数据")

    def _finish_calibration(self) -> None:
        if len(self._calib_obj_points) < config.CALIBRATION_MIN_FRAMES:
            messagebox.showwarning(
                "帧数不足",
                f"当前 {len(self._calib_obj_points)} 帧，至少需要 {config.CALIBRATION_MIN_FRAMES} 帧",
            )
            return
        if self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("错误", "无法读取相机画面")
            return

        image_size = (frame.shape[1], frame.shape[0])
        try:
            camera_matrix, dist_coeffs, reproj_error = cu.calibrate_from_samples(
                self._calib_obj_points, self._calib_img_points, image_size
            )
            cu.save_calibration(camera_matrix, dist_coeffs)
            self._reproj_error = reproj_error
            self._load_calibration()
            self.status_var.set(f"标定完成，重投影误差 {reproj_error:.4f} px")
            messagebox.showinfo(
                "标定成功",
                f"标定已保存。\n重投影误差: {reproj_error:.4f} px\n\n可切换到「距离测量」开始使用。",
            )
        except ValueError as exc:
            messagebox.showerror("标定失败", str(exc))

    def _open_board_generator(self) -> None:
        open_board_generator(self, on_params_changed=self._on_board_params_changed)

    def _open_board_folder(self) -> None:
        import os
        import subprocess

        folder = str(config.ROOT)
        if os.name == "nt":
            os.startfile(folder)
        else:
            subprocess.Popen(["xdg-open", folder])

    def _on_close(self) -> None:
        if self.cap is not None:
            self.cap.release()
        self.destroy()


def run_gui() -> None:
    app = MeasurementGUI()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
