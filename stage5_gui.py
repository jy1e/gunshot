import glob
import io
import json
import os
import re
import subprocess
import sys
import threading
import textwrap
from contextlib import redirect_stderr, redirect_stdout
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk
except ImportError:
    messagebox.showerror(
        "Missing Dependency",
        "customtkinter is required to run this application.\n"
        "Install it with:\n\n"
        "pip install customtkinter",
    )
    sys.exit(1)

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image
import tkinterdnd2 as tkdnd

from stage1_parser import parse_file
from stage3_pytest import generate_test_file
from stage4_driver import RCCarDriver

FONT_FAMILY = "Segoe UI"
FONT_KOREAN = "Malgun Gothic"
NO_PORT_LABEL = "No ports"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DRIVER_TYPE_OPTIONS = {
    "RC Car": "rc_car",
    "Web/App": "web_app",
}
BROWSER_TYPE_OPTIONS = ["Chrome", "Edge"]
BASE_URL_PLACEHOLDER = "https://example.com"

ICON_ICO_PATH = r"C:\Users\daame\Desktop\gunshot\ico\icon.ico"
LOGO_PATH = r"C:\Users\daame\Desktop\gunshot\ico\logo.png"

COLORS = {
    "bg": "#0a0a0a",
    "sidebar": "#111111",
    "panel": "#1a1a1a",
    "input": "#0f0f0f",
    "border": "#353535",
    "border_soft": "#242424",
    "line": "#d8d8d8",
    "line_dim": "#6f6f6f",
    "accent_red": "#CC0000",
    "accent_red_hover": "#FF1A1A",
    "accent_yellow": "#FFA500",
    "accent_yellow_hover": "#FFBC42",
    "text": "#ffffff",
    "text_muted": "#888888",
    "success": "#4ec9b0",
    "error": "#CC0000",
}


def get_available_ports():
    return RCCarDriver().scan_ports()


def set_taskbar_icon(hwnd, ico_path):
    try:
        import win32api
        import win32con
        import win32gui

        icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
        hicon = win32gui.LoadImage(
            None, ico_path, win32con.IMAGE_ICON, 0, 0, icon_flags
        )
        win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, hicon)
        win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, hicon)
    except Exception:
        pass


class Stage5GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GUNSHOT")
        self.root.geometry("1100x720")
        self.root.minsize(980, 700)
        self.root.configure(fg_color=COLORS["bg"])

        self.parsed_text = ""
        self.port_values = []
        self.selected_port = "COM3"
        self.selected_driver_type = "rc_car"
        self.selected_browser = "chrome"
        self.base_url = ""
        self.chart_canvas = None
        self.last_run_context = None

        self._init_fonts()
        self._build_ui()
        self._update_driver_option_controls()
        self.show_main_page()
        self.refresh_ports(silent=True)
        self.root.after(300, self._set_taskbar_icon)

    def _set_taskbar_icon(self):
        try:
            hwnd = self.root.winfo_id()
            set_taskbar_icon(hwnd, ICON_ICO_PATH)
        except Exception:
            pass

    def _init_fonts(self):
        self.font_title = ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold")
        self.font_body = ctk.CTkFont(family=FONT_KOREAN, size=12)
        self.font_body_bold = ctk.CTkFont(family=FONT_KOREAN, size=12, weight="bold")
        self.font_button = ctk.CTkFont(family="Consolas", size=13, weight="bold")
        self.font_icon = ctk.CTkFont(family="Consolas", size=18)
        self.font_log = ctk.CTkFont(family=FONT_KOREAN, size=12)
        self.font_section = ctk.CTkFont(family="Consolas", size=12, weight="bold")
        self.font_value = ctk.CTkFont(family="Consolas", size=28, weight="bold")
        self.font_table_header = ctk.CTkFont(family=FONT_KOREAN, size=11, weight="bold")
        self.font_table = ctk.CTkFont(family=FONT_KOREAN, size=11)
        self.font_mono = ctk.CTkFont(family=FONT_KOREAN, size=11)
        self.font_subtitle = ctk.CTkFont(family="Consolas", size=11)
        self.font_hint = ctk.CTkFont(family="Consolas", size=11)
        self.font_small_button = ctk.CTkFont(family=FONT_KOREAN, size=10, weight="bold")
        self.font_result = ctk.CTkFont(family="Consolas", size=12, weight="bold")

    def _create_section_header(self, parent, text, line_color):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.grid_columnconfigure(0, weight=0)
        header.grid_columnconfigure(1, weight=1)

        label = ctk.CTkLabel(
            header,
            text=text,
            font=self.font_section,
            text_color=COLORS["text"],
        )
        label.grid(row=0, column=0, sticky="w")

        accent_line = ctk.CTkFrame(
            header,
            fg_color=line_color,
            width=42,
            height=2,
            corner_radius=0,
        )
        accent_line.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(2, 0))
        return header

    def _create_summary_card(self, parent, title, value_color):
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["panel"],
            corner_radius=4,
            border_width=1,
            border_color=COLORS["accent_red"],
        )
        card.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            card,
            text=title,
            font=self.font_body_bold,
            text_color=COLORS["text_muted"],
        )
        title_label.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        value_label = ctk.CTkLabel(
            card,
            text="0",
            font=self.font_value,
            text_color=value_color,
        )
        value_label.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 14))

        return card, value_label

    def _configure_detail_columns(self, widget):
        widget.grid_columnconfigure(0, weight=3, minsize=160)
        widget.grid_columnconfigure(1, weight=1, minsize=90)
        widget.grid_columnconfigure(2, weight=1, minsize=96)
        widget.grid_columnconfigure(3, weight=1, minsize=128)

    def _build_ui(self):
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_content()

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self.root,
            width=200,
            corner_radius=0,
            fg_color=COLORS["sidebar"],
            border_width=1,
            border_color=COLORS["border_soft"],
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        try:
            logo_img = ctk.CTkImage(
                light_image=Image.open(LOGO_PATH),
                dark_image=Image.open(LOGO_PATH),
                size=(156, 56),
            )
            logo_label = ctk.CTkLabel(sidebar, image=logo_img, text="")
            logo_label.pack(pady=(24, 28))
            self.logo_img = logo_img
        except Exception:
            ctk.CTkLabel(
                sidebar,
                text="GUNSHOT",
                font=self.font_title,
                text_color=COLORS["text"],
            ).pack(pady=(24, 28))

        ctk.CTkLabel(
            sidebar,
            text="AI-Based Black Box Test Automation",
            font=self.font_subtitle,
            text_color=COLORS["text_muted"],
        ).pack(pady=(0, 20))

        self.btn_select = ctk.CTkButton(
            sidebar,
            text="SELECT FILE",
            command=self.on_select_file,
            height=40,
            corner_radius=5,
            font=self.font_button,
            fg_color=COLORS["panel"],
            hover_color="#202020",
            border_width=2,
            border_color=COLORS["line"],
            text_color=COLORS["text"],
        )
        self.btn_select.pack(fill="x", padx=16, pady=(0, 10))

        self.btn_generate = ctk.CTkButton(
            sidebar,
            text="GENERATE TC",
            command=self.on_generate_tc,
            height=40,
            corner_radius=5,
            font=self.font_button,
            fg_color=COLORS["accent_red"],
            hover_color=COLORS["accent_red_hover"],
            text_color=COLORS["text"],
        )
        self.btn_generate.pack(fill="x", padx=16, pady=(0, 10))

        ctk.CTkLabel(
            sidebar,
            text=(
                "1. Upload requirements document\n"
                "2. Connect target hardware via serial\n"
                "3. Generate & execute test cases"
            ),
            font=self.font_hint,
            text_color=COLORS["text_muted"],
            justify="left",
        ).pack(side="bottom", anchor="w", padx=16, pady=20)

    def _build_content(self):
        self.content = ctk.CTkFrame(self.root, corner_radius=0, fg_color=COLORS["bg"])
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self._build_main_page()
        self._build_result_page()

    def _build_main_page(self):
        self.main_page = ctk.CTkFrame(self.content, fg_color=COLORS["bg"], corner_radius=0)
        self.main_page.grid(row=0, column=0, sticky="nsew")
        self.main_page.grid_columnconfigure(0, weight=1)
        for row_index in range(5):
            self.main_page.grid_rowconfigure(row_index, weight=0)
        self.main_page.grid_rowconfigure(5, weight=1)

        file_panel = ctk.CTkFrame(
            self.main_page,
            fg_color=COLORS["panel"],
            corner_radius=4,
            border_width=1,
            border_color=COLORS["border"],
        )
        file_panel.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        file_panel.grid_columnconfigure(0, weight=1)

        self._create_section_header(
            file_panel,
            "Requirements File",
            COLORS["line"],
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.filepath_entry = ctk.CTkEntry(
            file_panel,
            placeholder_text="No file selected",
            height=36,
            corner_radius=4,
            font=self.font_mono,
            fg_color=COLORS["input"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
        )
        self.filepath_entry.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.filepath_entry.drop_target_register(tkdnd.DND_FILES)
        self.filepath_entry.dnd_bind("<<Drop>>", self.on_drop_file)

        driver_panel = ctk.CTkFrame(
            self.main_page,
            fg_color=COLORS["panel"],
            corner_radius=4,
            border_width=1,
            border_color=COLORS["border"],
        )
        driver_panel.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        driver_panel.grid_columnconfigure(0, weight=1)

        self._create_section_header(
            driver_panel,
            "Driver Type",
            COLORS["line_dim"],
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.driver_type_menu = ctk.CTkOptionMenu(
            driver_panel,
            values=list(DRIVER_TYPE_OPTIONS.keys()),
            height=36,
            corner_radius=4,
            font=self.font_mono,
            fg_color=COLORS["input"],
            button_color=COLORS["border"],
            button_hover_color="#4a4a4a",
            dropdown_fg_color=COLORS["panel"],
            dropdown_hover_color="#252525",
            text_color=COLORS["text"],
            command=self.on_driver_type_change,
        )
        self.driver_type_menu.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.driver_type_menu.set("RC Car")

        self.browser_type_panel = ctk.CTkFrame(
            self.main_page,
            fg_color=COLORS["panel"],
            corner_radius=4,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.browser_type_panel.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.browser_type_panel.grid_columnconfigure(0, weight=1)

        self._create_section_header(
            self.browser_type_panel,
            "Browser Type",
            COLORS["line_dim"],
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.browser_type_menu = ctk.CTkOptionMenu(
            self.browser_type_panel,
            values=BROWSER_TYPE_OPTIONS,
            height=36,
            corner_radius=4,
            font=self.font_mono,
            fg_color=COLORS["input"],
            button_color=COLORS["border"],
            button_hover_color="#4a4a4a",
            dropdown_fg_color=COLORS["panel"],
            dropdown_hover_color="#252525",
            text_color=COLORS["text"],
        )
        self.browser_type_menu.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.browser_type_menu.set("Chrome")

        self.url_panel = ctk.CTkFrame(
            self.main_page,
            fg_color=COLORS["panel"],
            corner_radius=4,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.url_panel.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.url_panel.grid_columnconfigure(0, weight=1)

        self._create_section_header(
            self.url_panel,
            "Base URL",
            COLORS["line_dim"],
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.url_entry = ctk.CTkEntry(
            self.url_panel,
            placeholder_text=BASE_URL_PLACEHOLDER,
            height=36,
            corner_radius=4,
            font=self.font_mono,
            fg_color=COLORS["input"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
        )
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))

        port_panel = ctk.CTkFrame(
            self.main_page,
            fg_color=COLORS["panel"],
            corner_radius=4,
            border_width=1,
            border_color=COLORS["border"],
        )
        port_panel.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.port_panel = port_panel

        port_header = self._create_section_header(
            port_panel,
            "Serial Port",
            COLORS["line_dim"],
        )
        port_header.pack(anchor="w", padx=16, pady=(14, 8))

        port_row = ctk.CTkFrame(port_panel, fg_color="transparent")
        port_row.pack(fill="x", padx=16, pady=(0, 14))

        self.port_menu = ctk.CTkOptionMenu(
            port_row,
            values=[NO_PORT_LABEL],
            height=36,
            width=220,
            corner_radius=4,
            font=self.font_mono,
            fg_color=COLORS["input"],
            button_color=COLORS["border"],
            button_hover_color="#4a4a4a",
            dropdown_fg_color=COLORS["panel"],
            dropdown_hover_color="#252525",
            text_color=COLORS["text"],
        )
        self.port_menu.pack(side="left")
        self.port_menu.set(NO_PORT_LABEL)

        self.btn_refresh = ctk.CTkButton(
            port_row,
            text="↻",
            width=40,
            height=36,
            corner_radius=4,
            font=self.font_icon,
            fg_color=COLORS["input"],
            hover_color="#2a2a2a",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            command=self.refresh_ports,
        )
        self.btn_refresh.pack(side="left", padx=(8, 0))

        log_panel = ctk.CTkFrame(
            self.main_page,
            fg_color=COLORS["panel"],
            corner_radius=4,
            border_width=1,
            border_color=COLORS["accent_red"],
        )
        log_panel.grid(row=5, column=0, sticky="nsew", padx=20, pady=(0, 20))
        log_panel.grid_columnconfigure(0, weight=1)
        log_panel.grid_rowconfigure(1, weight=1)

        self.main_page.grid_rowconfigure(5, weight=1)

        log_header_row = ctk.CTkFrame(log_panel, fg_color="transparent")
        log_header_row.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        log_header_row.grid_columnconfigure(1, weight=0)

        self._create_section_header(
            log_header_row,
            "Test Results",
            COLORS["accent_red"],
        ).grid(row=0, column=0, sticky="w")

        self.btn_retry_results = ctk.CTkButton(
            log_header_row,
            text="↻",
            width=36,
            height=32,
            corner_radius=4,
            font=self.font_icon,
            fg_color=COLORS["input"],
            hover_color="#2a2a2a",
            border_width=1,
            border_color=COLORS["accent_red"],
            text_color=COLORS["text"],
            state="disabled",
            command=self.retry_last_test_run,
        )
        self.btn_retry_results.grid(row=0, column=1, sticky="w", padx=(8, 0))

        self.result_text = ctk.CTkTextbox(
            log_panel,
            corner_radius=4,
            fg_color="#0b0b0b",
            border_width=1,
            border_color=COLORS["border_soft"],
            text_color=COLORS["text"],
            font=self.font_log,
            wrap="word",
        )
        self.result_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.result_text.configure(state="disabled")

    def _build_result_page(self):
        self.result_page = ctk.CTkFrame(self.content, fg_color=COLORS["bg"], corner_radius=0)
        self.result_page.grid(row=0, column=0, sticky="nsew")
        self.result_page.grid_columnconfigure(0, weight=1)
        self.result_page.grid_rowconfigure(1, weight=1)

        summary_row = ctk.CTkFrame(self.result_page, fg_color="transparent")
        summary_row.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        for column in range(3):
            summary_row.grid_columnconfigure(column, weight=1)

        total_card, self.total_count_label = self._create_summary_card(
            summary_row, "총 TC 수", COLORS["text"]
        )
        total_card.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        pass_card, self.pass_count_label = self._create_summary_card(
            summary_row, "PASS 수", COLORS["success"]
        )
        pass_card.grid(row=0, column=1, sticky="ew", padx=8)

        fail_card, self.fail_count_label = self._create_summary_card(
            summary_row, "FAIL 수", COLORS["accent_red"]
        )
        fail_card.grid(row=0, column=2, sticky="ew", padx=(8, 0))

        center_row = ctk.CTkFrame(self.result_page, fg_color="transparent")
        center_row.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        center_row.grid_columnconfigure(0, weight=2)
        center_row.grid_columnconfigure(1, weight=7)
        center_row.grid_rowconfigure(0, weight=1)

        chart_panel = ctk.CTkFrame(
            center_row,
            fg_color=COLORS["panel"],
            corner_radius=4,
            border_width=1,
            border_color=COLORS["accent_red"],
        )
        chart_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        chart_panel.grid_columnconfigure(0, weight=1)
        chart_panel.grid_rowconfigure(1, weight=1)

        self._create_section_header(
            chart_panel,
            "PASS / FAIL Ratio",
            COLORS["accent_red"],
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.chart_body = ctk.CTkFrame(chart_panel, fg_color=COLORS["bg"], corner_radius=4)
        self.chart_body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        table_panel = ctk.CTkFrame(
            center_row,
            fg_color=COLORS["panel"],
            corner_radius=4,
            border_width=1,
            border_color=COLORS["accent_red"],
        )
        table_panel.grid(row=0, column=1, sticky="nsew")
        table_panel.grid_columnconfigure(0, weight=1)
        table_panel.grid_rowconfigure(1, weight=1)

        self._create_section_header(
            table_panel,
            "TC Detail",
            COLORS["accent_red"],
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.table_scroll = ctk.CTkScrollableFrame(
            table_panel,
            fg_color=COLORS["input"],
            corner_radius=4,
            border_width=1,
            border_color=COLORS["border_soft"],
        )
        self.table_scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.table_scroll.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(self.result_page, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))

        self.btn_close_result = ctk.CTkButton(
            footer,
            text="닫기",
            command=self.show_main_page,
            height=40,
            width=140,
            corner_radius=5,
            font=self.font_body_bold,
            fg_color=COLORS["panel"],
            hover_color="#202020",
            border_width=1,
            border_color=COLORS["accent_red"],
            text_color=COLORS["text"],
        )
        self.btn_close_result.pack(anchor="e")

    def show_main_page(self):
        self.result_page.grid_remove()
        self.main_page.grid()

    def show_result_page(self):
        self.main_page.grid_remove()
        self.result_page.grid()

    def on_driver_type_change(self, selected_label):
        self.selected_driver_type = DRIVER_TYPE_OPTIONS.get(selected_label, "rc_car")
        self._update_driver_option_controls()

    def _update_port_controls(self):
        is_serial_driver = self.selected_driver_type == "rc_car"
        self.port_menu.configure(state="normal" if is_serial_driver else "disabled")
        self.btn_refresh.configure(state="normal" if is_serial_driver else "disabled")
        if not is_serial_driver:
            self.port_menu.set(NO_PORT_LABEL)
        else:
            current = self.port_menu.get()
            if current not in self.port_menu.cget("values"):
                self.port_menu.set(self.port_menu.cget("values")[0])

    def _update_driver_option_controls(self):
        is_serial_driver = self.selected_driver_type == "rc_car"
        if is_serial_driver:
            self.port_panel.grid()
            self.browser_type_panel.grid_remove()
            self.url_panel.grid_remove()
        else:
            self.port_panel.grid_remove()
            self.browser_type_panel.grid()
            self.url_panel.grid()
        self._update_port_controls()

    def log(self, message):
        self.result_text.configure(state="normal")
        self.result_text.insert("end", message + "\n")
        self.result_text.see("end")
        self.result_text.configure(state="disabled")

    def refresh_ports(self, silent=False):
        ports = get_available_ports()
        self.port_values = ports
        values = ports if ports else [NO_PORT_LABEL]

        self.port_menu.configure(values=values)
        if ports:
            current = self.port_menu.get()
            if current not in values:
                self.port_menu.set(ports[0])
            if not silent:
                self.log(f"[Port] {len(ports)} detected: {', '.join(ports)}")
        else:
            self.port_menu.set(NO_PORT_LABEL)
            if not silent:
                self.log("[Port] No serial ports available.")
        self._update_port_controls()

    def on_select_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Requirements File",
            filetypes=[
                ("Supported files", "*.docx *.pdf *.txt"),
                ("Word", "*.docx"),
                ("PDF", "*.pdf"),
                ("Text", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not filepath:
            return

        self._set_requirements_filepath(filepath)

    def _set_requirements_filepath(self, filepath):
        self.filepath_entry.delete(0, "end")
        self.filepath_entry.insert(0, filepath)
        self.log(f"[File] {filepath}")

        try:
            self.parsed_text = parse_file(filepath)
            preview = self.parsed_text[:200].replace("\n", " ")
            if len(self.parsed_text) > 200:
                preview += "..."
            self.log(f"[Parse] parse_file() complete ({len(self.parsed_text)} chars)")
            self.log(f"[Preview] {preview}")
        except Exception as exc:
            self.parsed_text = ""
            self.log(f"[Error] parse_file() — {exc}")
            messagebox.showerror("File Parse Error", str(exc))

    def on_drop_file(self, event):
        try:
            paths = self.root.tk.splitlist(event.data)
        except Exception:
            paths = [event.data]
        if not paths:
            return "break"

        filepath = paths[0]
        if filepath.startswith("{") and filepath.endswith("}"):
            filepath = filepath[1:-1]

        if os.path.isdir(filepath):
            return "break"

        if os.path.splitext(filepath)[1].lower() not in (".docx", ".pdf", ".txt"):
            messagebox.showwarning(
                "Unsupported File",
                "Only .docx, .pdf, and .txt files are supported.",
            )
            return "break"

        self._set_requirements_filepath(filepath)
        return "copy"

    def on_generate_tc(self):
        if not self.parsed_text:
            messagebox.showwarning("Generate TC", "Please select a requirements file first.")
            return

        selected_label = self.driver_type_menu.get()
        self.selected_driver_type = DRIVER_TYPE_OPTIONS.get(selected_label, "rc_car")
        port = self.port_menu.get()
        self.selected_port = port if port and port != NO_PORT_LABEL else None
        browser_label = self.browser_type_menu.get()
        self.selected_browser = browser_label.lower() if browser_label else "chrome"
        self.base_url = self.url_entry.get().strip()

        if self.selected_driver_type == "rc_car" and not self.selected_port:
            messagebox.showwarning("Serial Port", "Please select a serial port.")
            return

        if self.selected_driver_type == "web_app" and not self.base_url:
            messagebox.showwarning("Base URL", "Please enter a base URL.")
            return

        if self.selected_driver_type == "rc_car" and self.selected_port:
            self.log(f"[Port] Selected: {port}")
        elif self.selected_driver_type == "web_app":
            self.log(f"[Browser] Selected: {browser_label}, URL: {self.base_url}")
        else:
            self.log(f"[Driver] Selected: {selected_label}")

        self.last_run_context = {
            "parsed_text": self.parsed_text,
            "port": self.selected_port,
            "driver_type": self.selected_driver_type,
            "driver_label": selected_label,
            "browser": self.selected_browser,
            "base_url": self.base_url,
        }
        self.log("[Run] Starting generate_test_file()...")
        self.btn_generate.configure(state="disabled")
        self.btn_retry_results.configure(state="disabled")
        threading.Thread(
            target=self._run_generate_tc,
            args=(self.selected_port, self.selected_driver_type, self.selected_browser, self.base_url),
            daemon=True,
        ).start()

    def retry_last_test_run(self):
        if not self.last_run_context:
            return

        self.log("[Retry] Re-running last test sequence...")
        self.btn_generate.configure(state="disabled")
        self.btn_retry_results.configure(state="disabled")
        threading.Thread(
            target=self._run_generate_tc,
            args=(
                self.last_run_context.get("port"),
                self.last_run_context.get("driver_type", "rc_car"),
                self.last_run_context.get("browser", "chrome"),
                self.last_run_context.get("base_url", ""),
            ),
            daemon=True,
        ).start()

    def _run_generate_tc(self, port, driver_type, browser, base_url):
        captured_output = io.StringIO()
        pytest_output = []
        result_meta = {"report_generated": False}
        run_failed = False
        original_run = subprocess.run

        def patched_run(*args, **kwargs):
            kwargs.setdefault("capture_output", True)
            kwargs.setdefault("text", True)
            result = original_run(*args, **kwargs)
            if result.stdout:
                pytest_output.append(result.stdout)
            if result.stderr:
                pytest_output.append(result.stderr)
            return result

        subprocess.run = patched_run
        try:
            with redirect_stdout(captured_output), redirect_stderr(captured_output):
                result_meta = generate_test_file(
                    self.parsed_text,
                    port=port or "COM3",
                    driver_type=driver_type,
                    browser=browser or "chrome",
                    base_url=base_url or "",
                ) or {"report_generated": False}
        except Exception as exc:
            run_failed = True
            self.root.after(0, lambda: self.log(f"[Error] generate_test_file() — {exc}"))
            self.root.after(
                0,
                lambda: messagebox.showerror("TC Generation Error", str(exc)),
            )
            self.root.after(0, lambda: self.btn_generate.configure(state="normal"))
            self.root.after(0, lambda: self.btn_retry_results.configure(state="normal"))
            return
        finally:
            subprocess.run = original_run

        def finish():
            for line in captured_output.getvalue().splitlines():
                if line.strip():
                    self.log(line)
            for block in pytest_output:
                for line in block.splitlines():
                    if line.strip():
                        self.log(line)
            self.log("[Done] generate_test_file()")
            self.btn_generate.configure(state="normal")
            self.btn_retry_results.configure(state="disabled")

            if result_meta.get("report_generated"):
                try:
                    result_data = self._load_result_data()
                    self._populate_result_page(result_data)
                    if result_data.get("failed", 0) > 0:
                        self.btn_retry_results.configure(state="normal")
                    self.show_result_page()
                except Exception as exc:
                    self.log(f"[Error] result view load failed — {exc}")
                    self.btn_retry_results.configure(state="normal")
                    messagebox.showerror("Result View Error", str(exc))
            elif run_failed:
                self.btn_retry_results.configure(state="normal")

        self.root.after(0, finish)

    def _load_json_file(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _extract_timestamp(self, text):
        match = re.search(r"test_case_(\d{8}_\d{6})\.py", text or "")
        return match.group(1) if match else None

    def _extract_index_from_nodeid(self, nodeid):
        match = re.search(r"expected(\d+)\]", nodeid or "")
        return int(match.group(1)) if match else None

    def _extract_cmd_from_nodeid(self, nodeid):
        match = re.search(r"\[([^\]-]+)-expected\d+\]", nodeid or "")
        return match.group(1) if match else "-"

    def _normalize_technique(self, value):
        mapping = {
            "상태전이": "상태전이",
            "state_transition": "상태전이",
            "state transition": "상태전이",
            "경계값": "경계값",
            "boundary": "경계값",
            "boundary_value": "경계값",
            "boundary value": "경계값",
            "동등분할": "동등분할",
            "equivalence": "동등분할",
            "equivalence_partition": "동등분할",
            "equivalence partition": "동등분할",
            "무효전이": "무효전이",
            "invalid_transition": "무효전이",
            "invalid transition": "무효전이",
        }
        if not value:
            return "-"
        key = str(value).strip().lower()
        return mapping.get(key, value)

    def _flatten_error_message(self, value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            for key in ("message", "longrepr", "reprcrash", "crash"):
                if key in value:
                    text = self._flatten_error_message(value[key])
                    if text:
                        return text
            for nested in value.values():
                text = self._flatten_error_message(nested)
                if text:
                    return text
            return ""
        if isinstance(value, list):
            for item in value:
                text = self._flatten_error_message(item)
                if text:
                    return text
            return ""
        return str(value)

    def _format_detail_text(self, value):
        if value is None or value == "":
            return "-"
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        text = str(value)
        lines = []
        for line in text.splitlines() or [text]:
            if len(line) > 90:
                lines.append(textwrap.fill(line, width=90, break_long_words=False, break_on_hyphens=False))
            else:
                lines.append(line)
        return "\n".join(lines)

    def _show_detail_popup(self, title, value):
        popup = tk.Toplevel(self.root)
        popup.title(title)
        content_text = self._format_detail_text(value)
        if title == "명령어":
            popup.geometry("440x260")
        elif title == "에러 메시지" and len(content_text) > 240:
            popup.geometry("840x560")
        elif len(content_text) < 180:
            popup.geometry("520x320")
        else:
            popup.geometry("760x500")
        popup.configure(bg=COLORS["bg"])
        try:
            popup.iconbitmap(ICON_ICO_PATH)
            popup.wm_iconbitmap(ICON_ICO_PATH)
        except Exception:
            pass
        popup.transient(self.root)
        popup.grab_set()
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_rowconfigure(1, weight=1)
        popup.after(50, lambda: popup.wm_iconbitmap(ICON_ICO_PATH))
        popup.after(150, lambda: set_taskbar_icon(popup.winfo_id(), ICON_ICO_PATH))

        header = ctk.CTkFrame(
            popup,
            fg_color=COLORS["panel"],
            corner_radius=4,
            border_width=1,
            border_color=COLORS["accent_red"],
        )
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text=title,
            font=self.font_body_bold,
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=(16, 8), pady=14)

        ctk.CTkFrame(
            header,
            fg_color=COLORS["accent_red"],
            width=42,
            height=2,
            corner_radius=0,
        ).grid(row=0, column=1, sticky="w", padx=(0, 16), pady=(2, 0))

        body = ctk.CTkTextbox(
            popup,
            corner_radius=4,
            fg_color="#0b0b0b",
            border_width=1,
            border_color=COLORS["border_soft"],
            text_color=COLORS["text"],
            font=self.font_body,
            wrap="word",
        )
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 10))
        body.insert("1.0", content_text)
        body.configure(state="disabled")

        close_button = ctk.CTkButton(
            popup,
            text="닫기",
            command=popup.destroy,
            height=36,
            width=120,
            corner_radius=5,
            font=self.font_body_bold,
            fg_color=COLORS["panel"],
            hover_color="#202020",
            border_width=1,
            border_color=COLORS["accent_red"],
            text_color=COLORS["text"],
        )
        close_button.grid(row=2, column=0, sticky="e", padx=16, pady=(0, 16))

    def _extract_error_message(self, test):
        for key in ("call", "setup", "teardown", "longrepr"):
            if key in test:
                text = self._flatten_error_message(test[key])
                if text:
                    return text
        return ""

    def _resolve_report_timestamp(self, report_data):
        for test in report_data.get("tests", []):
            timestamp = self._extract_timestamp(test.get("nodeid", ""))
            if timestamp:
                return timestamp
        for collector in report_data.get("collectors", []):
            timestamp = self._extract_timestamp(collector.get("nodeid", ""))
            if timestamp:
                return timestamp
            for result in collector.get("result", []):
                timestamp = self._extract_timestamp(result.get("nodeid", ""))
                if timestamp:
                    return timestamp
        return None

    def _find_technique_path(self, timestamp):
        exact_path = os.path.join(BASE_DIR, f"technique_{timestamp}.json")
        if timestamp and os.path.exists(exact_path):
            return exact_path

        candidates = glob.glob(os.path.join(BASE_DIR, "technique_*.json"))
        if not candidates:
            raise FileNotFoundError("technique_*.json 파일을 찾을 수 없습니다.")
        return max(candidates, key=os.path.getmtime)

    def _load_result_data(self):
        report_path = os.path.join(BASE_DIR, ".report.json")
        if not os.path.exists(report_path):
            raise FileNotFoundError(".report.json 파일을 찾을 수 없습니다.")

        report_data = self._load_json_file(report_path)
        timestamp = self._resolve_report_timestamp(report_data)
        technique_path = self._find_technique_path(timestamp)
        technique_data = self._load_json_file(technique_path)

        if isinstance(technique_data, dict):
            technique_items = technique_data.get("items", [])
        elif isinstance(technique_data, list):
            technique_items = technique_data
        else:
            technique_items = []
        technique_map = {}
        for position, item in enumerate(technique_items):
            index = item.get("index", position)
            technique_map[index] = {
                "cmd": item.get("cmd", ""),
                "technique": self._normalize_technique(item.get("technique")),
            }

        rows = []
        passed = 0
        failed = 0

        for position, test in enumerate(report_data.get("tests", [])):
            report_index = self._extract_index_from_nodeid(test.get("nodeid", ""))
            index = report_index if report_index is not None else position
            technique_item = technique_map.get(index, {})
            outcome = "PASS" if test.get("outcome") == "passed" else "FAIL"
            if outcome == "PASS":
                passed += 1
            else:
                failed += 1

            rows.append(
                {
                    "cmd": technique_item.get("cmd") or self._extract_cmd_from_nodeid(test.get("nodeid", "")),
                    "technique": technique_item.get("technique") or "-",
                    "result": outcome,
                    "error": "" if outcome == "PASS" else self._extract_error_message(test),
                }
            )

        return {
            "total": len(rows),
            "passed": passed,
            "failed": failed,
            "rows": rows,
        }

    def _populate_result_page(self, result_data):
        self.total_count_label.configure(text=str(result_data["total"]))
        self.pass_count_label.configure(text=str(result_data["passed"]))
        self.fail_count_label.configure(text=str(result_data["failed"]))
        self._render_pie_chart(result_data["passed"], result_data["failed"])
        self._render_result_rows(result_data["rows"])

    def _render_pie_chart(self, passed, failed):
        if self.chart_canvas is not None:
            self.chart_canvas.get_tk_widget().destroy()
            self.chart_canvas = None

        total = passed + failed
        figure = Figure(figsize=(3.2, 3.0), dpi=100, facecolor=COLORS["bg"])
        ax = figure.add_subplot(111)
        ax.set_facecolor(COLORS["bg"])

        if total == 0:
            values = [1]
            labels = ["NO DATA"]
            colors = [COLORS["border"]]
            autopct = None
        else:
            values = [passed, failed]
            labels = ["PASS", "FAIL"]
            colors = [COLORS["success"], COLORS["accent_red"]]
            autopct = lambda pct: f"{pct:.0f}%"

        pie_result = ax.pie(
            values,
            labels=labels,
            colors=colors,
            startangle=90,
            counterclock=False,
            autopct=autopct,
            wedgeprops={"edgecolor": COLORS["bg"], "linewidth": 2},
            textprops={"color": COLORS["text"], "fontsize": 11},
        )

        def _flatten_artists(items):
            flattened = []
            for item in items:
                if hasattr(item, "set_color"):
                    flattened.append(item)
                elif isinstance(item, (list, tuple)):
                    flattened.extend(_flatten_artists(item))
            return flattened

        if hasattr(pie_result, "texts"):
            texts = _flatten_artists(list(getattr(pie_result, "texts", [])))
            autotexts = _flatten_artists(list(getattr(pie_result, "autotexts", [])))
        elif isinstance(pie_result, tuple) and len(pie_result) == 3:
            _, texts, autotexts = pie_result
            texts = _flatten_artists(texts)
            autotexts = _flatten_artists(autotexts)
        else:
            _, texts = pie_result
            texts = _flatten_artists(texts)
            autotexts = []
        for text in texts:
            text.set_color(COLORS["text"])
        for autotext in autotexts:
            autotext.set_color(COLORS["text"])
            autotext.set_fontsize(11)

        ax.axis("equal")
        figure.tight_layout()

        self.chart_canvas = FigureCanvasTkAgg(figure, master=self.chart_body)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)

    def _render_result_rows(self, rows):
        for child in self.table_scroll.winfo_children():
            child.destroy()

        header_row = ctk.CTkFrame(
            self.table_scroll,
            fg_color=COLORS["bg"],
            corner_radius=4,
            border_width=1,
            border_color=COLORS["border_soft"],
        )
        header_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._configure_detail_columns(header_row)

        for column, text in enumerate(["테스트 기법", "결과", "명령어", "에러"]):
            ctk.CTkLabel(
                header_row,
                text=text,
                font=self.font_table_header,
                text_color=COLORS["text"],
                anchor="center",
            ).grid(row=0, column=column, sticky="nsew", padx=10, pady=10)

        for row_index, row_data in enumerate(rows, start=1):
            row = ctk.CTkFrame(
                self.table_scroll,
                fg_color=COLORS["panel"] if row_index % 2 == 0 else COLORS["input"],
                corner_radius=4,
                border_width=1,
                border_color=COLORS["border_soft"],
            )
            row.grid(row=row_index, column=0, sticky="ew", pady=(0, 8))
            self._configure_detail_columns(row)

            ctk.CTkLabel(
                row,
                text=row_data["technique"],
                font=self.font_table,
                text_color=COLORS["text"],
                anchor="center",
            ).grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

            ctk.CTkLabel(
                row,
                text=row_data["result"],
                font=self.font_result,
                text_color=COLORS["success"] if row_data["result"] == "PASS" else COLORS["accent_red"],
                width=72,
                anchor="center",
            ).grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

            ctk.CTkButton(
                row,
                text="보기",
                command=lambda value=row_data["cmd"]: self._show_detail_popup("명령어", value),
                height=28,
                width=96,
                corner_radius=4,
                font=self.font_small_button,
                fg_color=COLORS["panel"],
                hover_color="#202020",
                border_width=1,
                border_color=COLORS["border"],
                text_color=COLORS["text"],
            ).grid(row=0, column=2, padx=10, pady=8)

            if row_data["error"]:
                ctk.CTkButton(
                    row,
                    text="보기",
                    command=lambda value=row_data["error"]: self._show_detail_popup("에러 메시지", value),
                    height=28,
                    width=96,
                    corner_radius=4,
                    font=self.font_small_button,
                    fg_color=COLORS["panel"],
                    hover_color="#202020",
                    border_width=1,
                    border_color=COLORS["accent_red"],
                    text_color=COLORS["text"],
                ).grid(row=0, column=3, padx=10, pady=8)
            else:
                ctk.CTkLabel(
                    row,
                    text="-",
                    font=self.font_table,
                    text_color=COLORS["text_muted"],
                    width=96,
                    anchor="center",
                ).grid(row=0, column=3, sticky="nsew", padx=10, pady=10)


def main():
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GUNSHOT.App")
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    try:
        tkdnd.TkinterDnD.require(root)
    except Exception:
        pass

    root.iconbitmap(ICON_ICO_PATH)
    Stage5GUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
