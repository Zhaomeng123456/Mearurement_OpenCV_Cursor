"""ChArUco 标定板生成器 GUI（可嵌入 Toplevel 或独立运行）"""

from __future__ import annotations

import os
from collections.abc import Callable
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import cv2
from PIL import Image, ImageTk

import board_generator as bg
import board_params as bp
import config

_active_window: Optional[tk.Misc] = None
_standalone_root: Optional[tk.Tk] = None
_active_app: Optional["ChArUcoBoardApp"] = None


class ChArUcoBoardApp:
    def __init__(
        self,
        root: tk.Misc,
        on_params_changed: Callable[[], None] | None = None,
    ) -> None:
        self.root = root
        self._on_params_changed = on_params_changed
        self.root.title("ChArUco 标定板生成器")
        if isinstance(root, tk.Toplevel):
            root.protocol("WM_DELETE_WINDOW", self._on_close)
        elif isinstance(root, tk.Tk):
            root.geometry("1100x720")
            root.minsize(900, 600)

        self._board_img = None
        self._preview_tk: Optional[ImageTk.PhotoImage] = None

        self._build_ui()
        self.reload_from_active_params()
        self._generate_board()

    def reload_from_active_params(self) -> None:
        """从当前运行时标定参数刷新控件。"""
        d = bg.defaults_from_active()
        self.dict_var.set(d.dict_name)
        self.squares_x_var.set(d.squares_x)
        self.squares_y_var.set(d.squares_y)
        self.sq_len_var.set(d.square_length_mm)
        self.mk_len_var.set(d.marker_length_mm)

    def _build_ui(self) -> None:
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        left = ttk.Frame(paned, width=320)
        right = ttk.Frame(paned)
        paned.add(left)
        paned.add(right)

        self._build_controls(left)
        self._build_preview(right)
        self._build_status_bar()

    def _build_controls(self, parent: ttk.Frame) -> None:
        frm = ttk.LabelFrame(parent, text="参数", padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        row = 0
        d = bg.defaults_from_active()

        ttk.Label(frm, text="ArUco 字典:").grid(row=row, column=0, sticky="w", pady=3)
        self.dict_var = tk.StringVar(value=d.dict_name)
        ttk.Combobox(
            frm,
            textvariable=self.dict_var,
            values=list(bg.ARUCO_DICTS.keys()),
            state="readonly",
            width=22,
        ).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        ttk.Label(frm, text="方格数 X:").grid(row=row, column=0, sticky="w", pady=3)
        self.squares_x_var = tk.IntVar(value=d.squares_x)
        ttk.Spinbox(frm, from_=2, to=20, textvariable=self.squares_x_var, width=10).grid(
            row=row, column=1, sticky="w", pady=3
        )
        row += 1

        ttk.Label(frm, text="方格数 Y:").grid(row=row, column=0, sticky="w", pady=3)
        self.squares_y_var = tk.IntVar(value=d.squares_y)
        ttk.Spinbox(frm, from_=2, to=20, textvariable=self.squares_y_var, width=10).grid(
            row=row, column=1, sticky="w", pady=3
        )
        row += 1

        ttk.Label(frm, text="方格边长 (mm):").grid(row=row, column=0, sticky="w", pady=3)
        self.sq_len_var = tk.DoubleVar(value=d.square_length_mm)
        ttk.Spinbox(
            frm, from_=5.0, to=200.0, increment=1.0, textvariable=self.sq_len_var, width=10
        ).grid(row=row, column=1, sticky="w", pady=3)
        row += 1

        ttk.Label(frm, text="标记边长 (mm):").grid(row=row, column=0, sticky="w", pady=3)
        self.mk_len_var = tk.DoubleVar(value=d.marker_length_mm)
        ttk.Spinbox(
            frm, from_=2.0, to=190.0, increment=1.0, textvariable=self.mk_len_var, width=10
        ).grid(row=row, column=1, sticky="w", pady=3)
        row += 1

        ttk.Label(frm, text="页面尺寸:").grid(row=row, column=0, sticky="w", pady=3)
        self.page_var = tk.StringVar(value="A4")
        ttk.Combobox(
            frm,
            textvariable=self.page_var,
            values=list(bg.PAGE_SIZES_MM.keys()),
            state="readonly",
            width=10,
        ).grid(row=row, column=1, sticky="w", pady=3)
        row += 1

        ttk.Label(frm, text="DPI:").grid(row=row, column=0, sticky="w", pady=3)
        self.dpi_var = tk.IntVar(value=300)
        ttk.Spinbox(
            frm, from_=72, to=1200, increment=50, textvariable=self.dpi_var, width=10
        ).grid(row=row, column=1, sticky="w", pady=3)
        row += 1

        ttk.Separator(frm, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10
        )
        row += 1

        ttk.Button(frm, text="生成 / 预览", command=self._generate_board).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=4
        )
        row += 1

        ttk.Button(frm, text="应用到标定参数", command=self._apply_params_only).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=4
        )
        row += 1

        ttk.Button(frm, text="保存为 PDF", command=self._save_pdf).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=4
        )
        row += 1

        ttk.Button(frm, text="保存为 PNG", command=self._save_png).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=4
        )
        row += 1

        ttk.Button(frm, text="保存到项目默认路径", command=self._save_default_png).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=4
        )
        row += 1

        self.info_var = tk.StringVar()
        ttk.Label(frm, textvariable=self.info_var, wraplength=280, foreground="gray").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )

        frm.columnconfigure(1, weight=1)

    def _build_preview(self, parent: ttk.Frame) -> None:
        frm = ttk.LabelFrame(parent, text="预览", padding=6)
        frm.pack(fill=tk.BOTH, expand=True)

        self.preview_canvas = tk.Canvas(frm, bg="#f0f0f0", highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas.bind("<Configure>", self._on_preview_resize)

    def _build_status_bar(self) -> None:
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(6, 2)
        ).pack(side=tk.BOTTOM, fill=tk.X)

    def _current_params(self) -> tuple[int, int, float, float, str]:
        return (
            self.squares_x_var.get(),
            self.squares_y_var.get(),
            float(self.sq_len_var.get()),
            float(self.mk_len_var.get()),
            self.dict_var.get(),
        )

    def _apply_params_to_project(self) -> None:
        board_w, board_h, sq_len, mk_len, dict_name = self._current_params()
        if mk_len >= sq_len:
            raise ValueError("标记边长必须小于方格边长")
        bp.update(
            bp.from_mm_values(board_w, board_h, sq_len, mk_len, dict_name),
            persist=True,
        )
        if self._on_params_changed:
            self._on_params_changed()

    def _apply_params_only(self) -> None:
        try:
            self._apply_params_to_project()
            self.status_var.set("标定参数已更新")
            messagebox.showinfo("完成", "当前参数已应用到标定/测距模块。")
        except ValueError as exc:
            messagebox.showwarning("无效尺寸", str(exc))
        except Exception as exc:
            messagebox.showerror("错误", f"更新参数失败:\n{exc}")

    def _generate_board(self) -> None:
        try:
            board_w, board_h, sq_len, mk_len, dict_key = self._current_params()
            dict_id = bg.ARUCO_DICTS[dict_key]

            if mk_len >= sq_len:
                messagebox.showwarning("无效尺寸", "标记边长必须小于方格边长。")
                return

            dpi_val = self.dpi_var.get()
            board_img, _ = bg.generate_charuco_board(
                board_w, board_h, sq_len, mk_len, dict_id, dpi=dpi_val
            )
            self._board_img = board_img

            bw_mm, bh_mm = bg.get_board_physical_size_mm(board_w, board_h, sq_len)
            self.info_var.set(
                f"网格: {board_w}×{board_h}\n"
                f"物理尺寸: {bw_mm:.1f} × {bh_mm:.1f} mm\n"
                f"图像: {board_img.shape[1]}×{board_img.shape[0]} px\n"
                f"保存时将同步到标定参数"
            )

            self._update_preview()
            self.status_var.set("标定板生成成功")

        except Exception as exc:
            messagebox.showerror("错误", f"生成标定板失败:\n{exc}")
            self.status_var.set("生成失败")

    def _update_preview(self) -> None:
        if self._board_img is None:
            return

        pil_img = bg.bgr_to_pil(self._board_img)

        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw < 10 or ch < 10:
            cw, ch = 500, 400

        iw, ih = pil_img.size
        scale = min(cw / iw, ch / ih)
        new_w, new_h = int(iw * scale), int(ih * scale)

        pil_resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
        self._preview_tk = ImageTk.PhotoImage(pil_resized)

        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(cw // 2, ch // 2, image=self._preview_tk, anchor=tk.CENTER)

    def _on_preview_resize(self, _event) -> None:
        self._update_preview()

    def _get_board_info_lines(self, dpi: Optional[int] = None) -> list[str]:
        board_w, board_h, sq_len, mk_len, dict_key = self._current_params()
        bw_mm, bh_mm = bg.get_board_physical_size_mm(board_w, board_h, sq_len)
        return bg.format_board_info(dict_key, board_w, board_h, sq_len, mk_len, bw_mm, bh_mm, dpi)

    def _save_composed_png(self, file_path: str, dpi_val: int, with_caption: bool = True) -> None:
        if with_caption:
            info_lines = self._get_board_info_lines(dpi=dpi_val)
            pil_img = bg.compose_board_with_caption(self._board_img, info_lines, dpi=dpi_val)
            pil_img.save(file_path, format="PNG", dpi=(dpi_val, dpi_val))
        else:
            bg.bgr_to_pil(self._board_img).save(file_path, format="PNG", dpi=(dpi_val, dpi_val))

    def _save_pdf(self) -> None:
        if self._board_img is None:
            messagebox.showwarning("提示", "请先生成标定板。")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF 文件", "*.pdf")],
            initialdir=str(config.ROOT),
            initialfile="charuco_board.pdf",
        )
        if not file_path:
            return

        try:
            self._apply_params_to_project()
            page_size_mm = bg.PAGE_SIZES_MM[self.page_var.get()]
            dpi_val = self.dpi_var.get()
            info_lines = self._get_board_info_lines(dpi=dpi_val)
            composed = bg.compose_board_with_caption(self._board_img, info_lines, dpi=dpi_val)
            bg.save_image_as_pdf(composed, file_path, page_size_mm, dpi=dpi_val)

            self.status_var.set(f"PDF 已保存: {os.path.basename(file_path)}")
            messagebox.showinfo("完成", f"PDF 已保存，标定参数已同步。\n{file_path}")
        except ValueError as exc:
            messagebox.showwarning("无效尺寸", str(exc))
        except Exception as exc:
            messagebox.showerror("错误", f"保存 PDF 失败:\n{exc}")
            self.status_var.set("保存 PDF 失败")

    def _save_png(self) -> None:
        if self._board_img is None:
            messagebox.showwarning("提示", "请先生成标定板。")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG 图片", "*.png")],
            initialdir=str(config.ROOT),
            initialfile="charuco_board.png",
        )
        if not file_path:
            return

        try:
            self._apply_params_to_project()
            dpi_val = self.dpi_var.get()
            self._save_composed_png(file_path, dpi_val)
            self.status_var.set(f"PNG 已保存: {os.path.basename(file_path)}")
            messagebox.showinfo("完成", f"PNG 已保存，标定参数已同步。\n{file_path}")
        except ValueError as exc:
            messagebox.showwarning("无效尺寸", str(exc))
        except Exception as exc:
            messagebox.showerror("错误", f"保存 PNG 失败:\n{exc}")
            self.status_var.set("保存 PNG 失败")

    def _save_default_png(self) -> None:
        if self._board_img is None:
            messagebox.showwarning("提示", "请先生成标定板。")
            return

        try:
            self._apply_params_to_project()
            cv2.imwrite(str(config.BOARD_IMAGE_FILE), self._board_img)
            self.status_var.set(f"已保存: {config.BOARD_IMAGE_FILE.name}")
            messagebox.showinfo("完成", f"标定板已保存，标定参数已同步。\n{config.BOARD_IMAGE_FILE}")
        except ValueError as exc:
            messagebox.showwarning("无效尺寸", str(exc))
        except Exception as exc:
            messagebox.showerror("错误", f"保存失败:\n{exc}")
            self.status_var.set("保存失败")

    def _on_close(self) -> None:
        global _active_window, _active_app
        _active_window = None
        _active_app = None
        self.root.destroy()


def open_board_generator(
    parent: tk.Misc | None = None,
    on_params_changed: Callable[[], None] | None = None,
) -> tk.Misc:
    """打开标定板生成器。parent 为 None 时创建独立 Tk 窗口。"""
    global _active_window, _standalone_root, _active_app

    if _active_window is not None and _active_window.winfo_exists():
        if _active_app is not None:
            _active_app.reload_from_active_params()
            if on_params_changed is not None:
                _active_app._on_params_changed = on_params_changed
        _active_window.lift()
        _active_window.focus_force()
        return _active_window

    if parent is None:
        _standalone_root = tk.Tk()
        window = _standalone_root
    else:
        window = tk.Toplevel(parent)
        window.geometry("1100x720")
        window.minsize(900, 600)

    _active_window = window
    _active_app = ChArUcoBoardApp(window, on_params_changed=on_params_changed)

    if parent is None:
        window.mainloop()

    return window
