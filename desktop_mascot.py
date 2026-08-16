import os
import sys
import json
import asyncio
import threading
import math
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import urllib.request
import urllib.parse

from agent.orchestrator import MasterOrchestrator
from tools.screen_perception import ScreenPerceptionEngine
from tools import file_tools

# ==============================================================================
# CustomTkinter Global Configuration
# ==============================================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ==============================================================================
# Design Token System — IBM Carbon-Inspired
# ==============================================================================
C = {
    # Surfaces (layers get lighter as they elevate)
    "base":        "#111111",
    "layer_0":     "#161616",
    "layer_1":     "#1c1c1c",
    "layer_2":     "#252525",
    "layer_3":     "#303030",
    "field":       "#1a1a1a",
    "hover":       "#3a3a3a",
    "active":      "#4a4a4a",

    # Borders
    "border":      "#333333",
    "border_l":    "#444444",
    "focus":       "#0f62fe",

    # Blue spectrum
    "blue":        "#0f62fe",
    "blue_h":      "#0353e9",
    "blue_l":      "#4589ff",
    "blue_xl":     "#a6c8ff",
    "blue_bg":     "#0f62fe15",

    # Text
    "t1":          "#f4f4f4",
    "t2":          "#c6c6c6",
    "t3":          "#8d8d8d",
    "t4":          "#6f6f6f",
    "tw":          "#ffffff",

    # Status
    "green":       "#42be65",
    "green_d":     "#24a148",
    "yellow":      "#f1c21b",
    "red":         "#fa4d56",
    "purple":      "#be95ff",
    "teal":        "#08bdba",
    "cyan":        "#33b1ff",
}

# Typography
F_BRAND     = ("Segoe UI", 18, "bold")
F_H1        = ("Segoe UI", 14, "bold")
F_H2        = ("Segoe UI", 12, "bold")
F_H3        = ("Segoe UI", 11, "bold")
F_BODY      = ("Segoe UI", 11)
F_BODY_S    = ("Segoe UI", 10)
F_CAP       = ("Segoe UI", 9)
F_CAP_B     = ("Segoe UI", 9, "bold")
F_TINY      = ("Segoe UI", 8)
F_TINY_B    = ("Segoe UI", 8, "bold")
F_MONO      = ("Consolas", 11)
F_MONO_S    = ("Consolas", 10)
F_BTN       = ("Segoe UI", 11, "bold")
F_BTN_S     = ("Segoe UI", 10, "bold")

# Spacing
S1 = 4; S2 = 8; S3 = 12; S4 = 16; S5 = 20; S6 = 24; S7 = 32; S8 = 40; S9 = 48

# Radius
R_S = 6; R_M = 8; R_L = 12; R_XL = 16; R_PILL = 50

# ==============================================================================
# Mascot Theme Definitions
# ==============================================================================
MASCOT_THEMES = {
    "blue_bot": {
        "name": "Classic Blue Neo Bot",
        "desc": "Original Electric Blue Cloud Robot Mascot",
        "idle": "blue_bot_idle.png",
        "coding": "blue_bot_coding.png"
    },
    "doc_bot": {
        "name": "Doc Bot (Architecture & Specs)",
        "desc": "Cloud Mascot with Scroll & Checkmark Visor",
        "idle": "doc_bot_idle.png",
        "coding": "doc_bot_coding.png"
    },
    "data_bot": {
        "name": "Data Bot (Analytics & Experience)",
        "desc": "Cloud Mascot with Terminal Visor & Chart Badge",
        "idle": "data_bot_idle.png",
        "coding": "data_bot_coding.png"
    },
    "code_bot": {
        "name": "Code Bot (Implementation Specialist)",
        "desc": "Cyber Matrix Bot with Binary Screen & Code Badge",
        "idle": "code_bot_idle.png",
        "coding": "code_bot_coding.png"
    },
    "artist_bot": {
        "name": "Artist Bot (Styling & CSS Designer)",
        "desc": "Creative Canvas Bot with Paint Palette",
        "idle": "artist_bot_idle.png",
        "coding": "artist_bot_coding.png"
    },
    "server_bot": {
        "name": "Server Bot (QA & Systems Engineer)",
        "desc": "Retro Server Rack Bot with Matrix Face",
        "idle": "server_bot_idle.png",
        "coding": "server_bot_coding.png"
    },
    "pixel_bot": {
        "name": "Neo Purple Bot",
        "desc": "Classic Pixel Robot",
        "idle": "pixel_bot_idle.png",
        "coding": "pixel_bot_coding.png"
    },
    "cyber_cat": {
        "name": "Cyber Neko Cat",
        "desc": "Futuristic Neon Cyan Cat",
        "idle": "cyber_cat_idle.png",
        "coding": "cyber_cat_coding.png"
    },
    "neon_dragon": {
        "name": "Neon Cyber Dragon",
        "desc": "Emerald Dragon with Glowing Horns",
        "idle": "neon_dragon_idle.png",
        "coding": "neon_dragon_coding.png"
    },
    "cosmic_orb": {
        "name": "Cosmic AI Orb",
        "desc": "Floating Crystal Orb",
        "idle": "cosmic_orb_idle.png",
        "coding": "cosmic_orb_coding.png"
    },
    "vector_bot": {
        "name": "Dynamic Vector Bot",
        "desc": "Hand-Drawn Vector Bot",
        "idle": "",
        "coding": ""
    }
}


class FloatingMascotApp:
    """Premium AI Agent Studio & Desktop Companion.
    
    Floating overlay uses raw tkinter (for transparency).
    Studio window uses CustomTkinter for a modern, premium look.
    """

    def __init__(self):
        # =====================================================================
        # Floating Mascot Overlay (raw tkinter — transparency requires this)
        # =====================================================================
        self.root = tk.Tk()
        self.root.title("Neo Agent Studio")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        self.trans_color = "#010101"
        self.root.config(bg=self.trans_color)
        self.root.wm_attributes("-transparentcolor", self.trans_color)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"190x210+{screen_w - 210}+{screen_h - 250}")

        self.start_x = 0
        self.start_y = 0
        self.tick = 0
        self.mascot_state = "idle"
        self.chat_window = None
        self.current_plan = None
        self.sub_agents_tracker = {}
        self.current_folder = os.path.abspath(file_tools.get_workspace_root())
        self.attached_file_path = None
        self.attached_file_name = ""
        self.attached_image_b64 = None

        self.agent = MasterOrchestrator()
        self.screen_engine = ScreenPerceptionEngine()

        self.canvas = tk.Canvas(self.root, width=190, height=210, bg=self.trans_color, highlightthickness=0)
        self.canvas.pack()

        self.active_theme_key = "blue_bot"
        self.preload_all_mascot_themes()
        self.load_mascot_theme(self.get_saved_theme())

        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Button-3>", self._show_ctx)
        self.canvas.bind("<Double-Button-1>", lambda e: self.open_chat_dialog())

        # OS-native context menu
        self.context_menu = tk.Menu(
            self.root, tearoff=0,
            bg=C["layer_2"], fg=C["t1"],
            activebackground=C["blue"], activeforeground="#ffffff",
            font=F_BODY_S
        )
        self.context_menu.add_command(label="  Open Studio", command=self.open_chat_dialog)
        self.context_menu.add_command(label="  Change Folder...", command=self.select_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="  Neo (Web/Games)", command=lambda: self.open_chat_dialog(default_agent="neo"))
        self.context_menu.add_command(label="  Claw (Next.js)", command=lambda: self.open_chat_dialog(default_agent="claw"))
        self.context_menu.add_command(label="  Eagle (Review)", command=lambda: self.open_chat_dialog(default_agent="eagle"))
        self.context_menu.add_command(label="  Herald (Slides)", command=lambda: self.open_chat_dialog(default_agent="herald"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="  Analyze Workspace", command=self.trigger_folder_analysis)
        self.context_menu.add_command(label="  Scan Screen", command=self.trigger_screen_analysis)
        self.context_menu.add_command(label="  Settings...", command=self.open_mascot_settings)
        self.context_menu.add_command(label="  Web Dashboard", command=self._open_web)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="  Quit", command=self.root.destroy)

        self._animate()

    # =========================================================================
    # Mascot Theme System
    # =========================================================================
    def preload_all_mascot_themes(self):
        self.mascot_cache = {}
        mascot_dir = os.path.join(os.path.dirname(__file__), "ui", "assets", "mascots")
        for key, theme in MASCOT_THEMES.items():
            if key == "vector_bot":
                self.mascot_cache[key] = {"idle": None, "coding": None}
                continue
            idle_p = os.path.join(mascot_dir, theme["idle"])
            coding_p = os.path.join(mascot_dir, theme["coding"])
            if not os.path.exists(idle_p):
                idle_p = os.path.join(os.path.dirname(__file__), "ui", "assets", "neo-mascot-idle.png")
            if not os.path.exists(coding_p):
                coding_p = os.path.join(os.path.dirname(__file__), "ui", "assets", "neo-mascot-coding.png")
            self.mascot_cache[key] = {
                "idle": tk.PhotoImage(file=idle_p),
                "coding": tk.PhotoImage(file=coding_p)
            }

    def get_saved_theme(self):
        try:
            cfg = os.path.join(os.path.dirname(__file__), ".data", "mascot_config.json")
            if os.path.exists(cfg):
                with open(cfg, "r", encoding="utf-8") as f:
                    return json.load(f).get("active_theme", "blue_bot")
        except Exception:
            pass
        return "blue_bot"

    def save_theme_config(self, key):
        try:
            d = os.path.join(os.path.dirname(__file__), ".data")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "mascot_config.json"), "w", encoding="utf-8") as f:
                json.dump({"active_theme": key}, f)
        except Exception:
            pass

    def load_mascot_theme(self, key="blue_bot"):
        if key not in MASCOT_THEMES:
            key = "blue_bot"
        self.active_theme_key = key
        if hasattr(self, "mascot_cache") and key in self.mascot_cache:
            self.mascot_images = self.mascot_cache[key]
        self.save_theme_config(key)
        self._draw()

    # =========================================================================
    # Mascot Canvas
    # =========================================================================
    def _on_click(self, e):
        self.start_x, self.start_y = e.x, e.y

    def _on_drag(self, e):
        x = self.root.winfo_x() + (e.x - self.start_x)
        y = self.root.winfo_y() + (e.y - self.start_y)
        self.root.geometry(f"+{x}+{y}")

    def _show_ctx(self, e):
        self.context_menu.tk_popup(e.x_root, e.y_root)

    def _draw(self):
        if not hasattr(self, "canvas") or not self.canvas:
            return
        self.canvas.delete("all")
        self.tick += 1
        bob = int(math.sin(self.tick * 0.12) * 5)
        cx, cy = 95, 85 + bob

        is_coding = self.mascot_state in {"planning", "thinking", "executing", "ast_check"}
        img = self.mascot_images.get("coding" if is_coding else "idle") if hasattr(self, "mascot_images") else None
        if img:
            self.canvas.create_image(cx, cy + 5, image=img)

        labels = {"idle": ("Neo Companion", C["blue_l"]),
                  "planning": ("Processing...", C["yellow"]),
                  "thinking": ("Processing...", C["yellow"]),
                  "executing": ("Writing Code...", C["purple"]),
                  "success": ("Task Complete", C["green"])}
        text, color = labels.get(self.mascot_state, ("Neo Companion", C["blue_l"]))
        self.canvas.create_text(cx, 185, text=text, fill=color, font=F_CAP_B)

    def _animate(self):
        self._draw()
        self.root.after(50, self._animate)

    # =========================================================================
    # Utility
    # =========================================================================
    def select_folder(self):
        chosen = filedialog.askdirectory(title="Select Workspace", initialdir=self.current_folder)
        if chosen:
            chosen = os.path.abspath(chosen)
            file_tools.set_workspace_root(chosen)
            self.current_folder = chosen
            messagebox.showinfo("Workspace Changed", f"Set to:\n{chosen}")
            if self.chat_window and self.chat_window.winfo_exists():
                if hasattr(self, "_ws_path_lbl"):
                    self._ws_path_lbl.configure(text=self._folder_display())
                if hasattr(self, "_refresh_ws"):
                    self._refresh_ws()

    def _folder_display(self):
        name = os.path.basename(self.current_folder) or self.current_folder
        return f"  {name}"

    def trigger_folder_analysis(self):
        self.mascot_state = "thinking"
        def w():
            async def t():
                r = await self.agent.analyze_and_autofix_folder(self.current_folder)
                self.root.after(0, lambda: self._show_result("Workspace Analysis", r))
            asyncio.run(t())
        threading.Thread(target=w, daemon=True).start()

    def trigger_screen_analysis(self):
        self.mascot_state = "thinking"
        def w():
            async def t():
                r = await self.agent.analyze_and_autofix_screen_and_folder(self.current_folder)
                self.root.after(0, lambda: self._show_result("Screen Diagnostics", r))
            asyncio.run(t())
        threading.Thread(target=w, daemon=True).start()

    def _show_result(self, title, result):
        self.mascot_state = "idle"
        s, m = result.get("status"), result.get("message", "")
        if s in ["fixed", "success"]:
            self.mascot_state = "success"
            messagebox.showinfo(title, f"Resolved:\n{m}\n\nFile: {result.get('target_file')}")
        else:
            messagebox.showinfo(title, m)

    def _open_web(self):
        import webbrowser
        webbrowser.open("http://127.0.0.1:8000")

    # =========================================================================
    # Settings Dialog
    # =========================================================================
    def open_mascot_settings(self):
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("Settings")
        dlg.geometry("460x520")
        dlg.attributes("-topmost", True)
        dlg.configure(fg_color=C["base"])
        dlg.after(100, dlg.lift)
        dlg.after(100, dlg.focus_force)

        # Header
        hdr = ctk.CTkFrame(dlg, fg_color=C["layer_1"], corner_radius=0, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="  Avatar Settings", font=F_H2, text_color=C["t1"]).pack(side="left", padx=S4)

        ctk.CTkLabel(dlg, text="Choose a mascot for your desktop companion.", font=F_CAP, text_color=C["t3"]).pack(anchor="w", padx=S6, pady=(S4, S2))

        # Scrollable list
        lst = ctk.CTkScrollableFrame(dlg, fg_color=C["layer_0"], corner_radius=R_L, border_width=1, border_color=C["border"])
        lst.pack(fill="both", expand=True, padx=S6, pady=(0, S3))

        var = tk.StringVar(value=self.active_theme_key)
        for key, theme in MASCOT_THEMES.items():
            row = ctk.CTkFrame(lst, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkRadioButton(
                row, text=f"  {theme['name']}", value=key, variable=var,
                font=F_BODY_S, text_color=C["t1"],
                fg_color=C["blue"], hover_color=C["blue_h"],
                border_color=C["border_l"],
                border_width_unchecked=2, border_width_checked=6
            ).pack(anchor="w", padx=S3, pady=S1)

        # Buttons
        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(fill="x", padx=S6, pady=S4)

        def apply():
            self.load_mascot_theme(var.get())
            dlg.destroy()

        ctk.CTkButton(btns, text="Cancel", font=F_BTN_S, fg_color="transparent", text_color=C["t2"],
                       hover_color=C["hover"], border_width=1, border_color=C["border_l"],
                       corner_radius=R_M, height=36, width=90, command=dlg.destroy).pack(side="right", padx=(S2, 0))
        ctk.CTkButton(btns, text="Apply", font=F_BTN_S, fg_color=C["blue"], hover_color=C["blue_h"],
                       text_color=C["tw"], corner_radius=R_M, height=36, width=90, command=apply).pack(side="right")

    # =========================================================================
    # MAIN STUDIO WINDOW
    # =========================================================================
    def open_chat_dialog(self, default_tab=0, default_agent="auto"):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.lift()
            return

        win = ctk.CTkToplevel(self.root)
        self.chat_window = win
        win.title("Neo Studio")
        win.geometry("960x920")
        win.minsize(760, 680)
        win.attributes("-topmost", True)
        win.configure(fg_color=C["base"])
        win.after(100, win.lift)
        win.after(100, win.focus_force)

        self.selected_agent = default_agent

        # =================================================================
        # HEADER — Unified brand + workspace + actions in one slim bar
        # =================================================================
        header = ctk.CTkFrame(win, fg_color=C["layer_0"], corner_radius=0, height=48)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Left: Brand
        ctk.CTkLabel(header, text=" neo", font=("Segoe UI", 17, "bold"), text_color=C["blue_l"]).pack(side="left", padx=(S4, 0))
        ctk.CTkLabel(header, text=".studio", font=("Segoe UI", 17), text_color=C["t3"]).pack(side="left")

        # Right: Actions
        ctk.CTkButton(header, text="Web UI", font=F_TINY_B, fg_color="transparent", text_color=C["blue_l"],
                       hover_color=C["hover"], corner_radius=R_S, width=60, height=28,
                       command=self._open_web).pack(side="right", padx=(0, S3))

        ctk.CTkButton(header, text="Settings", font=F_TINY_B, fg_color="transparent", text_color=C["t3"],
                       hover_color=C["hover"], corner_radius=R_S, width=60, height=28,
                       command=self.open_mascot_settings).pack(side="right", padx=(0, S1))

        # Workspace folder button (clickable, shows current folder name)
        self._ws_path_lbl = ctk.CTkButton(
            header, text=self._folder_display(), font=F_MONO_S,
            fg_color=C["layer_2"], text_color=C["t2"], hover_color=C["hover"],
            corner_radius=R_S, height=28, anchor="w",
            command=self.select_folder
        )
        self._ws_path_lbl.pack(side="right", padx=(0, S2))

        # Thin accent line below header
        ctk.CTkFrame(win, fg_color=C["blue"], height=2, corner_radius=0).pack(fill="x")

        # =================================================================
        # TABVIEW — Full-width, clean segmented tabs
        # =================================================================
        tabview = ctk.CTkTabview(
            win, fg_color=C["base"], corner_radius=0,
            segmented_button_fg_color=C["layer_0"],
            segmented_button_selected_color=C["blue"],
            segmented_button_selected_hover_color=C["blue_h"],
            segmented_button_unselected_color=C["layer_0"],
            segmented_button_unselected_hover_color=C["hover"],
            text_color=C["t1"]
        )
        tabview.pack(fill="both", expand=True, padx=0, pady=0)

        chat_tab = tabview.add("  Chat  ")
        plan_tab = tabview.add("  Plan  ")
        ws_tab   = tabview.add("  Files  ")
        art_tab  = tabview.add("  Artifacts  ")

        # =================================================================
        # TAB 1: CHAT — Complete redesign
        # =================================================================

        # ---- Top controls row: Agent + Chips in one line ----
        controls = ctk.CTkFrame(chat_tab, fg_color="transparent")
        controls.pack(fill="x", padx=S5, pady=(S3, 0))

        # Agent selector (compact, not full-width)
        agent_values = ["Auto", "Neo", "Claw", "Eagle", "Herald"]
        agent_map = {"Auto": "auto", "Neo": "neo", "Claw": "claw", "Eagle": "eagle", "Herald": "herald"}
        rev_map = {v: k for k, v in agent_map.items()}

        def on_agent(val):
            self.selected_agent = agent_map.get(val, "auto")

        agent_seg = ctk.CTkSegmentedButton(
            controls, values=agent_values, command=on_agent,
            font=F_CAP_B, corner_radius=R_M, height=32,
            selected_color=C["blue"], selected_hover_color=C["blue_h"],
            unselected_color=C["layer_2"], unselected_hover_color=C["hover"],
            text_color=C["tw"]
        )
        agent_seg.set(rev_map.get(default_agent, "Auto"))
        agent_seg.pack(side="left")

        # Screen scan button on the right
        ctk.CTkButton(
            controls, text="Scan Screen", font=F_CAP_B,
            fg_color=C["layer_2"], text_color=C["teal"], hover_color=C["hover"],
            border_width=1, border_color=C["border"], corner_radius=R_M, height=32, width=100,
            command=self.trigger_screen_analysis
        ).pack(side="right")

        # ---- Welcome area / Chat messages ----
        # We use a main frame that holds: welcome OR chat_box, then input bar at bottom
        chat_container = ctk.CTkFrame(chat_tab, fg_color="transparent")
        chat_container.pack(fill="both", expand=True, padx=S5, pady=(S3, 0))

        # Welcome / Quick Actions (shown initially in the chat area)
        welcome_frame = ctk.CTkFrame(chat_container, fg_color="transparent")
        welcome_frame.pack(fill="both", expand=True)

        # Welcome header
        w_header = ctk.CTkFrame(welcome_frame, fg_color="transparent")
        w_header.pack(pady=(S9, S4))
        ctk.CTkLabel(w_header, text="What can I help you build?", font=F_H1, text_color=C["t1"]).pack()
        ctk.CTkLabel(w_header, text="Choose a quick action or type your own prompt below.", font=F_BODY_S, text_color=C["t3"]).pack(pady=(S1, 0))

        # Action cards grid (2x2)
        cards_frame = ctk.CTkFrame(welcome_frame, fg_color="transparent")
        cards_frame.pack(fill="x", padx=S7)
        cards_frame.columnconfigure((0, 1), weight=1, uniform="card")

        def send_quick_prompt(prompt_text, force_agent=None):
            if force_agent:
                self.selected_agent = force_agent
                agent_seg.set(rev_map.get(force_agent, "Auto"))
            entry.delete(0, "end")
            entry.insert(0, prompt_text)
            send_msg()

        card_data = [
            ("Build Web Game", "Single-file retro Snake with\nscore tracking & sound effects", C["cyan"], "neo",
             "Build a single-file retro Snake arcade game with score tracking and sound effects"),
            ("Next.js Project", "Full-stack developer portfolio\nwith glassmorphism dark mode", C["purple"], "claw",
             "Build a complete Next.js developer portfolio with animated dark mode glassmorphism UI"),
            ("Code Review", "Analyze workspace, find bugs,\ngenerate DebugCard report", C["green"], "eagle",
             "Analyze code in my workspace, identify any bugs, and generate an educational DebugCard"),
            ("Slide Deck", "10-slide AI presentation\nwith speaker notes", C["yellow"], "herald",
             "Create a professional presentation about Artificial Intelligence with 10 slides and speaker notes"),
        ]

        for i, (title, desc, accent, ag, prompt) in enumerate(card_data):
            card = ctk.CTkFrame(
                cards_frame, fg_color=C["layer_1"], corner_radius=R_L,
                border_width=1, border_color=C["border"]
            )
            card.grid(row=i // 2, column=i % 2, padx=S2, pady=S2, sticky="nsew")

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=S5, pady=S4)

            # Accent dot + title
            title_row = ctk.CTkFrame(inner, fg_color="transparent")
            title_row.pack(fill="x")
            ctk.CTkFrame(title_row, fg_color=accent, width=8, height=8, corner_radius=4).pack(side="left", padx=(0, S2))
            ctk.CTkLabel(title_row, text=title, font=F_H3, text_color=C["t1"]).pack(side="left")

            ctk.CTkLabel(inner, text=desc, font=F_CAP, text_color=C["t3"], justify="left", anchor="w").pack(fill="x", pady=(S1, S3))

            ctk.CTkButton(
                inner, text="Start  \u2192", font=F_CAP_B,
                fg_color="transparent", text_color=accent, hover_color=C["hover"],
                border_width=1, border_color=C["border"], corner_radius=R_M,
                height=28, width=80, anchor="center",
                command=lambda p=prompt, a=ag: send_quick_prompt(p, a)
            ).pack(anchor="w")

        # Chat message textbox (initially hidden behind welcome, shown when first message sent)
        chat_box = ctk.CTkTextbox(
            chat_container, font=F_BODY, wrap="word",
            fg_color=C["layer_0"], text_color=C["t1"],
            border_width=1, border_color=C["border"],
            corner_radius=R_L
        )
        # NOT packed yet — will replace welcome_frame on first message

        # Tag colors
        chat_box.tag_config("user_hdr", foreground=C["blue_l"])
        chat_box.tag_config("user_body", foreground=C["t1"])
        chat_box.tag_config("neo_hdr", foreground=C["tw"])
        chat_box.tag_config("neo_body", foreground=C["t2"])
        chat_box.tag_config("system", foreground=C["t3"])
        chat_box.tag_config("routing", foreground=C["blue_l"])
        chat_box.tag_config("artifact", foreground=C["green"])
        chat_box.tag_config("plan", foreground=C["yellow"])
        chat_box.tag_config("subagent", foreground=C["cyan"])

        chat_visible = {"shown": False}

        def show_chat():
            if not chat_visible["shown"]:
                welcome_frame.pack_forget()
                chat_box.pack(fill="both", expand=True)
                chat_box.insert("end", "Session started.\n\n", "system")
                chat_visible["shown"] = True

        # ---- Attachment row ----
        attach_bar = ctk.CTkFrame(chat_tab, fg_color="transparent", height=20)
        attach_bar.pack(fill="x", padx=S5)

        attach_lbl = ctk.CTkLabel(attach_bar, text="", font=F_TINY_B, text_color=C["blue_l"])
        attach_lbl.pack(side="left")

        def pick_file():
            fp = filedialog.askopenfilename(
                title="Attach File",
                filetypes=[("Supported", "*.png;*.jpg;*.jpeg;*.webp;*.pdf;*.pptx;*.xlsx;*.csv;*.py;*.js;*.html;*.json"), ("All", "*.*")]
            )
            if fp:
                self.attached_file_path = fp
                self.attached_file_name = os.path.basename(fp)
                ext = os.path.splitext(fp)[1].lower()
                if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]:
                    import base64
                    with open(fp, "rb") as f:
                        self.attached_image_b64 = base64.b64encode(f.read()).decode("utf-8")
                    attach_lbl.configure(text=f"  Image: {self.attached_file_name}")
                else:
                    self.attached_image_b64 = None
                    attach_lbl.configure(text=f"  File: {self.attached_file_name}")

        def clear_attach():
            self.attached_file_path = None
            self.attached_file_name = ""
            self.attached_image_b64 = None
            attach_lbl.configure(text="")

        # ---- INPUT BAR — prominent, bottom-anchored ----
        input_outer = ctk.CTkFrame(
            chat_tab, fg_color=C["layer_1"], corner_radius=R_L,
            border_width=1, border_color=C["border"]
        )
        input_outer.pack(fill="x", padx=S5, pady=(S2, S4))

        input_row = ctk.CTkFrame(input_outer, fg_color="transparent")
        input_row.pack(fill="x", padx=S3, pady=S3)

        ctk.CTkButton(
            input_row, text="+", font=("Segoe UI", 16), width=36, height=36,
            fg_color="transparent", text_color=C["t3"], hover_color=C["hover"],
            corner_radius=R_M, command=pick_file
        ).pack(side="left", padx=(0, S2))

        entry = ctk.CTkEntry(
            input_row, font=F_BODY, height=40,
            fg_color=C["field"], text_color=C["t1"],
            placeholder_text="Ask Neo anything...",
            placeholder_text_color=C["t4"],
            border_width=0, corner_radius=R_M
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, S2))

        # =================================================================
        # TAB 2: Execution Plan
        # =================================================================
        plan_hdr = ctk.CTkFrame(plan_tab, fg_color="transparent")
        plan_hdr.pack(fill="x", padx=S5, pady=(S4, S2))
        ctk.CTkLabel(plan_hdr, text="Execution Plan", font=F_H2, text_color=C["t1"]).pack(side="left")

        plan_txt = ctk.CTkTextbox(
            plan_tab, font=F_MONO, wrap="word",
            fg_color=C["layer_0"], text_color=C["t2"],
            border_width=1, border_color=C["border"], corner_radius=R_L
        )
        plan_txt.pack(fill="both", expand=True, padx=S5, pady=(0, S5))

        def refresh_plan():
            plan_txt.configure(state="normal")
            plan_txt.delete("1.0", "end")
            if not self.current_plan:
                plan_txt.insert("end", "  No active plan.\n\n  Submit a prompt to generate an execution plan.\n")
            else:
                p = self.current_plan
                plan_txt.insert("end", f"  PLAN: {p.get('title')}\n")
                plan_txt.insert("end", f"  {p.get('summary')}\n")
                plan_txt.insert("end", f"  Progress: {p.get('progress', 0)}%\n\n")
                for st in p.get("steps", []):
                    s = st.get("status")
                    icon = "  \u2713" if s == "completed" else ("  \u25cf" if s == "in_progress" else "  \u25cb")
                    plan_txt.insert("end", f"{icon}  Step {st.get('step_id')}: {st.get('title')}\n")
                    plan_txt.insert("end", f"      {st.get('assigned_role')}  |  {st.get('target_file')}\n")
                    plan_txt.insert("end", f"      {st.get('description')}\n\n")
            if self.sub_agents_tracker:
                plan_txt.insert("end", "\n  ACTIVE SUB-AGENTS\n")
                for sa in self.sub_agents_tracker.values():
                    plan_txt.insert("end", f"    {sa.get('name')} ({sa.get('role')}): {sa.get('status','').upper()} {sa.get('progress',0)}%\n")

        # =================================================================
        # TAB 3: Workspace Explorer
        # =================================================================
        ws_toolbar = ctk.CTkFrame(ws_tab, fg_color="transparent")
        ws_toolbar.pack(fill="x", padx=S5, pady=(S4, S2))

        ws_title = ctk.CTkLabel(ws_toolbar, text="Workspace Files", font=F_H2, text_color=C["t1"])
        ws_title.pack(side="left")

        ctk.CTkButton(ws_toolbar, text="Change Folder", font=F_CAP_B, fg_color=C["blue"], hover_color=C["blue_h"],
                       text_color=C["tw"], corner_radius=R_M, height=30, width=110, command=self.select_folder).pack(side="right")
        ctk.CTkButton(ws_toolbar, text="Refresh", font=F_CAP_B, fg_color="transparent", text_color=C["t2"],
                       hover_color=C["hover"], border_width=1, border_color=C["border"],
                       corner_radius=R_M, height=30, width=70, command=lambda: refresh_ws()).pack(side="right", padx=(0, S2))

        ws_txt = ctk.CTkTextbox(ws_tab, font=F_MONO, wrap="word", fg_color=C["layer_0"], text_color=C["t1"],
                                 border_width=1, border_color=C["border"], corner_radius=R_L)
        ws_txt.pack(fill="both", expand=True, padx=S5, pady=(0, S5))

        def open_file_viewer(filename):
            res = file_tools.read_file(filename)
            if res.get("status") != "success":
                messagebox.showerror("Error", f"Cannot read '{filename}': {res.get('message')}")
                return
            vdlg = ctk.CTkToplevel(win)
            vdlg.title(f"Viewer \u2014 {filename}")
            vdlg.geometry("800x640")
            vdlg.attributes("-topmost", True)
            vdlg.configure(fg_color=C["base"])
            vdlg.after(100, vdlg.lift)

            vhdr = ctk.CTkFrame(vdlg, fg_color=C["layer_1"], corner_radius=0, height=44)
            vhdr.pack(fill="x")
            vhdr.pack_propagate(False)
            ctk.CTkLabel(vhdr, text=f"  {filename}  ({res.get('lines',0)} lines)", font=F_MONO_S, text_color=C["t1"]).pack(side="left", padx=S4)
            ctk.CTkButton(vhdr, text="Close", font=F_CAP_B, fg_color=C["layer_2"], text_color=C["t2"],
                           hover_color=C["hover"], corner_radius=R_S, height=28, width=60, command=vdlg.destroy).pack(side="right", padx=S3)

            vtxt = ctk.CTkTextbox(vdlg, font=F_MONO, fg_color=C["field"], text_color=C["t1"],
                                   border_width=1, border_color=C["border"], corner_radius=R_L, wrap="none")
            vtxt.pack(fill="both", expand=True, padx=S4, pady=S4)
            vtxt.insert("end", res.get("content", ""))

        def refresh_ws():
            ws_txt.configure(state="normal")
            ws_txt.delete("1.0", "end")
            root_path = os.path.abspath(file_tools.get_workspace_root())
            files = file_tools.list_directory(root_path)
            count = files.get('count', 0)
            ws_title.configure(text=f"Workspace  \u00b7  {os.path.basename(root_path)}  ({count} items)")
            ws_txt.insert("end", f"  {root_path}\n  Double-click to open in viewer\n\n")
            for item in files.get("items", []):
                t = item["type"]
                n = item["name"]
                if t == "directory":
                    tag = "[DIR]  "
                elif n.endswith((".py", ".pyw")):
                    tag = "[PY]   "
                elif n.endswith((".html", ".htm")):
                    tag = "[HTML]  "
                elif n.endswith((".pptx",)):
                    tag = "[PPTX]  "
                elif n.endswith((".js", ".jsx", ".ts", ".tsx")):
                    tag = "[JS]   "
                else:
                    tag = "[FILE] "
                ws_txt.insert("end", f"  {tag}{n}\n")

        self._refresh_ws = refresh_ws

        def on_ws_click(event):
            try:
                idx = ws_txt._textbox.index(f"@{event.x},{event.y}")
                line = ws_txt._textbox.get(f"{idx} linestart", f"{idx} lineend").strip()
                if line:
                    for p in ["[DIR]", "[PY]", "[HTML]", "[PPTX]", "[JS]", "[FILE]"]:
                        line = line.replace(p, "").strip()
                    if line and not line.startswith(("d:", "D:", "C:", "/")):
                        open_file_viewer(line)
            except Exception:
                pass
        ws_txt.bind("<Double-Button-1>", on_ws_click)

        # =================================================================
        # TAB 4: Artifacts
        # =================================================================
        art_toolbar = ctk.CTkFrame(art_tab, fg_color="transparent")
        art_toolbar.pack(fill="x", padx=S5, pady=(S4, S2))
        ctk.CTkLabel(art_toolbar, text="Generated Artifacts", font=F_H2, text_color=C["t1"]).pack(side="left")

        def open_pres_dir():
            d = os.path.join(os.path.dirname(__file__), "data", "presentations")
            os.makedirs(d, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(d)

        ctk.CTkButton(art_toolbar, text="Open Folder", font=F_CAP_B, fg_color="transparent", text_color=C["t2"],
                       hover_color=C["hover"], border_width=1, border_color=C["border"],
                       corner_radius=R_M, height=30, width=100, command=open_pres_dir).pack(side="right")

        art_txt = ctk.CTkTextbox(art_tab, font=F_BODY_S, wrap="word", fg_color=C["layer_0"], text_color=C["t1"],
                                  border_width=1, border_color=C["border"], corner_radius=R_L)
        art_txt.pack(fill="both", expand=True, padx=S5, pady=(0, S5))

        def refresh_art():
            art_txt.configure(state="normal")
            art_txt.delete("1.0", "end")
            d = os.path.join(os.path.dirname(__file__), "data", "presentations")
            os.makedirs(d, exist_ok=True)
            files = [f for f in os.listdir(d) if f.endswith((".html", ".pptx"))]
            art_txt.insert("end", f"  Location: {d}\n\n")
            if not files:
                art_txt.insert("end", "  No artifacts yet.\n  Use a quick action or ask Herald to generate slide decks.\n")
            else:
                for f in files:
                    ext = "[PPTX]" if f.endswith(".pptx") else "[HTML]"
                    art_txt.insert("end", f"    {ext}  {f}\n")

        # Tab change handler
        def on_tab(_=None):
            try:
                t = tabview.get()
                if "Files" in t: refresh_ws()
                elif "Plan" in t: refresh_plan()
                elif "Artifact" in t: refresh_art()
            except Exception:
                pass
        tabview.configure(command=on_tab)

        # Initial data load
        refresh_ws()
        refresh_plan()
        refresh_art()

        if default_tab > 0:
            tabs = ["  Chat  ", "  Plan  ", "  Files  ", "  Artifacts  "]
            if default_tab < len(tabs):
                tabview.set(tabs[default_tab])

        # =================================================================
        # SEND MESSAGE LOGIC
        # =================================================================
        def send_msg():
            raw = entry.get().strip()
            if not raw and not self.attached_image_b64 and not self.attached_file_path:
                return

            show_chat()

            msg = raw
            if self.selected_agent and self.selected_agent != "auto":
                if not msg.lower().startswith(f"@{self.selected_agent}") and not msg.lower().startswith(f"[agent:{self.selected_agent}]"):
                    msg = f"[AGENT:{self.selected_agent.upper()}] {msg}"

            b64 = self.attached_image_b64
            att = f"  [{self.attached_file_name}]" if self.attached_file_name else ""
            entry.delete(0, "end")

            chat_box.insert("end", "You   ", "user_hdr")
            chat_box.insert("end", f"{raw}{att}\n\n", "user_body")
            chat_box.insert("end", "Neo   ", "neo_hdr")
            chat_box.see("end")

            clear_attach()
            self.mascot_state = "thinking"

            def worker():
                async def stream():
                    imgs = [b64] if b64 else None
                    prompt = msg or "Inspect attachment and assist with task."
                    async for ev in self.agent.stream_response(prompt, images=imgs, target_folder=self.current_folder):
                        et = ev.get("type")

                        if et == "state":
                            self.root.after(0, setattr, self, 'mascot_state', ev.get("mascot_state", "thinking"))

                        elif et == "folder_selection_required":
                            self.agent.resolve_folder_selection(ev.get("id"), self.current_folder)

                        elif et == "framework_selection_required":
                            rid = ev.get("id")
                            def ask(r=rid):
                                ans = messagebox.askyesno("Framework", "YES = Next.js (Claw)\nNO = HTML5 (Neo)", parent=win)
                                self.agent.resolve_framework_selection(r, "nextjs" if ans else "html")
                            self.root.after(0, ask)

                        elif et == "permission_request":
                            self.agent.resolve_permission(ev.get("id"), True)

                        elif et == "plan_generated":
                            pd = ev.get("plan")
                            self.current_plan = pd
                            def show_p(p=pd):
                                chat_box.insert("end", f"\n[PLAN] {p.get('title')}\n", "plan")
                                chat_box.see("end")
                                refresh_plan()
                            self.root.after(0, show_p)

                        elif et == "token":
                            tok = ev.get("content", "")
                            def add(t=tok):
                                chat_box.insert("end", t, "neo_body")
                                chat_box.see("end")
                            self.root.after(0, add)

                        elif et == "routing":
                            tgt = ev.get("target_agent", "neo").upper()
                            rsn = ev.get("reasoning", "")
                            def show_r(t=tgt, r=rsn):
                                chat_box.insert("end", f"\n[ROUTING -> {t}] {r}\n", "routing")
                                chat_box.see("end")
                            self.root.after(0, show_r)

                        elif et == "artifact":
                            a = ev.get("artifact", {})
                            def show_a(title=a.get("title",""), path=a.get("file_path","")):
                                chat_box.insert("end", f"\n[ARTIFACT] {title} ({path})\n", "artifact")
                                chat_box.see("end")
                                refresh_art()
                            self.root.after(0, show_a)

                        elif et in ["sub_agent_spawn", "sub_agent_update", "sub_agent_complete"]:
                            sa = ev.get("sub_agent", {})
                            if sa and sa.get("id"):
                                self.sub_agents_tracker[sa["id"]] = sa
                            def show_sa(s=sa):
                                chat_box.insert("end", f"\n[{s.get('role')}] {s.get('name')}: {s.get('status','').upper()}\n", "subagent")
                                chat_box.see("end")
                                refresh_plan()
                            self.root.after(0, show_sa)

                    self.root.after(0, lambda: [
                        chat_box.insert("end", "\n\n"),
                        chat_box.see("end"),
                        setattr(self, 'mascot_state', 'idle'),
                        refresh_ws(),
                        refresh_plan(),
                        refresh_art()
                    ])
                asyncio.run(stream())
            threading.Thread(target=worker, daemon=True).start()

        send_btn = ctk.CTkButton(
            input_row, text="\u2192", font=("Segoe UI", 18, "bold"), width=42, height=40,
            fg_color=C["blue"], hover_color=C["blue_h"], text_color=C["tw"],
            corner_radius=R_M, command=send_msg
        )
        send_btn.pack(side="right")

        entry.bind("<Return>", lambda e: send_msg())

    # =========================================================================
    def run(self):
        self.root.mainloop()


def launch_desktop_mascot():
    app = FloatingMascotApp()
    app.run()


if __name__ == "__main__":
    launch_desktop_mascot()
