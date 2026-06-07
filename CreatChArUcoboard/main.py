"""
ChArUco Board Generator
GUI application for creating, previewing, and exporting ChArUco calibration boards to PDF.
"""

import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk


# ---------------------------------------------------------------------------
# ArUco dictionary names (from OpenCV's predefined dictionaries)
# ---------------------------------------------------------------------------
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


def generate_charuco_board(board_w, board_h, sq_len, mk_len, dict_id):
    """Generate a ChArUco board image as a numpy array (BGR)."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(dict_id)
    board = cv2.aruco.CharucoBoard(
        (board_w, board_h), sq_len, mk_len, aruco_dict
    )
    dpi = 300
    board_px = int(board_w * sq_len * dpi / 25.4)
    board_py = int(board_h * sq_len * dpi / 25.4)
    board_img = board.generateImage((board_px, board_py), marginSize=0)
    return board_img, board


def get_board_physical_size_mm(board_w, board_h, sq_len):
    """Return (width_mm, height_mm) of the board."""
    return board_w * sq_len, board_h * sq_len


def bgr_to_pil(board_img):
    """Convert a BGR OpenCV image to a PIL RGB Image."""
    rgb = cv2.cvtColor(board_img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def mm_to_px(mm_val, dpi):
    """Convert millimeters to pixels at the given DPI."""
    return int(mm_val / 25.4 * dpi)


def format_board_info(dict_name, board_w, board_h, sq_len, mk_len, bw_mm, bh_mm, dpi=None):
    """Build caption lines describing the calibration board."""
    lines = [
        "ChArUco Calibration Board",
        f"Dictionary: {dict_name}    Grid: {board_w} x {board_h} squares",
        f"Square: {sq_len:.1f} mm    Marker: {mk_len:.1f} mm    "
        f"Physical size: {bw_mm:.1f} x {bh_mm:.1f} mm",
    ]
    if dpi is not None:
        lines.append(f"Export DPI: {dpi}")
    return lines


def _get_font(size_px):
    """Load a TrueType font, with fallbacks for Windows."""
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


def compose_board_with_caption(board_img, info_lines, dpi=300):
    """Return a PIL image with the board on top and info text below."""
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


def save_image_as_pdf(pil_img, file_path, page_size_mm, dpi=300, margin_mm=10):
    """Save a PIL image centered on a PDF page using Pillow."""
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


# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------
class ChArUcoBoardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ChArUco Board Generator")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)

        # State
        self._board_img = None
        self._board_object = None
        self._preview_tk = None

        self._build_ui()
        self._generate_board()

    # ---- UI construction --------------------------------------------------

    def _build_ui(self):
        # Main paned window: left=controls, right=preview
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        left = ttk.Frame(paned, width=320)
        right = ttk.Frame(paned)
        paned.add(left)
        paned.add(right)

        self._build_controls(left)
        self._build_preview(right)
        self._build_status_bar()

    def _build_controls(self, parent):
        frm = ttk.LabelFrame(parent, text="Parameters", padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        row = 0

        # Dictionary
        ttk.Label(frm, text="Dictionary:").grid(row=row, column=0, sticky="w", pady=3)
        self.dict_var = tk.StringVar(value="DICT_4X4_50")
        cb = ttk.Combobox(frm, textvariable=self.dict_var,
                          values=list(ARUCO_DICTS.keys()), state="readonly", width=22)
        cb.grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        # Board grid
        ttk.Label(frm, text="Squares X:").grid(row=row, column=0, sticky="w", pady=3)
        self.squares_x_var = tk.IntVar(value=5)
        ttk.Spinbox(frm, from_=2, to=20, textvariable=self.squares_x_var, width=10).grid(
            row=row, column=1, sticky="w", pady=3)
        row += 1

        ttk.Label(frm, text="Squares Y:").grid(row=row, column=0, sticky="w", pady=3)
        self.squares_y_var = tk.IntVar(value=7)
        ttk.Spinbox(frm, from_=2, to=20, textvariable=self.squares_y_var, width=10).grid(
            row=row, column=1, sticky="w", pady=3)
        row += 1

        # Square length (mm)
        ttk.Label(frm, text="Square length (mm):").grid(row=row, column=0, sticky="w", pady=3)
        self.sq_len_var = tk.DoubleVar(value=30.0)
        ttk.Spinbox(frm, from_=5.0, to=200.0, increment=1.0,
                    textvariable=self.sq_len_var, width=10).grid(
            row=row, column=1, sticky="w", pady=3)
        row += 1

        # Marker length (mm)
        ttk.Label(frm, text="Marker length (mm):").grid(row=row, column=0, sticky="w", pady=3)
        self.mk_len_var = tk.DoubleVar(value=20.0)
        ttk.Spinbox(frm, from_=2.0, to=190.0, increment=1.0,
                    textvariable=self.mk_len_var, width=10).grid(
            row=row, column=1, sticky="w", pady=3)
        row += 1

        # Page size
        ttk.Label(frm, text="Page size:").grid(row=row, column=0, sticky="w", pady=3)
        self.page_var = tk.StringVar(value="A4")
        cb_page = ttk.Combobox(frm, textvariable=self.page_var,
                               values=list(PAGE_SIZES_MM.keys()), state="readonly", width=10)
        cb_page.grid(row=row, column=1, sticky="w", pady=3)
        row += 1

        # DPI
        ttk.Label(frm, text="DPI:").grid(row=row, column=0, sticky="w", pady=3)
        self.dpi_var = tk.IntVar(value=300)
        ttk.Spinbox(frm, from_=72, to=1200, increment=50,
                    textvariable=self.dpi_var, width=10).grid(
            row=row, column=1, sticky="w", pady=3)
        row += 1

        # Separator
        ttk.Separator(frm, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1

        # Generate button
        btn_gen = ttk.Button(frm, text="Generate / Preview", command=self._generate_board)
        btn_gen.grid(row=row, column=0, columnspan=2, sticky="ew", pady=4)
        row += 1

        # Save PDF button
        btn_save = ttk.Button(frm, text="Save as PDF", command=self._save_pdf)
        btn_save.grid(row=row, column=0, columnspan=2, sticky="ew", pady=4)
        row += 1

        # Save PNG button
        btn_save_png = ttk.Button(frm, text="Save as PNG", command=self._save_png)
        btn_save_png.grid(row=row + 1, column=0, columnspan=2, sticky="ew", pady=4)

        # Info text
        self.info_var = tk.StringVar()
        ttk.Label(frm, textvariable=self.info_var, wraplength=280,
                  foreground="gray").grid(
            row=row + 2, column=0, columnspan=2, sticky="w", pady=(10, 0))

        frm.columnconfigure(1, weight=1)

    def _build_preview(self, parent):
        frm = ttk.LabelFrame(parent, text="Preview", padding=6)
        frm.pack(fill=tk.BOTH, expand=True)

        self.preview_canvas = tk.Canvas(frm, bg="#f0f0f0", highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

        # Bind resize to update preview scaling
        self.preview_canvas.bind("<Configure>", self._on_preview_resize)

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Ready")
        sb = ttk.Label(self.root, textvariable=self.status_var,
                       relief=tk.SUNKEN, anchor=tk.W, padding=(6, 2))
        sb.pack(side=tk.BOTTOM, fill=tk.X)

    # ---- Board generation ------------------------------------------------

    def _generate_board(self):
        try:
            dict_key = self.dict_var.get()
            dict_id = ARUCO_DICTS[dict_key]
            board_w = self.squares_x_var.get()
            board_h = self.squares_y_var.get()
            sq_len = float(self.sq_len_var.get())
            mk_len = float(self.mk_len_var.get())

            if mk_len >= sq_len:
                messagebox.showwarning(
                    "Invalid Size",
                    "Marker length must be smaller than square length.")
                return

            board_img, board_obj = generate_charuco_board(
                board_w, board_h, sq_len, mk_len, dict_id
            )

            self._board_img = board_img
            self._board_object = board_obj

            bw_mm, bh_mm = get_board_physical_size_mm(board_w, board_h, sq_len)
            self.info_var.set(
                f"Board: {board_w}x{board_h} squares\n"
                f"Physical size: {bw_mm:.1f} x {bh_mm:.1f} mm\n"
                f"Image: {board_img.shape[1]}x{board_img.shape[0]} px"
            )

            self._update_preview()
            self.status_var.set("Board generated successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate board:\n{e}")
            self.status_var.set("Error generating board")

    # ---- Preview ---------------------------------------------------------

    def _update_preview(self):
        if self._board_img is None:
            return

        pil_img = bgr_to_pil(self._board_img)

        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()

        if cw < 10 or ch < 10:
            cw, ch = 500, 400

        # Fit image inside canvas while keeping aspect ratio
        iw, ih = pil_img.size
        scale = min(cw / iw, ch / ih)
        new_w, new_h = int(iw * scale), int(ih * scale)

        pil_resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
        self._preview_tk = ImageTk.PhotoImage(pil_resized)

        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(
            cw // 2, ch // 2, image=self._preview_tk, anchor=tk.CENTER
        )

    def _on_preview_resize(self, event):
        self._update_preview()

    # ---- Save ------------------------------------------------------------

    def _get_board_info_lines(self, dpi=None):
        board_w = self.squares_x_var.get()
        board_h = self.squares_y_var.get()
        sq_len = float(self.sq_len_var.get())
        mk_len = float(self.mk_len_var.get())
        bw_mm, bh_mm = get_board_physical_size_mm(board_w, board_h, sq_len)
        return format_board_info(
            self.dict_var.get(), board_w, board_h, sq_len, mk_len, bw_mm, bh_mm, dpi
        )

    def _save_pdf(self):
        if self._board_img is None:
            messagebox.showwarning("No Board", "Generate a board first.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialdir=os.getcwd(),
            initialfile="charuco_board.pdf",
        )
        if not file_path:
            return

        try:
            page_key = self.page_var.get()
            page_size_mm = PAGE_SIZES_MM[page_key]
            dpi_val = self.dpi_var.get()

            info_lines = self._get_board_info_lines(dpi=dpi_val)
            composed = compose_board_with_caption(
                self._board_img, info_lines, dpi=dpi_val
            )
            save_image_as_pdf(composed, file_path, page_size_mm, dpi=dpi_val)

            self.status_var.set(f"PDF saved: {os.path.basename(file_path)}")
            messagebox.showinfo("Saved", f"PDF saved to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PDF:\n{e}")
            self.status_var.set("Error saving PDF")

    def _save_png(self):
        if self._board_img is None:
            messagebox.showwarning("No Board", "Generate a board first.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG images", "*.png")],
            initialdir=os.getcwd(),
            initialfile="charuco_board.png",
        )
        if not file_path:
            return

        try:
            dpi_val = self.dpi_var.get()
            info_lines = self._get_board_info_lines(dpi=dpi_val)
            pil_img = compose_board_with_caption(
                self._board_img, info_lines, dpi=dpi_val
            )
            pil_img.save(file_path, format="PNG", dpi=(dpi_val, dpi_val))

            self.status_var.set(f"PNG saved: {os.path.basename(file_path)}")
            messagebox.showinfo("Saved", f"PNG saved to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PNG:\n{e}")
            self.status_var.set("Error saving PNG")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ChArUcoBoardApp(root)
    root.mainloop()
