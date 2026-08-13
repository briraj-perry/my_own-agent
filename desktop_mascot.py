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
        "desc": "Creative Canvas Bot with Paint Palette & Rainbow Arms",
        "idle": "artist_bot_idle.png",
        "coding": "artist_bot_coding.png"
    },
    "server_bot": {
        "name": "🖥️ Server Bot (QA & Systems Engineer)",
        "desc": "Retro Server Rack Bot with Glowing Matrix Face",
        "idle": "server_bot_idle.png",
        "coding": "server_bot_coding.png"
    },
    "launch_bot": {
        "name": "🚀 Launch Bot (Deployment & Build Specialist)",
        "desc": "High-Speed Cyber Rocket Mascot",
        "idle": "launch_bot_idle.png",
        "coding": "launch_bot_coding.png"
    },
    "cloud_bot": {
        "name": "☁️ Cloud Bot (Cloud & API Specialist)",
        "desc": "Playful Pixel Cloud Mascot with Sweatdrop",
        "idle": "cloud_bot_idle.png",
        "coding": "cloud_bot_coding.png"
    },
    "fox_bot": {
        "name": "🦊 Fox Bot (Cyber Fox Engine)",
        "desc": "Futuristic Cyber Fox with FOX Visor",
        "idle": "fox_bot_idle.png",
        "coding": "fox_bot_coding.png"
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
        settings_dlg.geometry("560x620")
        settings_dlg.attributes("-topmost", True)
        settings_dlg.config(bg="#f8fafc")

        lbl_hdr = tk.Label(settings_dlg, text="⚙️ Select Desktop Mascot Character", bg="#ffffff", fg="#0f172a", font=("Outfit", 13, "bold"), pady=10)
        lbl_hdr.pack(fill="x", side="top")

        lbl_sub = tk.Label(settings_dlg, text="Click any character below to switch live! 100% transparent patch-free overlay.", bg="#f8fafc", fg="#64748b", font=("Segoe UI", 9), pady=6)
        lbl_sub.pack()

        selected_var = tk.StringVar(value=self.active_theme_key)

        # Scrollable Canvas Container for all 14 mascots
        container = tk.Frame(settings_dlg, bg="#f8fafc")
        container.pack(fill="both", expand=True, padx=12, pady=6)

        canvas = tk.Canvas(container, bg="#f8fafc", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f8fafc")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        card_frames = {}

        def update_card_visuals(active_key):
            for k, card_el in card_frames.items():
                is_active = (k == active_key)
                card_el.config(
                    bg="#e0e7ff" if is_active else "#ffffff",
                    highlightbackground="#4f46e5" if is_active else "#cbd5e1"
                )

        def on_select_theme(key):
            selected_var.set(key)
            self.load_mascot_theme(key)
            update_card_visuals(key)

        for key, info in MASCOT_THEMES.items():
            card = tk.Frame(scrollable_frame, bg="#e0e7ff" if self.active_theme_key == key else "#ffffff", bd=1, relief="solid", highlightbackground="#4f46e5" if self.active_theme_key == key else "#cbd5e1", highlightthickness=2)
            card.pack(fill="x", pady=5, ipady=4, ipadx=8)
            card_frames[key] = card

            # Left thumbnail image preview
            img_lbl = None
            if hasattr(self, "mascot_cache") and key in self.mascot_cache and self.mascot_cache[key].get("idle"):
                preview_img = self.mascot_cache[key].get("idle")
                img_lbl = tk.Label(card, image=preview_img, bg=card.cget("bg"))
                img_lbl.pack(side="left", padx=8)

            content_box = tk.Frame(card, bg=card.cget("bg"))
            content_box.pack(side="left", fill="both", expand=True)

            rb = tk.Radiobutton(
                content_box,
                text=info["name"],
                variable=selected_var,
                value=key,
                bg=card.cget("bg"),
                fg="#0f172a",
                selectcolor="#ffffff",
                activebackground=card.cget("bg"),
                activeforeground="#0f172a",
                font=("Segoe UI", 11, "bold"),
                command=lambda k=key: on_select_theme(k)
            )
            rb.pack(anchor="w", side="top")

            desc = tk.Label(content_box, text=info["desc"], bg=card.cget("bg"), fg="#64748b", font=("Segoe UI", 9))
            desc.pack(anchor="w", padx=24)

            card.bind("<Button-1>", lambda e, k=key: on_select_theme(k))
            content_box.bind("<Button-1>", lambda e, k=key: on_select_theme(k))
            desc.bind("<Button-1>", lambda e, k=key: on_select_theme(k))
            if img_lbl:
                img_lbl.bind("<Button-1>", lambda e, k=key: on_select_theme(k))

        def apply_choice():
            new_theme = selected_var.get()
            self.load_mascot_theme(new_theme)
            try:
                canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
            messagebox.showinfo("Mascot Updated", f"🎉 Mascot successfully active:\n{MASCOT_THEMES[new_theme]['name']}!")
            settings_dlg.destroy()

        btn_save = tk.Button(settings_dlg, text="Done 🚀", bg="#4f46e5", fg="#ffffff", font=("Segoe UI", 10, "bold"), bd=0, command=apply_choice)
        btn_save.pack(pady=10, ipadx=24, ipady=6)


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
        self.chat_window.title("my_neo-agent Companion Studio v2.0")
        self.chat_window.geometry("720x780")
        self.chat_window.attributes("-topmost", True)
        self.chat_window.config(bg="#090d16")

        # Apply ttk Professional Dark Theme Styles
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background='#090d16', borderwidth=0)
        style.configure('TNotebook.Tab', background='#1e293b', foreground='#94a3b8', padding=[18, 9], font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', '#4f46e5')], foreground=[('selected', '#ffffff')])

        # Top Header Bar
        header_frame = tk.Frame(self.chat_window, bg="#0f172a", height=54, highlightthickness=1, highlightbackground="rgba(255, 255, 255, 0.1)")
        header_frame.pack(fill="x", side="top")

        title_lbl = tk.Label(header_frame, text=" ⚡ my_neo-agent Companion Studio", bg="#0f172a", fg="#f8fafc", font=("Outfit", 13, "bold"))
        title_lbl.pack(side="left", padx=14, pady=10)

        btn_settings = tk.Button(header_frame, text="⚙️ Mascots", bg="#4f46e5", fg="#ffffff", font=("Segoe UI", 9, "bold"), bd=0, command=self.open_mascot_settings)
        btn_settings.pack(side="right", padx=(0, 12))

        curr_p = file_tools.get_workspace_root()
        disp_folder = os.path.basename(curr_p) or curr_p
        folder_lbl = tk.Label(header_frame, text=f"📁 {disp_folder}", bg="rgba(56, 189, 248, 0.15)", fg="#38bdf8", font=("Consolas", 9, "bold"), padx=12, pady=4)
        folder_lbl.pack(side="right", padx=6)

        # Tabbed Notebook Layout
        notebook = ttk.Notebook(self.chat_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Chat Stream & Quick Prompts
        chat_tab = tk.Frame(notebook, bg="#090d16")
        notebook.add(chat_tab, text="💬 Live AI Chat")

        chat_box = tk.Text(chat_tab, bg="#030712", fg="#cbd5e1", font=("Segoe UI", 10), wrap="word", highlightthickness=1, highlightbackground="rgba(255, 255, 255, 0.1)", bd=0)
        chat_box.pack(fill="both", expand=True, padx=8, pady=8)

        # Tags formatting for sleek dark theme
        chat_box.tag_config("user", foreground="#818cf8", font=("Segoe UI", 10, "bold"))
        chat_box.tag_config("assistant", foreground="#38bdf8", font=("Segoe UI", 10, "bold"))
        chat_box.tag_config("system", foreground="#94a3b8", font=("Segoe UI", 10, "italic"))
        chat_box.tag_config("plan", foreground="#c084fc", font=("Consolas", 10, "bold"))
        chat_box.tag_config("subagent", foreground="#34d399", font=("Segoe UI", 9, "bold"))

        chat_box.insert("end", "🤖 Neo Mascot Companion Studio v2.0 Initialized.\n", "system")
        chat_box.insert("end", f"Active Workspace: '{curr_p}'\nDynamic DAG Planning & AST Auto-Correction Active!\n\n")

        # Quick Action Prompt Bar
        quick_bar = tk.Frame(chat_tab, bg="#090d16")
        quick_bar.pack(fill="x", padx=8, pady=(0, 4))

        def quick_prompt(text):
            entry.delete(0, "end")
            entry.insert(0, text)
            send_msg()

        btn_nextjs = tk.Button(quick_bar, text="🚀 Next.js App", bg="#4f46e5", fg="#ffffff", font=("Segoe UI", 8, "bold"), bd=0, command=lambda: quick_prompt("Build a complete interactive Next.js application"))
        btn_nextjs.pack(side="left", padx=(0, 4), ipady=4, ipadx=8)

        btn_app = tk.Button(quick_bar, text="⚡ HTML App", bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 8, "bold"), bd=0, command=lambda: quick_prompt("Build a complete interactive Calculator web app with HTML, CSS, and JS"))
        btn_app.pack(side="left", padx=(0, 4), ipady=4, ipadx=8)

        btn_fix = tk.Button(quick_bar, text="🐞 Auto-Fix", bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 8, "bold"), bd=0, command=lambda: self.trigger_folder_analysis())
        btn_fix.pack(side="left", padx=(0, 4), ipady=4, ipadx=8)

        btn_screen = tk.Button(quick_bar, text="👁️ Vision Debug", bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 8, "bold"), bd=0, command=lambda: self.trigger_screen_analysis())
        btn_screen.pack(side="left", padx=(0, 4), ipady=4, ipadx=8)

        btn_folder = tk.Button(quick_bar, text="📂 Open Folder", bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 8, "bold"), bd=0, command=self.select_any_system_folder)
        btn_folder.pack(side="left", padx=(0, 4), ipady=4, ipadx=8)

        # Attachment status row
        attach_frame = tk.Frame(chat_tab, bg="#090d16")
        attach_frame.pack(fill="x", padx=8, pady=(0, 2))

        attach_label = tk.Label(attach_frame, text="", bg="#090d16", fg="#a5b4fc", font=("Segoe UI", 9, "bold"))
        attach_label.pack(side="left")

        # Input Frame
        input_frame = tk.Frame(chat_tab, bg="#090d16")
        input_frame.pack(fill="x", padx=8, pady=(0, 8))

        # Image attachment state
        self.attached_image_b64 = None
        self.attached_image_name = ""

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

        btn_attach = tk.Button(input_frame, text="🖼️ Image", bg="#1e293b", fg="#a5b4fc", font=("Segoe UI", 9, "bold"), bd=0, command=select_image_file)
        btn_attach.pack(side="left", padx=(0, 6), ipady=6, ipadx=10)

        entry = tk.Entry(input_frame, bg="#030712", fg="#f8fafc", font=("Segoe UI", 11), insertbackground="#818cf8", bd=0, highlightthickness=1, highlightbackground="rgba(255, 255, 255, 0.1)")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=6)

        # Tab 2: Dynamic Execution Plan & Sub-Agents DAG
        plan_tab = tk.Frame(notebook, bg="#090d16")
        notebook.add(plan_tab, text="🧠 Planning & Sub-Agents")

        plan_hdr = tk.Label(plan_tab, text="🧠 Active Execution Plan DAG", bg="#090d16", fg="#f8fafc", font=("Outfit", 11, "bold"))
        plan_hdr.pack(anchor="w", padx=10, pady=(8, 2))

        plan_txt = tk.Text(plan_tab, bg="#030712", fg="#cbd5e1", font=("Consolas", 10), wrap="word", highlightthickness=1, highlightbackground="rgba(255, 255, 255, 0.1)", bd=0)
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
        ws_tab = tk.Frame(notebook, bg="#090d16")
        notebook.add(ws_tab, text="📁 Workspace Files")

        ws_bar = tk.Frame(ws_tab, bg="#0f172a", pady=6, padx=10, highlightthickness=1, highlightbackground="rgba(255, 255, 255, 0.1)")
        ws_bar.pack(fill="x", side="top")

        lbl_ws_info = tk.Label(ws_bar, text="📁 Workspace Explorer", bg="#0f172a", fg="#f8fafc", font=("Consolas", 10, "bold"))
        lbl_ws_info.pack(side="left")

        def open_file_dialog_viewer(filename):
            res = file_tools.read_file(filename)
            if res.get("status") != "success":
                messagebox.showerror("Error Opening File", f"Could not read file '{filename}': {res.get('message')}")
                return
            
            view_dlg = tk.Toplevel(self.chat_window)
            is_py = filename.endswith(".py") or filename.endswith(".pyw")
            view_dlg.title(f"🐍 Viewing Python File: {filename}" if is_py else f"📄 Viewing File: {filename}")
            view_dlg.geometry("700x560")
            view_dlg.attributes("-topmost", True)
            view_dlg.config(bg="#090d16")

            lbl_header = tk.Label(view_dlg, text=f"{'🐍' if is_py else '📄'} {filename} ({res.get('lines', 0)} lines)", bg="#0f172a", fg="#f8fafc", font=("Consolas", 11, "bold"), pady=10)
            lbl_header.pack(fill="x", side="top")

            txt_body = tk.Text(view_dlg, bg="#030712", fg="#cbd5e1", font=("Consolas", 10), wrap="none", highlightthickness=1, highlightbackground="rgba(255, 255, 255, 0.1)", bd=0)
            txt_body.pack(fill="both", expand=True, padx=10, pady=10)
            txt_body.insert("end", res.get("content", ""))

            btn_close = tk.Button(view_dlg, text="Close Viewer", bg="#4f46e5", fg="#ffffff", font=("Segoe UI", 10, "bold"), bd=0, command=view_dlg.destroy)
            btn_close.pack(pady=(0, 10), ipadx=16, ipady=4)

        ws_txt = tk.Text(ws_tab, bg="#030712", fg="#cbd5e1", font=("Consolas", 9), wrap="word", highlightthickness=1, highlightbackground="rgba(255, 255, 255, 0.1)", bd=0)
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

        btn_refresh_ws = tk.Button(ws_bar, text="🔄 Refresh Files", bg="#4f46e5", fg="#ffffff", font=("Segoe UI", 9, "bold"), command=refresh_ws_view)
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

                        elif evt_type == "framework_selection_required":
                            req_id = event.get("id")
                            def ask_framework(rid=req_id):
                                ans = messagebox.askyesno(
                                    "Choose App Framework",
                                    "Do you want to build this using Next.js or normal HTML?\n\n"
                                    "• Click YES to use Next.js (Claw Agent)\n"
                                    "• Click NO to use Normal HTML (Neo Agent)",
                                    parent=self.root
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
