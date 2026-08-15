import os
import sys
import json
import asyncio
import threading
import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import urllib.request
import urllib.parse

from agent.orchestrator import MasterOrchestrator
from tools.screen_perception import ScreenPerceptionEngine
from tools import file_tools

# ==============================================================================
# IBM WatsonX / Carbon Design System Palette
# ==============================================================================
CARBON_COLORS = {
    "bg_dark": "#161616",          # Gray 100
    "bg_surface": "#262626",       # Gray 90
    "bg_layer": "#121212",         # Deep workspace
    "bg_hover": "#353535",         # Hover state
    "border": "#393939",           # Gray 80
    "border_subtle": "#2b2b2b",
    "ibm_blue": "#0f62fe",         # Primary interactive
    "ibm_blue_hover": "#0043ce",
    "ibm_blue_light": "#4589ff",
    "text_primary": "#f4f4f4",     # Primary copy
    "text_secondary": "#c6c6c6",   # Secondary copy
    "text_muted": "#8d8d8d",       # Muted copy
    "tag_bg": "#393939",
    "status_success": "#24a148",
    "status_warning": "#f1c21b",
    "status_error": "#da1e28",
    "status_info": "#0043ce",
}

MASCOT_THEMES = {
    "blue_bot": {
        "name": "🤖 Classic Blue Neo Bot",
        "desc": "Original Electric Blue Cloud Robot Mascot",
        "idle": "blue_bot_idle.png",
        "coding": "blue_bot_coding.png"
    },
    "doc_bot": {
        "name": "📜 Doc Bot (Architecture & Specs)",
        "desc": "Cloud Mascot with Scroll & Checkmark Visor",
        "idle": "doc_bot_idle.png",
        "coding": "doc_bot_coding.png"
    },
    "data_bot": {
        "name": "📊 Data Bot (Analytics & Experience)",
        "desc": "Cloud Mascot with Terminal Visor & Chart Badge",
        "idle": "data_bot_idle.png",
        "coding": "data_bot_coding.png"
    },
    "code_bot": {
        "name": "⚡ Code Bot (Implementation Specialist)",
        "desc": "Cyber Matrix Bot with Binary Screen & Code Badge",
        "idle": "code_bot_idle.png",
        "coding": "code_bot_coding.png"
    },
    "artist_bot": {
        "name": "🎨 Artist Bot (Styling & CSS Designer)",
        "desc": "Creative Canvas Bot with Paint Palette",
        "idle": "artist_bot_idle.png",
        "coding": "artist_bot_coding.png"
    },
    "server_bot": {
        "name": "🖥️ Server Bot (QA & Systems Engineer)",
        "desc": "Retro Server Rack Bot with Matrix Face",
        "idle": "server_bot_idle.png",
        "coding": "server_bot_coding.png"
    },
    "pixel_bot": {
        "name": "🤖 Neo Purple Bot",
        "desc": "Classic Pixel Robot",
        "idle": "pixel_bot_idle.png",
        "coding": "pixel_bot_coding.png"
    },
    "cyber_cat": {
        "name": "🐱 Cyber Neko Cat",
        "desc": "Futuristic Neon Cyan Cat",
        "idle": "cyber_cat_idle.png",
        "coding": "cyber_cat_coding.png"
    },
    "neon_dragon": {
        "name": "🐉 Neon Cyber Dragon",
        "desc": "Emerald Dragon with Glowing Horns",
        "idle": "neon_dragon_idle.png",
        "coding": "neon_dragon_coding.png"
    },
    "cosmic_orb": {
        "name": "✦ Cosmic AI Orb",
        "desc": "Floating Crystal Orb",
        "idle": "cosmic_orb_idle.png",
        "coding": "cosmic_orb_coding.png"
    },
    "vector_bot": {
        "name": "🤖 Dynamic Vector Bot",
        "desc": "Hand-Drawn Vector Bot",
        "idle": "",
        "coding": ""
    }
}


class FloatingMascotApp:
    """IBM WatsonX-Inspired Multi-Agent Companion Studio & Desktop Assistant."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Neo Mascot Companion Studio")
        
        # Transparent frameless floating overlay
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        self.trans_color = "#010101"
        self.root.config(bg=self.trans_color)
        self.root.wm_attributes("-transparentcolor", self.trans_color)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        mascot_x = screen_w - 210
        mascot_y = screen_h - 250
        self.root.geometry(f"190x210+{mascot_x}+{mascot_y}")

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

        # Core Orchestrator & Screen Perception
        self.agent = MasterOrchestrator()
        self.screen_engine = ScreenPerceptionEngine()

        self.canvas = tk.Canvas(self.root, width=190, height=210, bg=self.trans_color, highlightthickness=0)
        self.canvas.pack()

        self.active_theme_key = "blue_bot"
        self.preload_all_mascot_themes()
        self.load_mascot_theme(self.get_saved_theme())

        # Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", self.show_context_menu)
        self.canvas.bind("<Double-Button-1>", lambda e: self.open_chat_dialog())

        # WatsonX Style Context Menu
        self.context_menu = tk.Menu(
            self.root, tearoff=0,
            bg=CARBON_COLORS["bg_surface"],
            fg=CARBON_COLORS["text_primary"],
            activebackground=CARBON_COLORS["ibm_blue"],
            activeforeground="#ffffff",
            font=("Segoe UI", 9)
        )
        self.context_menu.add_command(label="💬 Open WatsonX Studio", command=self.open_chat_dialog)
        self.context_menu.add_command(label="📁 Change Project Folder...", command=self.select_any_system_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🤖 Neo: Web Apps & Games", command=lambda: self.open_chat_dialog(default_agent="neo"))
        self.context_menu.add_command(label="⚡ Claw: Next.js Full-Stack", command=lambda: self.open_chat_dialog(default_agent="claw"))
        self.context_menu.add_command(label="🦅 Eagle: Code Review & Vision", command=lambda: self.open_chat_dialog(default_agent="eagle"))
        self.context_menu.add_command(label="📊 Herald: Presentations & PPTX", command=lambda: self.open_chat_dialog(default_agent="herald"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🔍 Analyze Workspace Folder", command=self.trigger_folder_analysis)
        self.context_menu.add_command(label="👁️ Scan Screen Diagnostics", command=self.trigger_screen_analysis)
        self.context_menu.add_command(label="⚙️ Mascot Settings...", command=self.open_mascot_settings)
        self.context_menu.add_command(label="🌐 Open Web Dashboard", command=self.open_dashboard_browser)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="✖ Exit Companion", command=self.root.destroy)

        self.animate()

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
            cfg_file = os.path.join(os.path.dirname(__file__), ".data", "mascot_config.json")
            if os.path.exists(cfg_file):
                with open(cfg_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("active_theme", "blue_bot")
        except Exception:
            pass
        return "blue_bot"

    def save_theme_config(self, theme_key):
        try:
            cfg_dir = os.path.join(os.path.dirname(__file__), ".data")
            os.makedirs(cfg_dir, exist_ok=True)
            cfg_file = os.path.join(cfg_dir, "mascot_config.json")
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump({"active_theme": theme_key}, f)
        except Exception:
            pass

    def load_mascot_theme(self, theme_key="blue_bot"):
        if theme_key not in MASCOT_THEMES:
            theme_key = "blue_bot"
        self.active_theme_key = theme_key
        if hasattr(self, "mascot_cache") and theme_key in self.mascot_cache:
            self.mascot_images = self.mascot_cache[theme_key]
        self.save_theme_config(theme_key)
        self.draw_mascot()

    def open_mascot_settings(self):
        settings_dlg = tk.Toplevel(self.root)
        settings_dlg.title("Mascot Settings")
        settings_dlg.geometry("440x360")
        settings_dlg.attributes("-topmost", True)
        settings_dlg.config(bg=CARBON_COLORS["bg_dark"])

        tk.Label(
            settings_dlg, text="Choose Mascot Avatar",
            bg=CARBON_COLORS["bg_dark"], fg=CARBON_COLORS["text_primary"],
            font=("Segoe UI", 12, "bold")
        ).pack(pady=12)

        theme_var = tk.StringVar(value=self.active_theme_key)

        container = tk.Frame(settings_dlg, bg=CARBON_COLORS["bg_surface"], bd=1, relief="solid")
        container.pack(fill="both", expand=True, padx=16, pady=8)

        for key, theme in MASCOT_THEMES.items():
            r = tk.Radiobutton(
                container, text=theme["name"], value=key, variable=theme_var,
                bg=CARBON_COLORS["bg_surface"], fg=CARBON_COLORS["text_primary"],
                selectcolor=CARBON_COLORS["bg_dark"],
                activebackground=CARBON_COLORS["bg_hover"],
                activeforeground=CARBON_COLORS["text_primary"],
                font=("Segoe UI", 9)
            )
            r.pack(anchor="w", padx=12, pady=3)

        def apply_choice():
            new_theme = theme_var.get()
            self.load_mascot_theme(new_theme)
            settings_dlg.destroy()

        btn_save = tk.Button(
            settings_dlg, text="Apply Avatar",
            bg=CARBON_COLORS["ibm_blue"], fg="#ffffff",
            font=("Segoe UI", 9, "bold"), bd=0,
            command=apply_choice
        )
        btn_save.pack(pady=12, ipadx=18, ipady=5)

    def on_click(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def on_drag(self, event):
        x = self.root.winfo_x() + (event.x - self.start_x)
        y = self.root.winfo_y() + (event.y - self.start_y)
        self.root.geometry(f"+{x}+{y}")

    def show_context_menu(self, event):
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def draw_mascot(self):
        if not hasattr(self, "canvas") or self.canvas is None:
            return
        if not hasattr(self, "tick"):
            self.tick = 0
        if not hasattr(self, "mascot_state"):
            self.mascot_state = "idle"

        self.canvas.delete("all")
        self.tick += 1
        
        bob_y = int(math.sin(self.tick * 0.12) * 5)
        cx = 95
        cy = 85 + bob_y

        is_coding = self.mascot_state in {"planning", "thinking", "executing", "ast_check"}
        img_key = "coding" if is_coding else "idle"

        if hasattr(self, "mascot_images") and self.mascot_images:
            active_img = self.mascot_images.get(img_key)
            if active_img:
                self.canvas.create_image(cx, cy + 5, image=active_img)

        # Status text below mascot
        state_label = "Neo Companion"
        if self.mascot_state in {"planning", "thinking"}:
            state_label = "Processing..."
        elif self.mascot_state == "executing":
            state_label = "Writing Code..."
        elif self.mascot_state == "success":
            state_label = "Task Complete"

        self.canvas.create_text(cx, 185, text=state_label, fill=CARBON_COLORS["ibm_blue_light"], font=("Segoe UI", 9, "bold"))

    def animate(self):
        self.draw_mascot()
        self.root.after(50, self.animate)

    def select_any_system_folder(self):
        """Native OS folder picker to let user choose ANY directory on their system."""
        chosen = filedialog.askdirectory(
            title="Select Project Workspace Folder",
            initialdir=self.current_folder
        )
        if chosen:
            chosen_abs = os.path.abspath(chosen)
            file_tools.set_workspace_root(chosen_abs)
            self.current_folder = chosen_abs
            
            # Notify user
            messagebox.showinfo(
                "Workspace Changed",
                f"Project Workspace successfully set to:\n{chosen_abs}\n\nAll agents will now work in this directory."
            )
            
            # Update chat dialog if open
            if self.chat_window and self.chat_window.winfo_exists():
                if hasattr(self, "lbl_current_workspace_path") and self.lbl_current_workspace_path:
                    self.lbl_current_workspace_path.config(text=chosen_abs)
                if hasattr(self, "lbl_header_folder") and self.lbl_header_folder:
                    self.lbl_header_folder.config(text=f"📂 {os.path.basename(chosen_abs) or chosen_abs}")
                if hasattr(self, "refresh_ws_view_fn") and self.refresh_ws_view_fn:
                    self.refresh_ws_view_fn()

    def trigger_folder_analysis(self):
        self.mascot_state = "thinking"
        def run_worker():
            async def task():
                res = await self.agent.analyze_and_autofix_folder(self.current_folder)
                self.root.after(0, lambda: self.show_autofix_result("Workspace Analysis", res))
            asyncio.run(task())
        threading.Thread(target=run_worker, daemon=True).start()

    def trigger_screen_analysis(self):
        self.mascot_state = "thinking"
        def run_worker():
            async def task():
                res = await self.agent.analyze_and_autofix_screen_and_folder(self.current_folder)
                self.root.after(0, lambda: self.show_autofix_result("Screen Diagnostics", res))
            asyncio.run(task())
        threading.Thread(target=run_worker, daemon=True).start()

    def show_autofix_result(self, title, result):
        self.mascot_state = "idle"
        status = result.get("status")
        msg = result.get("message", "")
        if status in ["fixed", "success"]:
            self.mascot_state = "success"
            messagebox.showinfo(title, f"Resolved successfully:\n{msg}\n\nTarget File: {result.get('target_file')}")
        else:
            messagebox.showinfo(title, msg)

    def open_dashboard_browser(self):
        import webbrowser
        webbrowser.open("http://127.0.0.1:8000")

    # =========================================================================
    # IBM WatsonX Professional Desktop Studio GUI
    # =========================================================================
    def open_chat_dialog(self, default_tab=0, default_agent="auto"):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.lift()
            return

        self.chat_window = tk.Toplevel(self.root)
        self.chat_window.title("IBM WatsonX • Neo Agentic AI Studio")
        self.chat_window.geometry("880x880")
        self.chat_window.minsize(720, 680)
        self.chat_window.attributes("-topmost", True)
        self.chat_window.config(bg=CARBON_COLORS["bg_dark"])

        self.selected_agent = default_agent

        # Configure Carbon TTK Styles
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background=CARBON_COLORS["bg_dark"], borderwidth=0)
        style.configure(
            'TNotebook.Tab',
            background=CARBON_COLORS["bg_surface"],
            foreground=CARBON_COLORS["text_secondary"],
            padding=[18, 9],
            font=('Segoe UI', 9, 'bold')
        )
        style.map(
            'TNotebook.Tab',
            background=[('selected', CARBON_COLORS["ibm_blue"])],
            foreground=[('selected', '#ffffff')]
        )

        # ---------------------------------------------------------------------
        # Top WatsonX Header
        # ---------------------------------------------------------------------
        header_frame = tk.Frame(self.chat_window, bg=CARBON_COLORS["bg_surface"], height=52, bd=0)
        header_frame.pack(fill="x", side="top")

        # WatsonX Brand Logo/Text
        brand_frame = tk.Frame(header_frame, bg=CARBON_COLORS["bg_surface"])
        brand_frame.pack(side="left", padx=16, pady=10)

        tk.Label(
            brand_frame, text="watsonx",
            bg=CARBON_COLORS["bg_surface"], fg="#ffffff",
            font=("Segoe UI", 13, "bold")
        ).pack(side="left")

        tk.Label(
            brand_frame, text=".ai  |  Neo Companion Studio",
            bg=CARBON_COLORS["bg_surface"], fg=CARBON_COLORS["text_secondary"],
            font=("Segoe UI", 10)
        ).pack(side="left", padx=(4, 0))

        # Right Header Actions
        btn_launch_web = tk.Button(
            header_frame, text="🌐 Launch Web UI",
            bg=CARBON_COLORS["bg_hover"], fg=CARBON_COLORS["ibm_blue_light"],
            font=("Segoe UI", 8, "bold"), bd=0, padx=10, pady=4,
            activebackground=CARBON_COLORS["ibm_blue"], activeforeground="#ffffff",
            command=self.open_dashboard_browser
        )
        btn_launch_web.pack(side="right", padx=12)

        self.lbl_header_folder = tk.Label(
            header_frame,
            text=f"📂 {os.path.basename(self.current_folder) or self.current_folder}",
            bg=CARBON_COLORS["bg_hover"], fg=CARBON_COLORS["text_primary"],
            font=("Consolas", 9), padx=10, pady=4
        )
        self.lbl_header_folder.pack(side="right", padx=4)

        # ---------------------------------------------------------------------
        # PROMINENT PROJECT WORKSPACE BAR (Allows choosing folder anytime!)
        # ---------------------------------------------------------------------
        workspace_bar = tk.Frame(
            self.chat_window,
            bg=CARBON_COLORS["bg_layer"],
            bd=1, relief="solid",
            highlightthickness=1, highlightbackground=CARBON_COLORS["border"]
        )
        workspace_bar.pack(fill="x", padx=12, pady=(10, 4))

        tk.Label(
            workspace_bar, text="PROJECT WORKSPACE:",
            bg=CARBON_COLORS["bg_layer"], fg=CARBON_COLORS["text_muted"],
            font=("Segoe UI", 8, "bold")
        ).pack(side="left", padx=(12, 6), pady=8)

        self.lbl_current_workspace_path = tk.Label(
            workspace_bar,
            text=self.current_folder,
            bg=CARBON_COLORS["bg_surface"],
            fg=CARBON_COLORS["ibm_blue_light"],
            font=("Consolas", 9, "bold"),
            padx=10, pady=4,
            anchor="w"
        )
        self.lbl_current_workspace_path.pack(side="left", fill="x", expand=True, padx=4, pady=6)

        btn_select_folder = tk.Button(
            workspace_bar, text="📁 Choose Folder...",
            bg=CARBON_COLORS["ibm_blue"], fg="#ffffff",
            font=("Segoe UI", 9, "bold"), bd=0,
            activebackground=CARBON_COLORS["ibm_blue_hover"], activeforeground="#ffffff",
            padx=14, pady=5,
            command=self.select_any_system_folder
        )
        btn_select_folder.pack(side="right", padx=10, pady=6)

        # ---------------------------------------------------------------------
        # Tabbed Notebook Layout
        # ---------------------------------------------------------------------
        notebook = ttk.Notebook(self.chat_window)
        notebook.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        # =====================================================================
        # TAB 1: Assistant Chat Stream
        # =====================================================================
        chat_tab = tk.Frame(notebook, bg=CARBON_COLORS["bg_dark"])
        notebook.add(chat_tab, text="Assistant Chat")

        # Carbon Agent Switcher Bar
        agent_bar = tk.Frame(chat_tab, bg=CARBON_COLORS["bg_surface"], bd=1, relief="solid")
        agent_bar.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(
            agent_bar, text="AGENT SPECIALIST:",
            bg=CARBON_COLORS["bg_surface"], fg=CARBON_COLORS["text_muted"],
            font=("Segoe UI", 8, "bold")
        ).pack(side="left", padx=(10, 8), pady=6)

        agent_buttons = {}

        def set_agent_mode(agent_key):
            self.selected_agent = agent_key
            for k, btn in agent_buttons.items():
                if k == agent_key:
                    btn.config(bg=CARBON_COLORS["ibm_blue"], fg="#ffffff")
                else:
                    btn.config(bg=CARBON_COLORS["bg_hover"], fg=CARBON_COLORS["text_secondary"])

        agent_definitions = [
            ("auto", "🎯 Auto (Master)"),
            ("neo", "🤖 Neo (Web / Apps)"),
            ("claw", "⚡ Claw (Next.js)"),
            ("eagle", "🦅 Eagle (Review / Debug)"),
            ("herald", "📊 Herald (Presentations)"),
        ]

        for k, label in agent_definitions:
            is_active = (k == self.selected_agent)
            btn = tk.Button(
                agent_bar, text=label,
                bg=CARBON_COLORS["ibm_blue"] if is_active else CARBON_COLORS["bg_hover"],
                fg="#ffffff" if is_active else CARBON_COLORS["text_secondary"],
                font=("Segoe UI", 8, "bold"),
                bd=0, padx=10, pady=4,
                activebackground=CARBON_COLORS["ibm_blue_hover"], activeforeground="#ffffff",
                command=lambda ak=k: set_agent_mode(ak)
            )
            btn.pack(side="left", padx=3, pady=4)
            agent_buttons[k] = btn

        # Quick Starter Action Chips
        chips_frame = tk.Frame(chat_tab, bg=CARBON_COLORS["bg_dark"])
        chips_frame.pack(fill="x", padx=8, pady=(2, 4))

        def send_quick_prompt(prompt_text, force_agent=None):
            if force_agent:
                set_agent_mode(force_agent)
            entry.delete(0, "end")
            entry.insert(0, prompt_text)
            send_msg()

        chip_specs = [
            ("🎮 Build Web Game", "Build a single-file retro Snake arcade game with score tracking and sound effects", "neo"),
            ("⚡ Next.js Project", "Build a complete Next.js developer portfolio with animated dark mode glassmorphism UI", "claw"),
            ("🦅 Review Workspace", "Analyze code in my workspace, identify any bugs, and generate an educational DebugCard", "eagle"),
            ("📊 10-Slide Deck", "Create a professional presentation about Artificial Intelligence with 10 slides and speaker notes", "herald"),
            ("🔍 Screen Vision", None, None)
        ]

        for title, prompt_str, ag in chip_specs:
            if title == "🔍 Screen Vision":
                cmd = self.trigger_screen_analysis
            else:
                cmd = lambda p=prompt_str, a=ag: send_quick_prompt(p, a)
            b = tk.Button(
                chips_frame, text=title,
                bg=CARBON_COLORS["bg_surface"], fg=CARBON_COLORS["text_secondary"],
                font=("Segoe UI", 8), bd=0, padx=8, pady=3,
                activebackground=CARBON_COLORS["bg_hover"], activeforeground=CARBON_COLORS["text_primary"],
                command=cmd
            )
            b.pack(side="left", padx=(0, 4))

        # Chat Message Stream
        chat_box = tk.Text(
            chat_tab,
            bg=CARBON_COLORS["bg_layer"],
            fg=CARBON_COLORS["text_primary"],
            font=("Segoe UI", 10),
            wrap="word",
            bd=1, relief="solid",
            highlightthickness=1, highlightbackground=CARBON_COLORS["border"],
            padx=12, pady=12
        )
        chat_box.pack(fill="both", expand=True, padx=8, pady=4)

        # Tags styling
        chat_box.tag_config("user_hdr", foreground=CARBON_COLORS["ibm_blue_light"], font=("Segoe UI", 10, "bold"))
        chat_box.tag_config("user_body", foreground=CARBON_COLORS["text_primary"], font=("Segoe UI", 10))
        chat_box.tag_config("assistant_hdr", foreground="#ffffff", font=("Segoe UI", 10, "bold"))
        chat_box.tag_config("assistant_body", foreground=CARBON_COLORS["text_secondary"], font=("Segoe UI", 10))
        chat_box.tag_config("system", foreground=CARBON_COLORS["text_muted"], font=("Segoe UI", 9, "italic"))
        chat_box.tag_config("routing", foreground=CARBON_COLORS["ibm_blue_light"], font=("Consolas", 9, "bold"))
        chat_box.tag_config("artifact", foreground=CARBON_COLORS["status_success"], font=("Consolas", 9, "bold"))
        chat_box.tag_config("plan", foreground=CARBON_COLORS["status_warning"], font=("Consolas", 9, "bold"))
        chat_box.tag_config("subagent", foreground="#4589ff", font=("Segoe UI", 9, "bold"))

        chat_box.insert("end", "IBM WatsonX • Neo Agentic Suite Initialized.\n", "system")
        chat_box.insert("end", f"Active Workspace: '{self.current_folder}'\nSpecialists Available: Neo (Web), Claw (Next.js), Eagle (Debug), Herald (Presentations).\n\n", "system")

        # Attachment Status Row
        attach_frame = tk.Frame(chat_tab, bg=CARBON_COLORS["bg_dark"])
        attach_frame.pack(fill="x", padx=8, pady=(0, 2))

        attach_label = tk.Label(attach_frame, text="", bg=CARBON_COLORS["bg_dark"], fg=CARBON_COLORS["ibm_blue_light"], font=("Segoe UI", 8, "bold"))
        attach_label.pack(side="left")

        def select_file_attachment():
            file_path = filedialog.askopenfilename(
                title="Select File Attachment",
                filetypes=[
                    ("Supported Files", "*.png;*.jpg;*.jpeg;*.webp;*.pdf;*.pptx;*.xlsx;*.csv;*.py;*.js;*.html;*.json"),
                    ("All Files", "*.*")
                ]
            )
            if file_path:
                self.attached_file_path = file_path
                self.attached_file_name = os.path.basename(file_path)
                ext = os.path.splitext(file_path)[1].lower()
                if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]:
                    import base64
                    with open(file_path, "rb") as img_f:
                        self.attached_image_b64 = base64.b64encode(img_f.read()).decode("utf-8")
                    attach_label.config(text=f"🖼️ Image: {self.attached_file_name}  ")
                else:
                    self.attached_image_b64 = None
                    attach_label.config(text=f"📄 Document: {self.attached_file_name}  ")

        def clear_attachment():
            self.attached_file_path = None
            self.attached_file_name = ""
            self.attached_image_b64 = None
            attach_label.config(text="")

        # Input Row
        input_frame = tk.Frame(chat_tab, bg=CARBON_COLORS["bg_dark"])
        input_frame.pack(fill="x", padx=8, pady=(0, 8))

        btn_attach = tk.Button(
            input_frame, text="📎 Attach",
            bg=CARBON_COLORS["bg_surface"], fg=CARBON_COLORS["text_secondary"],
            font=("Segoe UI", 9), bd=0,
            activebackground=CARBON_COLORS["bg_hover"], activeforeground=CARBON_COLORS["text_primary"],
            command=select_file_attachment
        )
        btn_attach.pack(side="left", padx=(0, 6), ipadx=10, ipady=6)

        entry = tk.Entry(
            input_frame,
            bg=CARBON_COLORS["bg_layer"], fg="#ffffff",
            font=("Segoe UI", 11),
            insertbackground="#ffffff",
            bd=1, relief="solid",
            highlightthickness=1, highlightbackground=CARBON_COLORS["border"]
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=6)

        # =====================================================================
        # TAB 2: Execution Plan & DAG
        # =====================================================================
        plan_tab = tk.Frame(notebook, bg=CARBON_COLORS["bg_dark"])
        notebook.add(plan_tab, text="Execution Plan & Workflow")

        plan_hdr = tk.Label(
            plan_tab, text="Dynamic Execution Plan & Multi-Agent DAG",
            bg=CARBON_COLORS["bg_dark"], fg=CARBON_COLORS["text_primary"],
            font=("Segoe UI", 11, "bold")
        )
        plan_hdr.pack(anchor="w", padx=10, pady=(10, 4))

        plan_txt = tk.Text(
            plan_tab,
            bg=CARBON_COLORS["bg_layer"], fg=CARBON_COLORS["text_secondary"],
            font=("Consolas", 10), wrap="word",
            bd=1, relief="solid",
            highlightthickness=1, highlightbackground=CARBON_COLORS["border"]
        )
        plan_txt.pack(fill="both", expand=True, padx=10, pady=8)

        def refresh_plan_view():
            plan_txt.delete("1.0", "end")
            if not self.current_plan:
                plan_txt.insert("end", "No active execution plan.\nAsk a prompt to generate a dynamic step-by-step DAG plan.\n")
            else:
                p = self.current_plan
                plan_txt.insert("end", f"=== PLAN: {p.get('title')} ===\n")
                plan_txt.insert("end", f"Summary: {p.get('summary')}\n")
                plan_txt.insert("end", f"Progress: {p.get('progress', 0)}%\n\n")
                plan_txt.insert("end", "--- EXECUTION DAG STEPS ---\n")
                for st in p.get("steps", []):
                    icon = "[DONE]" if st.get("status") == "completed" else ("[IN PROGRESS]" if st.get("status") == "in_progress" else "[PENDING]")
                    plan_txt.insert("end", f"{icon} Step {st.get('step_id')}: {st.get('title')}\n")
                    plan_txt.insert("end", f"   Assigned: {st.get('assigned_role')} | Target: {st.get('target_file')}\n")
                    plan_txt.insert("end", f"   Details: {st.get('description')}\n\n")

            if self.sub_agents_tracker:
                plan_txt.insert("end", "\n--- ACTIVE SUB-AGENTS ---\n")
                for sa_id, sa in self.sub_agents_tracker.items():
                    plan_txt.insert("end", f"• {sa.get('name')} ({sa.get('role')}): {sa.get('status').upper()} ({sa.get('progress')}%)\n")

        # =====================================================================
        # TAB 3: Workspace Explorer & Code Viewer
        # =====================================================================
        ws_tab = tk.Frame(notebook, bg=CARBON_COLORS["bg_dark"])
        notebook.add(ws_tab, text="Workspace Explorer")

        ws_bar = tk.Frame(ws_tab, bg=CARBON_COLORS["bg_surface"], bd=1, relief="solid")
        ws_bar.pack(fill="x", side="top", padx=8, pady=(8, 4))

        lbl_ws_info = tk.Label(
            ws_bar, text="📁 Workspace Files",
            bg=CARBON_COLORS["bg_surface"], fg=CARBON_COLORS["text_primary"],
            font=("Segoe UI", 9, "bold")
        )
        lbl_ws_info.pack(side="left", padx=10, pady=8)

        btn_pick_folder_ws = tk.Button(
            ws_bar, text="📁 Choose Folder",
            bg=CARBON_COLORS["ibm_blue"], fg="#ffffff",
            font=("Segoe UI", 8, "bold"), bd=0,
            command=self.select_any_system_folder
        )
        btn_pick_folder_ws.pack(side="right", padx=(4, 8), pady=4, ipadx=8, ipady=3)

        btn_refresh_ws = tk.Button(
            ws_bar, text="🔄 Refresh",
            bg=CARBON_COLORS["bg_hover"], fg=CARBON_COLORS["text_primary"],
            font=("Segoe UI", 8), bd=0,
            command=lambda: refresh_ws_view()
        )
        btn_refresh_ws.pack(side="right", padx=4, pady=4, ipadx=8, ipady=3)

        def open_file_dialog_viewer(filename):
            res = file_tools.read_file(filename)
            if res.get("status") != "success":
                messagebox.showerror("Error Opening File", f"Could not read file '{filename}': {res.get('message')}")
                return
            
            view_dlg = tk.Toplevel(self.chat_window)
            view_dlg.title(f"Code Viewer: {filename}")
            view_dlg.geometry("760x600")
            view_dlg.attributes("-topmost", True)
            view_dlg.config(bg=CARBON_COLORS["bg_dark"])

            lbl_header = tk.Label(
                view_dlg, text=f"📄 {filename} ({res.get('lines', 0)} lines)",
                bg=CARBON_COLORS["bg_surface"], fg=CARBON_COLORS["text_primary"],
                font=("Consolas", 10, "bold"), pady=8
            )
            lbl_header.pack(fill="x", side="top")

            txt_body = tk.Text(
                view_dlg,
                bg=CARBON_COLORS["bg_layer"], fg=CARBON_COLORS["text_primary"],
                font=("Consolas", 10), wrap="none",
                bd=1, relief="solid"
            )
            txt_body.pack(fill="both", expand=True, padx=10, pady=10)
            txt_body.insert("end", res.get("content", ""))

            btn_close = tk.Button(
                view_dlg, text="Close Viewer",
                bg=CARBON_COLORS["bg_surface"], fg=CARBON_COLORS["text_primary"],
                font=("Segoe UI", 9), bd=0,
                command=view_dlg.destroy
            )
            btn_close.pack(pady=(0, 10), ipadx=16, ipady=4)

        ws_txt = tk.Text(
            ws_tab,
            bg=CARBON_COLORS["bg_layer"], fg=CARBON_COLORS["text_primary"],
            font=("Consolas", 10), wrap="word",
            bd=1, relief="solid",
            highlightthickness=1, highlightbackground=CARBON_COLORS["border"]
        )
        ws_txt.pack(fill="both", expand=True, padx=8, pady=4)

        def refresh_ws_view():
            ws_txt.delete("1.0", "end")
            curr_root = os.path.abspath(file_tools.get_workspace_root())
            ws_files = file_tools.list_directory(curr_root)
            lbl_ws_info.config(text=f"📁 Workspace: {os.path.basename(curr_root) or curr_root} ({ws_files.get('count', 0)} items)")
            ws_txt.insert("end", f"PROJECT ROOT: {curr_root}\n(Double-click any file to open in code viewer)\n\n")
            for item in ws_files.get("items", []):
                if item["type"] == "directory":
                    icon = "[DIR] "
                elif item["name"].endswith((".py", ".pyw")):
                    icon = "[PY]  "
                elif item["name"].endswith((".html", ".htm")):
                    icon = "[HTML]"
                elif item["name"].endswith((".pptx", ".ppt")):
                    icon = "[PPTX]"
                elif item["name"].endswith((".js", ".jsx", ".ts", ".tsx")):
                    icon = "[JS]  "
                else:
                    icon = "[FILE]"
                ws_txt.insert("end", f"{icon} {item['name']}\n")

        self.refresh_ws_view_fn = refresh_ws_view

        def on_file_click(event):
            try:
                line_idx = ws_txt.index(f"@{event.x},{event.y}")
                line_text = ws_txt.get(f"{line_idx} linestart", f"{line_idx} lineend").strip()
                if line_text:
                    for prefix in ["[DIR] ", "[PY]  ", "[HTML]", "[PPTX]", "[JS]  ", "[FILE]"]:
                        line_text = line_text.replace(prefix, "").strip()
                    if line_text and not line_text.startswith("PROJECT ROOT"):
                        open_file_dialog_viewer(line_text)
            except Exception:
                pass

        ws_txt.bind("<Double-Button-1>", on_file_click)

        # =====================================================================
        # TAB 4: Presentations & Artifacts Hub
        # =====================================================================
        pres_tab = tk.Frame(notebook, bg=CARBON_COLORS["bg_dark"])
        notebook.add(pres_tab, text="Generated Artifacts")

        pres_bar = tk.Frame(pres_tab, bg=CARBON_COLORS["bg_surface"], bd=1, relief="solid")
        pres_bar.pack(fill="x", side="top", padx=8, pady=(8, 4))

        tk.Label(
            pres_bar, text="📊 Presentations & Output Artifacts",
            bg=CARBON_COLORS["bg_surface"], fg=CARBON_COLORS["text_primary"],
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=10, pady=8)

        def open_pres_dir():
            pres_dir = os.path.join(os.path.dirname(__file__), "data", "presentations")
            os.makedirs(pres_dir, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(pres_dir)

        btn_open_folder = tk.Button(
            pres_bar, text="📂 Open Directory",
            bg=CARBON_COLORS["bg_hover"], fg=CARBON_COLORS["text_primary"],
            font=("Segoe UI", 8), bd=0,
            command=open_pres_dir
        )
        btn_open_folder.pack(side="right", padx=6, pady=4, ipadx=8, ipady=3)

        pres_txt = tk.Text(
            pres_tab,
            bg=CARBON_COLORS["bg_layer"], fg=CARBON_COLORS["text_primary"],
            font=("Segoe UI", 10), wrap="word",
            bd=1, relief="solid",
            highlightthickness=1, highlightbackground=CARBON_COLORS["border"]
        )
        pres_txt.pack(fill="both", expand=True, padx=8, pady=4)

        def refresh_pres_view():
            pres_txt.delete("1.0", "end")
            pres_dir = os.path.join(os.path.dirname(__file__), "data", "presentations")
            os.makedirs(pres_dir, exist_ok=True)
            files = [f for f in os.listdir(pres_dir) if f.endswith((".html", ".pptx"))]
            
            pres_txt.insert("end", "GENERATED PRESENTATION DECKS & FILES\n")
            pres_txt.insert("end", f"Storage Location: {pres_dir}\n\n")
            if not files:
                pres_txt.insert("end", "No presentations generated yet.\nUse '📊 10-Slide Deck' or ask Herald to generate slide decks.\n")
            else:
                for f in files:
                    ext = "[PowerPoint PPTX]" if f.endswith(".pptx") else "[Reveal.js HTML]"
                    pres_txt.insert("end", f"• {ext} {f}\n")

        def on_tab_change(event):
            try:
                current_title = notebook.tab(notebook.select(), "text")
                if "Workspace" in current_title:
                    refresh_ws_view()
                elif "Plan" in current_title:
                    refresh_plan_view()
                elif "Artifacts" in current_title:
                    refresh_pres_view()
            except Exception:
                pass

        notebook.bind("<<NotebookTabChanged>>", on_tab_change)

        refresh_ws_view()
        refresh_plan_view()
        refresh_pres_view()

        if default_tab > 0:
            notebook.select(default_tab)

        def send_msg():
            raw_msg = entry.get().strip()
            if not raw_msg and not self.attached_image_b64 and not self.attached_file_path:
                return

            msg = raw_msg
            if self.selected_agent and self.selected_agent != "auto":
                if not msg.lower().startswith(f"@{self.selected_agent}") and not msg.lower().startswith(f"[agent:{self.selected_agent}]"):
                    msg = f"[AGENT:{self.selected_agent.upper()}] {msg}"

            curr_b64 = self.attached_image_b64
            att_note = f" 📎 [{self.attached_file_name}]" if self.attached_file_name else ""

            entry.delete(0, "end")
            chat_box.insert("end", "User: ", "user_hdr")
            chat_box.insert("end", f"{raw_msg}{att_note}\n\n", "user_body")
            chat_box.insert("end", "WatsonX Assistant: ", "assistant_hdr")
            chat_box.see("end")

            clear_attachment()
            self.mascot_state = "thinking"

            def stream_ai_worker():
                async def run_stream():
                    imgs_payload = [curr_b64] if curr_b64 else None
                    prompt_text = msg or "Inspect attachment and assist with task."
                    async for event in self.agent.stream_response(prompt_text, images=imgs_payload, target_folder=self.current_folder):
                        evt_type = event.get("type")
                        
                        if evt_type == "state":
                            st = event.get("mascot_state", "thinking")
                            self.root.after(0, setattr, self, 'mascot_state', st)
                        
                        elif evt_type == "folder_selection_required":
                            req_id = event.get("id")
                            self.agent.resolve_folder_selection(req_id, self.current_folder)

                        elif evt_type == "framework_selection_required":
                            req_id = event.get("id")
                            def ask_framework(rid=req_id):
                                ans = messagebox.askyesno(
                                    "Select Architecture Framework",
                                    "Choose architecture target:\n\n"
                                    "• Click YES for Next.js (Claw Agent)\n"
                                    "• Click NO for Single-File HTML5 (Neo Agent)",
                                    parent=self.chat_window
                                )
                                choice = "nextjs" if ans else "html"
                                self.agent.resolve_framework_selection(rid, choice)
                            self.root.after(0, ask_framework)

                        elif evt_type == "permission_request":
                            req_id = event.get("id")
                            self.agent.resolve_permission(req_id, True)

                        elif evt_type == "plan_generated":
                            plan_data = event.get("plan")
                            self.current_plan = plan_data
                            def show_plan_notice(p):
                                chat_box.insert("end", f"\n[DAG PLAN GENERATED]: {p.get('title')}\n", "plan")
                                chat_box.see("end")
                                refresh_plan_view()
                            self.root.after(0, show_plan_notice, plan_data)

                        elif evt_type == "token":
                            token = event.get("content", "")
                            def append_token(t):
                                chat_box.insert("end", t, "assistant_body")
                                chat_box.see("end")
                            self.root.after(0, append_token, token)

                        elif evt_type == "routing":
                            target = event.get("target_agent", "neo").upper()
                            reason = event.get("reasoning", "")
                            def show_routing(t, r):
                                chat_box.insert("end", f"\n🎯 [ROUTING → {t} SPECIALIST]: {r}\n", "routing")
                                chat_box.see("end")
                            self.root.after(0, show_routing, target, reason)

                        elif evt_type == "artifact":
                            art = event.get("artifact", {})
                            title = art.get("title", "Artifact")
                            fpath = art.get("file_path", "")
                            def show_artifact(t, p):
                                chat_box.insert("end", f"\n📦 [ARTIFACT PRODUCED]: {t} ({p})\n", "artifact")
                                chat_box.see("end")
                                refresh_pres_view()
                            self.root.after(0, show_artifact, title, fpath)

                        elif evt_type in ["sub_agent_spawn", "sub_agent_update", "sub_agent_complete"]:
                            sa = event.get("sub_agent", {})
                            if sa and sa.get("id"):
                                self.sub_agents_tracker[sa["id"]] = sa
                            def notify_sa(name, role, status):
                                chat_box.insert("end", f"\n⚡ [{role}] Sub-Agent '{name}': {status.upper()}\n", "subagent")
                                chat_box.see("end")
                                refresh_plan_view()
                            self.root.after(0, notify_sa, sa.get("name"), sa.get("role"), sa.get("status"))

                    self.root.after(0, lambda: [
                        chat_box.insert("end", "\n\n"),
                        chat_box.see("end"),
                        setattr(self, 'mascot_state', 'idle'),
                        refresh_ws_view(),
                        refresh_plan_view(),
                        refresh_pres_view()
                    ])

                asyncio.run(run_stream())

            threading.Thread(target=stream_ai_worker, daemon=True).start()

        send_btn = tk.Button(
            input_frame, text="Send ➔",
            bg=CARBON_COLORS["ibm_blue"], fg="#ffffff",
            font=("Segoe UI", 10, "bold"), bd=0,
            activebackground=CARBON_COLORS["ibm_blue_hover"], activeforeground="#ffffff",
            command=send_msg
        )
        send_btn.pack(side="right", padx=(0, 4), ipadx=16, ipady=5)
        entry.bind("<Return>", lambda e: send_msg())

    def run(self):
        self.root.mainloop()


def launch_desktop_mascot():
    app = FloatingMascotApp()
    app.run()


if __name__ == "__main__":
    launch_desktop_mascot()
