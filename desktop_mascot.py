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

from agent.core import NeoAgentCore
from tools.screen_perception import ScreenPerceptionEngine
from tools import file_tools

MASCOT_THEMES = {
    "blue_bot": {
        "name": "🤖 Classic Blue Neo Bot",
        "desc": "Original Electric Blue Cloud Robot Mascot (100% Patch-Free)",
        "idle": "blue_bot_idle.png",
        "coding": "blue_bot_coding.png"
    },
    "pixel_bot": {
        "name": "🤖 Neo Purple Bot",
        "desc": "Classic Cyberpunk Purple Pixel Robot",
        "idle": "pixel_bot_idle.png",
        "coding": "pixel_bot_coding.png"
    },
    "cyber_cat": {
        "name": "🐱 Cyber Neko Cat",
        "desc": "Futuristic Neon Cyan Cat with Visor Ears",
        "idle": "cyber_cat_idle.png",
        "coding": "cyber_cat_coding.png"
    },
    "neon_dragon": {
        "name": "🐉 Neon Cyber Dragon",
        "desc": "Emerald Dragon with Glowing Cyber Horns",
        "idle": "neon_dragon_idle.png",
        "coding": "neon_dragon_coding.png"
    },
    "cosmic_orb": {
        "name": "✦ Cosmic AI Orb",
        "desc": "Floating Crystal Orb with Satellite Rings",
        "idle": "cosmic_orb_idle.png",
        "coding": "cosmic_orb_coding.png"
    },
    "vector_bot": {
        "name": "🤖 Dynamic Vector Bot",
        "desc": "Hand-Drawn Dynamic Cyber Canvas Bot",
        "idle": "",
        "coding": ""
    }
}

class FloatingMascotApp:
    """Ultra-Modern Cyber Desktop Mascot Companion Overlay & DAG Planning Studio GUI."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("my_neo-agent Desktop Mascot Studio")
        
        # Window attributes: frameless, transparent background, always on top
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        # Transparent background color key
        self.trans_color = "#010101"
        self.root.config(bg=self.trans_color)
        self.root.wm_attributes("-transparentcolor", self.trans_color)

        # Position mascot near bottom right of screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        mascot_x = screen_w - 210
        mascot_y = screen_h - 250
        self.root.geometry(f"190x210+{mascot_x}+{mascot_y}")

        # Dragging state & state tracking initialized FIRST
        self.start_x = 0
        self.start_y = 0
        self.tick = 0
        self.mascot_state = "idle" # idle, planning, thinking, permission, executing, ast_check, success
        self.chat_window = None
        self.current_plan = None
        self.sub_agents_tracker = {}
        self.current_folder = file_tools.get_workspace_root()
        self.attached_image_b64 = None
        self.attached_image_name = ""

        # Agent & Screen Engine
        self.agent = NeoAgentCore()
        self.screen_engine = ScreenPerceptionEngine()

        # Canvas for animated pixel-art mascot rendering
        self.canvas = tk.Canvas(self.root, width=190, height=210, bg=self.trans_color, highlightthickness=0)
        self.canvas.pack()

        # Preload all mascot themes into permanent memory cache
        self.active_theme_key = "blue_bot"
        self.preload_all_mascot_themes()
        self.load_mascot_theme(self.get_saved_theme())

        # Canvas Click & Drag Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", self.show_context_menu)
        self.canvas.bind("<Double-Button-1>", lambda e: self.open_chat_dialog())

        # Build Context Menu
        self.context_menu = tk.Menu(self.root, tearoff=0, bg="#120e20", fg="#00f5d4", activebackground="#7b2cbf", activeforeground="#ffffff", font=("Segoe UI", 9, "bold"))
        self.context_menu.add_command(label="💬 Open Neo Companion Studio", command=self.open_chat_dialog)
        self.context_menu.add_command(label="⚙️ Choose Mascot Character...", command=self.open_mascot_settings)
        self.context_menu.add_command(label="📂 Open Any System Folder...", command=self.select_any_system_folder)
        self.context_menu.add_command(label="🧠 View Dynamic Execution Plan", command=lambda: self.open_chat_dialog(default_tab=1))
        self.context_menu.add_command(label="🔍 Analyze Folder & Fix Errors", command=self.trigger_folder_analysis)
        self.context_menu.add_command(label="👁️ Scan Screen & Fix Errors", command=self.trigger_screen_analysis)
        self.context_menu.add_command(label="⚡ Inspect Sub-Agents", command=self.open_subagents_dialog)
        self.context_menu.add_command(label="🌐 Open Web Dashboard", command=self.open_dashboard_browser)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="❌ Exit Mascot Companion", command=self.root.destroy)

        # Start animation loop
        self.animate()

    def preload_all_mascot_themes(self):
        """Preloads all PhotoImage instances into memory to prevent Tkinter garbage collection."""
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
        else:
            theme = MASCOT_THEMES[theme_key]
            if theme_key == "vector_bot":
                self.mascot_images = {"idle": None, "coding": None}
            else:
                mascot_dir = os.path.join(os.path.dirname(__file__), "ui", "assets", "mascots")
                idle_p = os.path.join(mascot_dir, theme["idle"])
                coding_p = os.path.join(mascot_dir, theme["coding"])
                if not os.path.exists(idle_p):
                    idle_p = os.path.join(os.path.dirname(__file__), "ui", "assets", "neo-mascot-idle.png")
                if not os.path.exists(coding_p):
                    coding_p = os.path.join(os.path.dirname(__file__), "ui", "assets", "neo-mascot-coding.png")
                self.mascot_images = {
                    "idle": tk.PhotoImage(file=idle_p),
                    "coding": tk.PhotoImage(file=coding_p)
                }
        self.save_theme_config(theme_key)
        self.draw_mascot()

    def open_mascot_settings(self):
        settings_dlg = tk.Toplevel(self.root)
        settings_dlg.title("⚙️ Mascot & Appearance Settings")
        settings_dlg.geometry("540x520")
        settings_dlg.attributes("-topmost", True)
        settings_dlg.config(bg="#090710")

        lbl_hdr = tk.Label(settings_dlg, text="⚙️ Select Desktop Mascot Character", bg="#120e20", fg="#00f5d4", font=("Outfit", 12, "bold"), pady=10)
        lbl_hdr.pack(fill="x", side="top")

        lbl_sub = tk.Label(settings_dlg, text="Click any character below to switch live! All patches removed for 100% transparent overlay.", bg="#090710", fg="#e0aaff", font=("Segoe UI", 9), pady=6)
        lbl_sub.pack()

        selected_var = tk.StringVar(value=self.active_theme_key)

        grid_frame = tk.Frame(settings_dlg, bg="#090710")
        grid_frame.pack(fill="both", expand=True, padx=16, pady=10)

        card_frames = {}

        def update_card_visuals(active_key):
            for k, card_el in card_frames.items():
                is_active = (k == active_key)
                card_el.config(
                    bg="#141020" if is_active else "#0d0918",
                    highlightbackground="#7b2cbf" if is_active else "#221838"
                )

        def on_select_theme(key):
            selected_var.set(key)
            self.load_mascot_theme(key)
            update_card_visuals(key)

        for key, info in MASCOT_THEMES.items():
            card = tk.Frame(grid_frame, bg="#141020" if self.active_theme_key == key else "#0d0918", bd=1, relief="solid", highlightbackground="#7b2cbf" if self.active_theme_key == key else "#221838", highlightthickness=2)
            card.pack(fill="x", pady=6, ipady=6, ipadx=8)
            card_frames[key] = card

            rb = tk.Radiobutton(
                card,
                text=info["name"],
                variable=selected_var,
                value=key,
                bg=card.cget("bg"),
                fg="#00f5d4",
                selectcolor="#221838",
                activebackground=card.cget("bg"),
                activeforeground="#00f5d4",
                font=("Segoe UI", 11, "bold"),
                command=lambda k=key: on_select_theme(k)
            )
            rb.pack(anchor="w", side="top", padx=8)

            desc = tk.Label(card, text=info["desc"], bg=card.cget("bg"), fg="#a7a3b4", font=("Segoe UI", 9))
            desc.pack(anchor="w", padx=28)
            
            # Make entire card clickable
            card.bind("<Button-1>", lambda e, k=key: on_select_theme(k))
            desc.bind("<Button-1>", lambda e, k=key: on_select_theme(k))

        def apply_choice():
            new_theme = selected_var.get()
            self.load_mascot_theme(new_theme)
            messagebox.showinfo("Mascot Updated", f"🎉 Mascot successfully active:\n{MASCOT_THEMES[new_theme]['name']}!")
            settings_dlg.destroy()

        btn_save = tk.Button(settings_dlg, text="Done 🚀", bg="#7b2cbf", fg="#ffffff", font=("Segoe UI", 10, "bold"), bd=0, command=apply_choice)
        btn_save.pack(pady=12, ipadx=20, ipady=6)

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
        
        # Vertical floating bobbing animation
        bob_y = int(math.sin(self.tick * 0.12) * 5)
        cx = 95
        cy = 85 + bob_y

        is_coding = self.mascot_state in {"planning", "thinking", "executing", "ast_check"}
        img_key = "coding" if is_coding else "idle"

        # Dynamic Aura Glow Colors based on State
        glow_color = "#9d4edd"
        if self.mascot_state in {"thinking", "planning"}:
            glow_color = "#00f5d4"
        elif self.mascot_state == "permission":
            glow_color = "#f72585"
        elif self.mascot_state in {"executing", "ast_check"}:
            glow_color = "#00f5d4"
        elif self.mascot_state == "success":
            glow_color = "#10b981"

        if getattr(self, "active_theme_key", "blue_bot") == "vector_bot":
            # Outer Aura Glow for Vector Mascot only
            self.canvas.create_oval(cx - 58, cy - 52, cx + 58, cy + 52, fill=glow_color, outline="", stipple="gray25")

            # Hand-drawn Vector Mascot
            body_color = "#7b2cbf"
            self.canvas.create_oval(cx - 48, cy - 44, cx + 48, cy + 38, fill=body_color, outline="#3c096c", width=3)
            self.canvas.create_oval(cx - 34, cy - 56, cx + 34, cy - 14, fill=body_color, outline="#3c096c", width=2)
            
            # Robot Legs
            self.canvas.create_rectangle(cx - 24, cy + 34, cx - 12, cy + 50, fill=body_color, outline="#3c096c", width=2)
            self.canvas.create_rectangle(cx + 12, cy + 34, cx + 24, cy + 50, fill=body_color, outline="#3c096c", width=2)

            # Screen Monitor Face
            self.canvas.create_rectangle(cx - 32, cy - 28, cx + 32, cy + 16, fill="#0d0918", outline="#e0aaff", width=2)

            # Animated Face Expression
            face_text = "> _"
            if self.mascot_state == "planning":
                face_text = "🧠 ?"
            elif self.mascot_state == "thinking":
                face_text = "> ~"
            elif self.mascot_state == "permission":
                face_text = "! ?"
            elif self.mascot_state in ["executing", "ast_check"]:
                face_text = "⚡ ⚡"
            elif self.mascot_state == "success":
                face_text = "^ ^"

            self.canvas.create_text(cx, cy - 6, text=face_text, fill="#00f5d4", font=("Consolas", 14, "bold"))

            # Chest Emblem
            self.canvas.create_text(cx, cy + 26, text="> NEO", fill="#ffffff", font=("Consolas", 8, "bold"))
        else:
            # PNG Image Mascot (Classic Blue Bot, Pixel Bot, Cyber Cat, Neon Dragon, Cosmic Orb)
            if hasattr(self, "mascot_images") and self.mascot_images:
                active_img = self.mascot_images.get(img_key)
                if active_img:
                    self.canvas.create_image(cx, cy + 5, image=active_img)

        # Active Plan Badge / Sub-Agents Badge
        if self.current_plan:
            prog = self.current_plan.get("progress", 0)
            self.canvas.create_rectangle(cx - 55, cy - 68, cx + 55, cy - 50, fill="#7b2cbf", outline="#00f5d4", width=1)
            self.canvas.create_text(cx, cy - 59, text=f"🧠 PLAN: {prog}%", fill="#00f5d4", font=("Segoe UI", 8, "bold"))
        elif len(self.sub_agents_tracker) > 0:
            sa_count = len(self.sub_agents_tracker)
            self.canvas.create_rectangle(cx - 52, cy - 68, cx + 52, cy - 50, fill="#f72585", outline="#ffffff", width=1)
            self.canvas.create_text(cx, cy - 59, text=f"⚡ {sa_count} SUB-AGENTS", fill="#ffffff", font=("Segoe UI", 8, "bold"))

        # State Label below mascot
        state_label = "Neo Companion"
        if self.mascot_state in {"planning", "thinking"}:
            state_label = "🧠 Planning DAG..."
        elif self.mascot_state == "ast_check":
            state_label = "🧪 AST Verifying..."
        elif self.mascot_state == "executing":
            state_label = "⚡ Writing Code..."
        elif self.mascot_state == "success":
            state_label = "✅ Complete!"

        self.canvas.create_text(cx, 185, text=state_label, fill="#00f5d4", font=("Segoe UI", 9, "bold"))

    def animate(self):
        self.draw_mascot()
        self.root.after(50, self.animate)

    def select_any_system_folder(self):
        """Opens native OS folder picker to let user choose ANY folder on their computer."""
        chosen = filedialog.askdirectory(title="Select Any Game or Project Folder on Your Computer")
        if chosen:
            file_tools.set_workspace_root(chosen)
            self.current_folder = chosen
            messagebox.showinfo("Active Folder Changed", f"📁 Active Working Folder set to:\n{chosen}\n\nNeo Agent can now see, analyze, and fix code in this folder!")
            if self.chat_window and self.chat_window.winfo_exists():
                self.open_chat_dialog()

    def trigger_folder_analysis(self):
        """Triggers direct code analysis on files inside target workspace folder on disk."""
        self.mascot_state = "thinking"
        
        def run_worker():
            async def task():
                res = await self.agent.analyze_and_autofix_folder(self.current_folder)
                self.root.after(0, lambda: self.show_autofix_result("Direct Workspace Folder Analysis", res))
            asyncio.run(task())

        threading.Thread(target=run_worker, daemon=True).start()

    def trigger_screen_analysis(self):
        """Triggers combined screen vision perception + target folder code auto-fix."""
        self.mascot_state = "thinking"
        
        def run_worker():
            async def task():
                res = await self.agent.analyze_and_autofix_screen_and_folder(self.current_folder)
                self.root.after(0, lambda: self.show_autofix_result("Desktop Screen & Folder Diagnostics", res))
            asyncio.run(task())

        threading.Thread(target=run_worker, daemon=True).start()

    def show_autofix_result(self, title, result):
        self.mascot_state = "idle"
        status = result.get("status")
        msg = result.get("message", "")

        if status in ["fixed", "success"]:
            self.mascot_state = "success"
            messagebox.showinfo(title, f"🎉 {msg}\n\nTarget File: {result.get('target_file')}\nPath: {result.get('full_path')}")
        elif status == "clean":
            messagebox.showinfo(title, msg)
        else:
            messagebox.showwarning(title, f"⚠️ Diagnostic Notice:\n{msg}")

    def open_dashboard_browser(self):
        import webbrowser
        webbrowser.open("http://127.0.0.1:8000")

    def open_subagents_dialog(self):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.lift()
            return
        self.open_chat_dialog(default_tab=1)

    def open_chat_dialog(self, default_tab=0):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.lift()
            return

        self.chat_window = tk.Toplevel(self.root)
        self.chat_window.title("my_neo-agent Companion Studio")
        self.chat_window.geometry("680x740")
        self.chat_window.attributes("-topmost", True)
        self.chat_window.config(bg="#090710")

        # Apply ttk Dark Theme Styles
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background='#090710', borderwidth=0)
        style.configure('TNotebook.Tab', background='#141020', foreground='#e0aaff', padding=[16, 9], font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', '#7b2cbf')], foreground=[('selected', '#ffffff')])

        # Top Header Bar
        header_frame = tk.Frame(self.chat_window, bg="#120e20", height=50)
        header_frame.pack(fill="x", side="top")

        title_lbl = tk.Label(header_frame, text=" ⚡ my_neo-agent Companion Studio", bg="#120e20", fg="#00f5d4", font=("Outfit", 12, "bold"))
        title_lbl.pack(side="left", padx=14, pady=10)

        btn_settings = tk.Button(header_frame, text="⚙️ Mascots", bg="#221838", fg="#00f5d4", font=("Segoe UI", 9, "bold"), bd=0, command=self.open_mascot_settings)
        btn_settings.pack(side="right", padx=(0, 10))

        curr_p = file_tools.get_workspace_root()
        disp_folder = os.path.basename(curr_p) or curr_p
        folder_lbl = tk.Label(header_frame, text=f"📁 {disp_folder}", bg="#221838", fg="#00f5d4", font=("Consolas", 9, "bold"), padx=10, pady=3)
        folder_lbl.pack(side="right", padx=6)

        # Tabbed Notebook Layout
        notebook = ttk.Notebook(self.chat_window)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # Tab 1: Chat Stream & Quick Prompts
        chat_tab = tk.Frame(notebook, bg="#090710")
        notebook.add(chat_tab, text="💬 Live AI Chat")

        chat_box = tk.Text(chat_tab, bg="#141020", fg="#ffffff", font=("Segoe UI", 10), wrap="word", highlightthickness=0, bd=0)
        chat_box.pack(fill="both", expand=True, padx=8, pady=8)

        # Tags formatting
        chat_box.tag_config("user", foreground="#f72585", font=("Segoe UI", 10, "bold"))
        chat_box.tag_config("assistant", foreground="#00f5d4", font=("Segoe UI", 10, "bold"))
        chat_box.tag_config("system", foreground="#9d4edd", font=("Segoe UI", 10, "italic"))
        chat_box.tag_config("plan", foreground="#00f5d4", font=("Consolas", 10, "bold"))
        chat_box.tag_config("subagent", foreground="#10b981", font=("Segoe UI", 9, "bold"))

        chat_box.insert("end", "🤖 Neo Companion System Initialized.\n", "system")
        chat_box.insert("end", f"Active Workspace: '{curr_p}'\nDynamic DAG Planning & AST Auto-Correction Active!\n\n")

        # Quick Action Prompt Bar
        quick_bar = tk.Frame(chat_tab, bg="#090710")
        quick_bar.pack(fill="x", padx=8, pady=(0, 4))

        def quick_prompt(text):
            entry.delete(0, "end")
            entry.insert(0, text)
            send_msg()

        btn_app = tk.Button(quick_bar, text="⚡ Build Web App", bg="#7b2cbf", fg="#ffffff", font=("Segoe UI", 8, "bold"), bd=0, command=lambda: quick_prompt("Build a complete interactive Calculator web app with HTML, CSS, and JS"))
        btn_app.pack(side="left", padx=(0, 4), ipady=3, ipadx=6)

        btn_fix = tk.Button(quick_bar, text="🐞 Auto-Fix Errors", bg="#221838", fg="#00f5d4", font=("Segoe UI", 8, "bold"), bd=0, command=lambda: self.trigger_folder_analysis())
        btn_fix.pack(side="left", padx=(0, 4), ipady=3, ipadx=6)

        btn_screen = tk.Button(quick_bar, text="👁️ Vision Debug", bg="#221838", fg="#00f5d4", font=("Segoe UI", 8, "bold"), bd=0, command=lambda: self.trigger_screen_analysis())
        btn_screen.pack(side="left", padx=(0, 4), ipady=3, ipadx=6)

        btn_folder = tk.Button(quick_bar, text="📂 Open Folder", bg="#221838", fg="#e0aaff", font=("Segoe UI", 8, "bold"), bd=0, command=self.select_any_system_folder)
        btn_folder.pack(side="left", padx=(0, 4), ipady=3, ipadx=6)

        # Input Frame
        input_frame = tk.Frame(chat_tab, bg="#090710")
        input_frame.pack(fill="x", padx=8, pady=(0, 8))

        # Image attachment state
        self.attached_image_b64 = None
        self.attached_image_name = ""

        # Attachment status row
        attach_frame = tk.Frame(chat_tab, bg="#090710")
        attach_frame.pack(fill="x", padx=8, pady=(0, 2))

        attach_label = tk.Label(attach_frame, text="", bg="#090710", fg="#00f5d4", font=("Segoe UI", 9, "bold"))
        attach_label.pack(side="left")

        def select_image_file():
            file_path = filedialog.askopenfilename(
                title="Select Image to Upload",
                filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif")]
            )
            if file_path:
                try:
                    import base64
                    with open(file_path, "rb") as img_f:
                        self.attached_image_b64 = base64.b64encode(img_f.read()).decode("utf-8")
                        self.attached_image_name = os.path.basename(file_path)
                        attach_label.config(text=f"🖼️ Attached: {self.attached_image_name}")
                except Exception as ex:
                    messagebox.showerror("Image Upload Error", f"Failed to load image: {ex}")

        def clear_image_file():
            self.attached_image_b64 = None
            self.attached_image_name = ""
            attach_label.config(text="")

        btn_attach = tk.Button(input_frame, text="🖼️ Upload Image", bg="#221838", fg="#00f5d4", font=("Segoe UI", 9, "bold"), bd=0, command=select_image_file)
        btn_attach.pack(side="left", padx=(0, 6), ipady=4, ipadx=8)

        entry = tk.Entry(input_frame, bg="#221838", fg="#00f5d4", font=("Segoe UI", 11), insertbackground="#00f5d4", bd=0, highlightthickness=1, highlightbackground="#7b2cbf")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=6)

        # Tab 2: Dynamic Execution Plan & Sub-Agents DAG
        plan_tab = tk.Frame(notebook, bg="#090710")
        notebook.add(plan_tab, text="🧠 Planning & Sub-Agents")

        plan_hdr = tk.Label(plan_tab, text="🧠 Active Execution Plan DAG", bg="#090710", fg="#00f5d4", font=("Outfit", 11, "bold"))
        plan_hdr.pack(anchor="w", padx=10, pady=(8, 2))

        plan_txt = tk.Text(plan_tab, bg="#141020", fg="#00f5d4", font=("Consolas", 10), wrap="word", bd=0)
        plan_txt.pack(fill="both", expand=True, padx=8, pady=8)

        def refresh_plan_view():
            plan_txt.delete("1.0", "end")
            if not self.current_plan:
                plan_txt.insert("end", "No active execution plan.\nAsk Neo a prompt to generate an explicit multi-step DAG execution plan!\n")
            else:
                p = self.current_plan
                plan_txt.insert("end", f"=== PLAN: {p.get('title')} ===\n")
                plan_txt.insert("end", f"Summary: {p.get('summary')}\n")
                plan_txt.insert("end", f"Overall Progress: {p.get('progress', 0)}%\n\n")
                plan_txt.insert("end", "--- EXECUTION DAG STEPS ---\n")
                for st in p.get("steps", []):
                    status_str = f"[{st.get('status').upper()}]"
                    icon = "✅" if st.get('status') == 'completed' else ("⚡" if st.get('status') == 'in_progress' else "⌛")
                    plan_txt.insert("end", f"{icon} {st.get('step_id')}: {st.get('title')} {status_str}\n")
                    plan_txt.insert("end", f"   Role: {st.get('assigned_role')} | Target File: {st.get('target_file')}\n")
                    plan_txt.insert("end", f"   Action: {st.get('description')}\n\n")

            if self.sub_agents_tracker:
                plan_txt.insert("end", "\n--- ACTIVE SUB-AGENTS ---\n")
                for sa_id, sa in self.sub_agents_tracker.items():
                    plan_txt.insert("end", f"⚡ {sa.get('name')} ({sa.get('role')}): {sa.get('status').upper()} - Progress: {sa.get('progress')}%\n")

        refresh_plan_view()

        # Tab 3: Workspace Explorer & Viewer
        ws_tab = tk.Frame(notebook, bg="#090710")
        notebook.add(ws_tab, text="📁 Workspace Files")

        ws_bar = tk.Frame(ws_tab, bg="#120e20", pady=4, padx=8)
        ws_bar.pack(fill="x", side="top")

        lbl_ws_info = tk.Label(ws_bar, text="📁 Workspace Explorer", bg="#120e20", fg="#00f5d4", font=("Consolas", 10, "bold"))
        lbl_ws_info.pack(side="left")

        def open_file_dialog_viewer(filename):
            res = file_tools.read_file(filename)
            if res.get("status") != "success":
                messagebox.showerror("Error Opening File", f"Could not read file '{filename}': {res.get('message')}")
                return
            
            view_dlg = tk.Toplevel(self.chat_window)
            is_py = filename.endswith(".py") or filename.endswith(".pyw")
            view_dlg.title(f"🐍 Viewing Python File: {filename}" if is_py else f"📄 Viewing File: {filename}")
            view_dlg.geometry("680x540")
            view_dlg.attributes("-topmost", True)
            view_dlg.config(bg="#090710")

            lbl_header = tk.Label(view_dlg, text=f"{'🐍' if is_py else '📄'} {filename} ({res.get('lines', 0)} lines)", bg="#120e20", fg="#00f5d4", font=("Consolas", 11, "bold"), pady=8)
            lbl_header.pack(fill="x", side="top")

            txt_body = tk.Text(view_dlg, bg="#141020", fg="#00f5d4" if is_py else "#e0aaff", font=("Consolas", 10), wrap="none", bd=0)
            txt_body.pack(fill="both", expand=True, padx=8, pady=8)
            txt_body.insert("end", res.get("content", ""))

            btn_close = tk.Button(view_dlg, text="Close Viewer", bg="#7b2cbf", fg="#ffffff", font=("Segoe UI", 10, "bold"), command=view_dlg.destroy)
            btn_close.pack(pady=(0, 8), ipadx=12)

        ws_txt = tk.Text(ws_tab, bg="#141020", fg="#00f5d4", font=("Consolas", 9), wrap="word", bd=0)
        ws_txt.pack(fill="both", expand=True, padx=8, pady=8)

        def refresh_ws_view():
            ws_txt.delete("1.0", "end")
            curr_root = file_tools.get_workspace_root()
            ws_files = file_tools.list_directory(curr_root)
            lbl_ws_info.config(text=f"📁 Workspace Explorer ({ws_files.get('count', 0)} items)")
            ws_txt.insert("end", f"📁 Active Folder: {curr_root}\nTotal Items: {ws_files.get('count', 0)} (Double-click file to open!)\n\n")
            for item in ws_files.get("items", []):
                if item["type"] == "directory":
                    icon = "📁"
                elif item.get("is_python") or item["name"].endswith(".py") or item["name"].endswith(".pyw"):
                    icon = "🐍"
                else:
                    icon = "📄"
                ws_txt.insert("end", f"{icon} {item['name']}\n")

        btn_refresh_ws = tk.Button(ws_bar, text="🔄 Refresh Files", bg="#7b2cbf", fg="#ffffff", font=("Segoe UI", 9, "bold"), command=refresh_ws_view)
        btn_refresh_ws.pack(side="right")

        def on_file_click(event):
            try:
                line_idx = ws_txt.index(f"@{event.x},{event.y}")
                line_text = ws_txt.get(f"{line_idx} linestart", f"{line_idx} lineend").strip()
                if line_text:
                    if "🐍" in line_text or "📄" in line_text:
                        filename = line_text.replace("🐍", "").replace("📄", "").strip()
                        open_file_dialog_viewer(filename)
            except Exception:
                pass

        ws_txt.bind("<Double-Button-1>", on_file_click)

        def on_tab_change(event):
            try:
                current_title = notebook.tab(notebook.select(), "text")
                if "Workspace Files" in current_title:
                    refresh_ws_view()
                elif "Execution Plan" in current_title:
                    refresh_plan_view()
            except Exception:
                pass

        notebook.bind("<<NotebookTabChanged>>", on_tab_change)

        refresh_ws_view()

        if default_tab > 0:
            notebook.select(default_tab)

        def send_msg():
            msg = entry.get().strip()
            if not msg and not self.attached_image_b64:
                return
            
            curr_b64 = self.attached_image_b64
            img_note = f" 🖼️ [{self.attached_image_name}]" if self.attached_image_name else ""

            entry.delete(0, "end")
            chat_box.insert("end", f"You: ", "user")
            chat_box.insert("end", f"{msg}{img_note}\n\n")
            chat_box.insert("end", "🤖 Neo Mascot: ", "assistant")
            chat_box.see("end")

            clear_image_file()
            self.mascot_state = "thinking"

            def stream_ai_worker():
                async def run_stream():
                    imgs_payload = [curr_b64] if curr_b64 else None
                    prompt_text = msg or "Inspect attached image and assist with code."
                    async for event in self.agent.stream_response(prompt_text, images=imgs_payload):
                        evt_type = event.get("type")
                        
                        if evt_type == "state":
                            st = event.get("mascot_state", "thinking")
                            self.root.after(0, setattr, self, 'mascot_state', st)
                        
                        elif evt_type == "folder_selection_required":
                            req_id = event.get("id")
                            self.agent.resolve_folder_selection(req_id, self.current_folder)

                        elif evt_type == "permission_request":
                            req_id = event.get("id")
                            self.agent.resolve_permission(req_id, True)

                        elif evt_type == "plan_generated":
                            plan_data = event.get("plan")
                            self.current_plan = plan_data
                            def show_plan_notice(p):
                                chat_box.insert("end", f"\n🧠 [DYNAMIC DAG PLAN GENERATED]: {p.get('title')}\n", "plan")
                                chat_box.see("end")
                                refresh_plan_view()
                            self.root.after(0, show_plan_notice, plan_data)

                        elif evt_type == "token":
                            token = event.get("content", "")
                            def append_token(t):
                                chat_box.insert("end", t)
                                chat_box.see("end")
                            self.root.after(0, append_token, token)

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
                        refresh_plan_view()
                    ])

                asyncio.run(run_stream())

            threading.Thread(target=stream_ai_worker, daemon=True).start()

        send_btn = tk.Button(input_frame, text="Send 🚀", bg="#7b2cbf", fg="#ffffff", font=("Segoe UI", 10, "bold"), bd=0, command=send_msg)
        send_btn.pack(side="right", ipady=4, ipadx=12)
        entry.bind("<Return>", lambda e: send_msg())

    def run(self):
        self.root.mainloop()

def launch_desktop_mascot():
    app = FloatingMascotApp()
    app.run()

if __name__ == "__main__":
    launch_desktop_mascot()
