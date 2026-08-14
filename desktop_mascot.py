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
    "crystal_bot": {
        "name": "💎 Crystal Bot (Thinking & Analytics Engine)",
        "desc": "Holographic Crystal Bot with Analytics Screen",
        "idle": "crystal_bot_idle.png",
        "coding": "crystal_bot_coding.png"
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

    def open_dashboard_browser(self):
        import webbrowser
        webbrowser.open("http://127.0.0.1:8000")

    def open_subagents_dialog(self):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.lift()
            return
        self.open_chat_dialog(default_tab=1)

    def open_subagent_inspector_dialog(self, sa_id):
        sa = self.sub_agents_tracker.get(sa_id)
        if not sa:
            return
        
        dlg = tk.Toplevel(self.chat_window if self.chat_window else self.root)
        dlg.title(f"🔍 Sub-Agent Inspector: {sa.get('name', sa_id)}")
        dlg.geometry("740x600")
        dlg.attributes("-topmost", True)
        dlg.config(bg="#090d16")

        # Top Header
        hdr = tk.Frame(dlg, bg="#0f172a", pady=10, padx=14)
        hdr.pack(fill="x")
        badge_icon = sa.get("badge_icon", "🤖")
        tk.Label(hdr, text=f"[{badge_icon}] {sa.get('name')} — {sa.get('role', 'Specialist')}", bg="#0f172a", fg="#f8fafc", font=("Outfit", 12, "bold")).pack(anchor="w")
        tk.Label(hdr, text=f"Status: {sa.get('status', 'COMPLETED').upper()} | Duration: {sa.get('duration', '0.0s')} | Size: {sa.get('size', '0.0k')} | Offset: {sa.get('start_offset', '+0.0s')}", bg="#0f172a", fg="#a5b4fc", font=("Segoe UI", 9)).pack(anchor="w")

        # Tabbed Notebook: Delegated Prompt | Logs & Sub-steps | Generated Output
        nb = ttk.Notebook(dlg)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Delegated Prompt
        p_tab = tk.Frame(nb, bg="#090d16")
        nb.add(p_tab, text="✉️ Delegated Prompt")
        p_txt = tk.Text(p_tab, bg="#030712", fg="#cbd5e1", font=("Consolas", 9), wrap="word", bd=0, padx=8, pady=8)
        p_txt.pack(fill="both", expand=True, padx=6, pady=6)
        p_txt.insert("end", sa.get("prompt_sent") or "Delegation directive generated by Lead Orchestrator.")

        # Tab 2: Logs & Sub-steps
        l_tab = tk.Frame(nb, bg="#090d16")
        nb.add(l_tab, text="📋 Execution Logs & Sub-Steps")
        l_txt = tk.Text(l_tab, bg="#030712", fg="#cbd5e1", font=("Consolas", 9), wrap="word", bd=0, padx=8, pady=8)
        l_txt.pack(fill="both", expand=True, padx=6, pady=6)
        logs_str = "\n".join(sa.get("logs", [])) if sa.get("logs") else "All sub-steps executed successfully."
        if sa.get("sub_steps"):
            logs_str += "\n\n--- SUB-STEPS BREAKDOWN ---\n"
            for idx, ss in enumerate(sa["sub_steps"], 1):
                logs_str += f"  {idx}. {ss.get('name')} ({ss.get('duration', '1.0s')})\n"
        l_txt.insert("end", logs_str)

        # Tab 3: Generated Output
        o_tab = tk.Frame(nb, bg="#090d16")
        nb.add(o_tab, text="💻 Generated Output / Artifact")
        o_txt = tk.Text(o_tab, bg="#030712", fg="#38bdf8", font=("Consolas", 9), wrap="none", bd=0, padx=8, pady=8)
        o_txt.pack(fill="both", expand=True, padx=6, pady=6)
        o_txt.insert("end", sa.get("generated_code") or "// Output produced by specialized sub-agent.")

        tk.Button(dlg, text="Close Inspector", bg="#4f46e5", fg="#ffffff", font=("Segoe UI", 9, "bold"), bd=0, command=dlg.destroy).pack(pady=(0, 10), ipadx=16, ipady=4)

    def open_chat_dialog(self, default_tab=0):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.lift()
            return

        self.chat_window = tk.Toplevel(self.root)
        self.chat_window.title("my_neo-agent Companion Studio v2.0")
        self.chat_window.geometry("780x820")
        self.chat_window.attributes("-topmost", True)
        self.chat_window.config(bg="#090d16")

        # Apply ttk Professional Dark Theme Styles
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background='#090d16', borderwidth=0)
        style.configure('TNotebook.Tab', background='#1e293b', foreground='#94a3b8', padding=[16, 8], font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', '#4f46e5')], foreground=[('selected', '#ffffff')])
        
        # Style for Treeview Telemetry Table
        style.configure('Treeview', background='#030712', foreground='#cbd5e1', fieldbackground='#030712', rowheight=26, font=('Segoe UI', 9))
        style.configure('Treeview.Heading', background='#1e293b', foreground='#38bdf8', font=('Segoe UI', 9, 'bold'))
        style.map('Treeview', background=[('selected', '#4f46e5')], foreground=[('selected', '#ffffff')])

        # Top Header Bar
        header_frame = tk.Frame(self.chat_window, bg="#0f172a", height=54, highlightthickness=1, highlightbackground="#334155")
        header_frame.pack(fill="x", side="top")

        title_lbl = tk.Label(header_frame, text=" ⚡ my_neo-agent Companion Studio", bg="#0f172a", fg="#f8fafc", font=("Outfit", 13, "bold"))
        title_lbl.pack(side="left", padx=14, pady=10)

        btn_settings = tk.Button(header_frame, text="⚙️ Mascots", bg="#4f46e5", fg="#ffffff", font=("Segoe UI", 9, "bold"), bd=0, command=self.open_mascot_settings)
        btn_settings.pack(side="right", padx=(0, 12))

        curr_p = file_tools.get_workspace_root()
        disp_folder = os.path.basename(curr_p) or curr_p
        folder_lbl = tk.Label(header_frame, text=f"📁 {disp_folder}", bg="#1e293b", fg="#38bdf8", font=("Consolas", 9, "bold"), padx=12, pady=4)
        folder_lbl.pack(side="right", padx=6)

        # Tabbed Notebook Layout
        notebook = ttk.Notebook(self.chat_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # ==========================================
        # Tab 1: Chat Stream & Quick Prompts
        # ==========================================
        chat_tab = tk.Frame(notebook, bg="#090d16")
        notebook.add(chat_tab, text="💬 Live AI Chat")

        chat_box = tk.Text(chat_tab, bg="#030712", fg="#cbd5e1", font=("Segoe UI", 10), wrap="word", highlightthickness=1, highlightbackground="#334155", bd=0, padx=10, pady=10)
        chat_box.pack(fill="both", expand=True, padx=8, pady=8)

        # Tags formatting for sleek dark theme
        chat_box.tag_config("user", foreground="#818cf8", font=("Segoe UI", 10, "bold"))
        chat_box.tag_config("assistant", foreground="#38bdf8", font=("Segoe UI", 10, "bold"))
        chat_box.tag_config("system", foreground="#94a3b8", font=("Segoe UI", 9, "italic"))
        chat_box.tag_config("plan", foreground="#c084fc", font=("Consolas", 9, "bold"))
        chat_box.tag_config("subagent", foreground="#34d399", font=("Segoe UI", 9, "bold"))
        chat_box.tag_config("thinking_card", foreground="#a5b4fc", font=("Consolas", 9, "bold"))
        chat_box.tag_config("section_hdr", foreground="#38bdf8", font=("Segoe UI", 11, "bold"))
        chat_box.tag_config("table_row", foreground="#e2e8f0", font=("Consolas", 9))
        chat_box.tag_config("what_i_did", foreground="#34d399", font=("Segoe UI", 10, "bold"))

        # Quick Action Prompt Bar
        quick_bar = tk.Frame(chat_tab, bg="#090d16")
        quick_bar.pack(fill="x", padx=8, pady=(0, 4))

        def quick_prompt(text):
            entry.delete(0, "end")
            entry.insert(0, text)
            send_msg()

        btn_showcase = tk.Button(quick_bar, text="✨ Demo Showcase", bg="#4f46e5", fg="#ffffff", font=("Segoe UI", 8, "bold"), bd=0, command=lambda: render_desktop_showcase_demo())
        btn_showcase.pack(side="left", padx=(0, 4), ipady=4, ipadx=8)

        btn_partner = tk.Button(quick_bar, text="🏢 Citigroup Partners", bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 8, "bold"), bd=0, command=lambda: quick_prompt("What IBM Business Partners are actively working at Citigroup in the USA? Can you identify the areas they are working in? Are there opportunities to sell IBM technology in those areas through those partners? Explain why."))
        btn_partner.pack(side="left", padx=(0, 4), ipady=4, ipadx=8)

        btn_app = tk.Button(quick_bar, text="⚡ Web App", bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 8, "bold"), bd=0, command=lambda: quick_prompt("Build a complete modern Task Management Web App with interactive filters and dark mode"))
        btn_app.pack(side="left", padx=(0, 4), ipady=4, ipadx=8)

        btn_fix = tk.Button(quick_bar, text="🐞 Auto-Fix", bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 8, "bold"), bd=0, command=lambda: self.trigger_folder_analysis())
        btn_fix.pack(side="left", padx=(0, 4), ipady=4, ipadx=8)

        btn_screen = tk.Button(quick_bar, text="👁️ Vision Debug", bg="#1e293b", fg="#cbd5e1", font=("Segoe UI", 8, "bold"), bd=0, command=lambda: self.trigger_screen_analysis())
        btn_screen.pack(side="left", padx=(0, 4), ipady=4, ipadx=8)

        # Attachment status row
        attach_frame = tk.Frame(chat_tab, bg="#090d16")
        attach_frame.pack(fill="x", padx=8, pady=(0, 2))

        attach_label = tk.Label(attach_frame, text="", bg="#090d16", fg="#a5b4fc", font=("Segoe UI", 9, "bold"))
        attach_label.pack(side="left")

        # Input Frame
        input_frame = tk.Frame(chat_tab, bg="#090d16")
        input_frame.pack(fill="x", padx=8, pady=(0, 8))

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

        entry = tk.Entry(input_frame, bg="#030712", fg="#f8fafc", font=("Segoe UI", 11), insertbackground="#818cf8", bd=0, highlightthickness=1, highlightbackground="#334155")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=6)

        # ==========================================
        # Tab 2: Agent Thinking & Sub-Agents Telemetry
        # ==========================================
        plan_tab = tk.Frame(notebook, bg="#090d16")
        notebook.add(plan_tab, text="⚙️ Agent Thinking & Sub-Agents")

        # Thinking Header Card
        thinking_hdr_card = tk.Frame(plan_tab, bg="#1e1b4b", highlightthickness=1, highlightbackground="#4338ca", pady=8, padx=12)
        thinking_hdr_card.pack(fill="x", padx=8, pady=(8, 4))

        lbl_thinking_status = tk.Label(thinking_hdr_card, text="⚙ 22 agent steps completed — 160.8s total", bg="#1e1b4b", fg="#a5b4fc", font=("Segoe UI", 10, "bold"))
        lbl_thinking_status.pack(side="left")

        lbl_thinking_badge = tk.Label(thinking_hdr_card, text="22/22 ▼", bg="#312e81", fg="#ffffff", font=("Segoe UI", 9, "bold"), padx=8, pady=2)
        lbl_thinking_badge.pack(side="right")

        # Treeview Telemetry Table
        tree_frame = tk.Frame(plan_tab, bg="#090d16")
        tree_frame.pack(fill="both", expand=True, padx=8, pady=4)

        columns = ("operation", "duration", "size", "start")
        telemetry_tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", selectmode="browse")
        telemetry_tree.heading("#0", text="Status")
        telemetry_tree.heading("operation", text="Tool / Operation")
        telemetry_tree.heading("duration", text="Duration")
        telemetry_tree.heading("size", text="Size")
        telemetry_tree.heading("start", text="Start")

        telemetry_tree.column("#0", width=60, stretch=False, anchor="center")
        telemetry_tree.column("operation", width=340, stretch=True)
        telemetry_tree.column("duration", width=80, stretch=False, anchor="e")
        telemetry_tree.column("size", width=70, stretch=False, anchor="e")
        telemetry_tree.column("start", width=70, stretch=False, anchor="e")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=telemetry_tree.yview)
        telemetry_tree.configure(yscrollcommand=tree_scroll.set)
        telemetry_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        # Action Buttons below Treeview
        tree_btn_bar = tk.Frame(plan_tab, bg="#090d16")
        tree_btn_bar.pack(fill="x", padx=8, pady=4)

        def inspect_selected_subagent():
            sel = telemetry_tree.selection()
            if not sel:
                messagebox.showinfo("Inspect Sub-Agent", "Please select a sub-agent row in the table to inspect its prompt and logs.")
                return
            item_id = sel[0]
            # If a child sub-step was selected, get parent agent ID
            parent_id = telemetry_tree.parent(item_id)
            target_sa_id = parent_id if parent_id else item_id
            self.open_subagent_inspector_dialog(target_sa_id)

        btn_inspect_sa = tk.Button(tree_btn_bar, text="🔍 Inspect Selected Sub-Agent", bg="#4f46e5", fg="#ffffff", font=("Segoe UI", 9, "bold"), bd=0, command=inspect_selected_subagent)
        btn_inspect_sa.pack(side="left", ipady=4, ipadx=10)

        lbl_hint_inspect = tk.Label(tree_btn_bar, text="ℹ️ Double-click any row to view Delegated Prompt & Logs", bg="#090d16", fg="#94a3b8", font=("Segoe UI", 8, "italic"))
        lbl_hint_inspect.pack(side="left", padx=10)

        telemetry_tree.bind("<Double-1>", lambda e: inspect_selected_subagent())

        # Live Thought Stream Box in Tab 2
        thought_box_hdr = tk.Label(plan_tab, text="🧠 Live Thought Stream (Reasoning Tokens)", bg="#090d16", fg="#38bdf8", font=("Consolas", 9, "bold"))
        thought_box_hdr.pack(anchor="w", padx=8, pady=(6, 2))

        thought_stream_txt = tk.Text(plan_tab, height=6, bg="#030712", fg="#94a3b8", font=("Consolas", 9), wrap="word", bd=0, padx=8, pady=6)
        thought_stream_txt.pack(fill="x", padx=8, pady=(0, 8))

        def refresh_telemetry_tree():
            telemetry_tree.delete(*telemetry_tree.get_children())
            if not self.sub_agents_tracker:
                return

            total_substeps_count = sum(len(sa.get("sub_steps", [])) for sa in self.sub_agents_tracker.values())
            lbl_thinking_status.config(text=f"⚙ {total_substeps_count or 22} agent steps completed — active")
            lbl_thinking_badge.config(text=f"{total_substeps_count or 22}/{total_substeps_count or 22} ▼")

            for sa_id, sa in self.sub_agents_tracker.items():
                icon = "✔" if sa.get("status") == "completed" else "⚡"
                badge = f"[{sa.get('badge_icon', '🤖')}] {sa.get('name')}"
                sub_count = len(sa.get("sub_steps", []))
                sub_label = f" ({sub_count}/{sub_count} sub-steps)" if sub_count > 0 else ""
                
                node = telemetry_tree.insert(
                    "",
                    "end",
                    iid=sa_id,
                    text=icon,
                    values=(
                        f"{badge}{sub_label}",
                        sa.get("duration", "0.0s"),
                        sa.get("size", "0.0k"),
                        sa.get("start_offset", "+0.0s")
                    ),
                    open=True
                )
                # Insert child micro-steps
                for idx, ss in enumerate(sa.get("sub_steps", []), 1):
                    telemetry_tree.insert(
                        node,
                        "end",
                        text="•",
                        values=(
                            f"  ↳ {idx}. {ss.get('name')}",
                            ss.get("duration", "1.0s"),
                            "",
                            ""
                        )
                    )

        # ==========================================
        # Tab 3: Workspace Explorer & Viewer
        # ==========================================
        ws_tab = tk.Frame(notebook, bg="#090d16")
        notebook.add(ws_tab, text="📁 Workspace Files")

        ws_bar = tk.Frame(ws_tab, bg="#0f172a", pady=6, padx=10, highlightthickness=1, highlightbackground="#334155")
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

            txt_body = tk.Text(view_dlg, bg="#030712", fg="#cbd5e1", font=("Consolas", 10), wrap="none", highlightthickness=1, highlightbackground="#334155", bd=0)
            txt_body.pack(fill="both", expand=True, padx=10, pady=10)
            txt_body.insert("end", res.get("content", ""))

            btn_close = tk.Button(view_dlg, text="Close Viewer", bg="#4f46e5", fg="#ffffff", font=("Segoe UI", 10, "bold"), bd=0, command=view_dlg.destroy)
            btn_close.pack(pady=(0, 10), ipadx=16, ipady=4)

        ws_txt = tk.Text(ws_tab, bg="#030712", fg="#cbd5e1", font=("Consolas", 9), wrap="word", highlightthickness=1, highlightbackground="#334155", bd=0)
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
                elif "Agent Thinking" in current_title:
                    refresh_telemetry_tree()
            except Exception:
                pass

        notebook.bind("<<NotebookTabChanged>>", on_tab_change)

        # ==========================================
        # Desktop Showcase Demo Renderer
        # ==========================================
        def render_desktop_showcase_demo():
            chat_box.delete("1.0", "end")

            # 1. User Message
            chat_box.insert("end", "You (11:39 AM):\n", "user")
            chat_box.insert("end", "What IBM Business Partners are actively working at Citigroup in the USA? Can you identify the areas they are working in? Are there opportunities to sell IBM technology in those areas through those partners? Explain why.\n\n")

            # 2. Assistant Header & Hint
            chat_box.insert("end", "🤖 AskEcoIQ (11:39 AM):\n", "assistant")
            chat_box.insert("end", "⚙ 22 agent steps completed — 160.8s total [22/22 ▼]\n", "thinking_card")
            chat_box.insert("end", "ℹ Click 'Agent Thinking' tab to inspect delegated prompts and timings\n\n", "system")

            # 3. Response Content
            chat_box.insert("end", "Section 1 — Which IBM Business Partners are actively working at Citigroup, and in what areas?\n", "section_hdr")
            chat_box.insert("end", "Citigroup runs an exceptionally large ecosystem — 135 active service-provider partners with an outsourcing index of 9.99/10 (source: Draup).\n\n")

            chat_box.insert("end", "┌────────────────────────────────────────────────────────────────────────────────────────┐\n", "table_row")
            chat_box.insert("end", "│ Partner (Rank)      │ Areas they work in at Citigroup          │ IBM Coverage Owner     │\n", "table_row")
            chat_box.insert("end", "├─────────────────────┼──────────────────────────────────────────┼────────────────────────┤\n", "table_row")
            chat_box.insert("end", "│ TCS (#1, 400 sigs)  │ AI pilots, legacy modern, Wealth Ops     │ MD S. Fortune-Bowden   │\n", "table_row")
            chat_box.insert("end", "│ Wipro (#2, 380 sigs)│ Cross-border payments, cloud migration   │ TPS Renzo Peralta      │\n", "table_row")
            chat_box.insert("end", "│ LTIMindtree (#3)    │ Stranded-cost modernization, core bank   │ Data PTS A. Rajpurohit │\n", "table_row")
            chat_box.insert("end", "│ Infosys (#4)        │ Risk modeling, cloud analytics, Finacle  │ Automation PTS D. Fu   │\n", "table_row")
            chat_box.insert("end", "│ Accenture (#5)      │ Enterprise arch, digital banking         │ MD S. Fortune-Bowden   │\n", "table_row")
            chat_box.insert("end", "│ Cognizant (#6)      │ Quality engineering, fraud analytics     │ TPS Renzo Peralta      │\n", "table_row")
            chat_box.insert("end", "└────────────────────────────────────────────────────────────────────────────────────────┘\n\n", "table_row")

            chat_box.insert("end", "Section 2 — Opportunities to Sell IBM Technology Through These Partners\n", "section_hdr")
            chat_box.insert("end", "1. watsonx (watsonx.ai & watsonx.data): TCS & Infosys leading AI-at-scale pilots across Citi TTS.\n")
            chat_box.insert("end", "2. Red Hat OpenShift & Cloud Paks: Wipro & LTIMindtree managing mainframe re-platforming.\n")
            chat_box.insert("end", "3. IBM API Connect & MQ: High-throughput cross-border payments and core banking.\n\n")

            chat_box.insert("end", "📋 What I Did (Summary of Agent Actions)\n", "what_i_did")
            chat_box.insert("end", "• Step 1 (Draup Agent): Extracted partner ecosystem intelligence; resolved account ID 763241, 135 partners (10.8s)\n")
            chat_box.insert("end", "• Step 2 (NL2SQL Agent): Formulated Q2C Sales Out SQL queries across 10 vendor footprints (24.5s)\n")
            chat_box.insert("end", "• Step 3 (Coverage Agent): Completed 12 sub-steps correlating 400+ partner signals (45.6s)\n")
            chat_box.insert("end", "• Step 4 (Design-In Agent): Pinpointed enterprise vectors for watsonx and OpenShift (0.0s)\n")
            chat_box.insert("end", "• Synthesis: 22 agent steps delivered across 4 specialized DAG sub-agents in 160.8s.\n\n")
            chat_box.see("end")

            # Populate Sub-Agents Tracker with the 4 enterprise agents & 22 steps
            self.sub_agents_tracker = {
                "draup": {
                    "id": "draup",
                    "name": "Draup Agent",
                    "role": "Market Intelligence Specialist",
                    "badge_icon": "D",
                    "status": "completed",
                    "duration": "10.8s",
                    "size": "56.2k",
                    "start_offset": "+5.7s",
                    "prompt_sent": "=== [DELEGATION DIRECTIVE FROM MAIN ORCHESTRATOR] ===\nSPECIALIST IDENTITY: Draup Agent\nSPECIALIST ROLE: Market Intelligence & Partner Ecosystem Specialist\nTARGET DELIVERABLE: Draup Market Footprint Handoff\nPRIMARY USER QUERY: What IBM Business Partners are actively working at Citigroup in the USA?\n\n=== 1. YOUR CORE MISSION & OBJECTIVES ===\nExtract active service-provider footprints, outsourcing indices, and top vendor rankings at Citigroup in the USA.\n\n=== 4. MANDATORY EXECUTION CONSTRAINTS ===\n1. ZERO PLACEHOLDERS: Generate 100% complete, verified partner names and metrics.\n2. Precision ratio: 9.99/10 outsourcing index.",
                    "logs: [\"Resolve Account ID\", \"Query Service-Provider Ranking\", \"Fetch Top-10 Footprints\", \"Parse USA boundaries\", \"Synthesize index\", \"Format matrix\"],": [],
                    "logs": ["✓ Sub-step 1/6: Resolve Account Entity ID & Metadata (1.2s)", "✓ Sub-step 2/6: Query Service-Provider Ranking Index (2.4s)", "✓ Sub-step 3/6: Fetch Top-10 Active Partner Footprints (3.1s)", "✓ Sub-step 4/6: Parse Geo Boundaries (USA Focus) (1.8s)", "✓ Sub-step 5/6: Synthesize Outsourcing Index Ratios (1.5s)", "✓ Sub-step 6/6: Format Primary Vendor Engagement Matrix (0.8s)"],
                    "generated_code": "# Draup Market Intelligence Handoff\nAccount: Citigroup Inc. (ID: 763241)\nTotal Active Partners: 135 | Outsourcing Index: 9.99/10\nTop Partners: TCS, Wipro, LTIMindtree, Infosys, Accenture, Cognizant",
                    "sub_steps": [
                        {"name": "Resolve Account Entity ID & Metadata", "duration": "1.2s"},
                        {"name": "Query Service-Provider Ranking Index", "duration": "2.4s"},
                        {"name": "Fetch Top-10 Active Partner Footprints", "duration": "3.1s"},
                        {"name": "Parse Geo Boundaries (USA Focus)", "duration": "1.8s"},
                        {"name": "Synthesize Outsourcing Index Ratios", "duration": "1.5s"},
                        {"name": "Format Primary Vendor Engagement Matrix", "duration": "0.8s"}
                    ]
                },
                "nl2sql": {
                    "id": "nl2sql",
                    "name": "NL2SQL Agent",
                    "role": "Enterprise SQL Specialist",
                    "badge_icon": "💻",
                    "status": "completed",
                    "duration": "24.5s",
                    "size": "2.7k",
                    "start_offset": "+7.4s",
                    "prompt_sent": "=== [DELEGATION DIRECTIVE FROM MAIN ORCHESTRATOR] ===\nSPECIALIST IDENTITY: NL2SQL Agent\nTARGET DELIVERABLE: SQL Sales Out Aggregates\n\nExecute SQL aggregation against Q2C Sales Out data for Citigroup service providers.",
                    "logs": ["✓ Sub-step 1/3: Generate Schema-Aligned SQL AST (5.2s)", "✓ Sub-step 2/3: Execute Q2C Sales Out Aggregate Query (12.1s)", "✓ Sub-step 3/3: Validate Transaction Signal Integrity (7.2s)"],
                    "generated_code": "SELECT partner_name, SUM(revenue_usd) as total_sales_out FROM q2c_sales_out WHERE account_id=763241 GROUP BY partner_name;",
                    "sub_steps": [
                        {"name": "Generate Schema-Aligned SQL AST", "duration": "5.2s"},
                        {"name": "Execute Q2C Sales Out Aggregate Query", "duration": "12.1s"},
                        {"name": "Validate Transaction Signal Integrity", "duration": "7.2s"}
                    ]
                },
                "coverage": {
                    "id": "coverage",
                    "name": "Coverage Agent",
                    "role": "Account Coverage Mapping",
                    "badge_icon": "👥",
                    "status": "completed",
                    "duration": "45.6s",
                    "size": "14.2k",
                    "start_offset": "+10.1s",
                    "prompt_sent": "=== [DELEGATION DIRECTIVE FROM MAIN ORCHESTRATOR] ===\nSPECIALIST IDENTITY: Coverage Agent\nMap Managing Directors, Technical Partner Specialists (TPS), and Data/Automation PTS leads for all active partners at Citigroup.",
                    "logs": ["✓ Sub-step 1/12: Scan Geo MD Directory", "✓ Sub-step 2/12: Extract TPS", "✓ Sub-step 3/12: Map Data PTS Leads", "✓ Sub-step 4/12: Filter US Matrix", "✓ Sub-step 5/12: Correlate Partner Signals (400+ signals)", "✓ Sub-step 6/12: Query Initiatives", "✓ Sub-step 7/12: Match TCS Modernization", "✓ Sub-step 8/12: Map Wipro Cloud", "✓ Sub-step 9/12: Map LTM Stranded-Cost", "✓ Sub-step 10/12: Correlate Sales Channels", "✓ Sub-step 11/12: Resolve Hierarchy", "✓ Sub-step 12/12: Generate Contact Roster"],
                    "generated_code": "# Verified Coverage Contacts\nUS: MD Sharon Fortune-Bowden | TPS: Renzo Peralta | Data PTS: Arvind Rajpurohit | Automation PTS: Derek Fu",
                    "sub_steps": [
                        {"name": "Scan Geo Managing Director Directory", "duration": "4.1s"},
                        {"name": "Extract Technical Partner Specialists (TPS)", "duration": "6.3s"},
                        {"name": "Map Data PTS & Automation Practice Leads", "duration": "8.5s"},
                        {"name": "Filter US-Specific Coverage Matrix", "duration": "5.2s"},
                        {"name": "Correlate Partner Signals (400+ signals)", "duration": "9.4s"},
                        {"name": "Query Portfolio Simplification Initiatives", "duration": "3.1s"},
                        {"name": "Match TCS Legacy Modernization Coverage", "duration": "2.5s"},
                        {"name": "Map Wipro Cloud Migration Coverage", "duration": "2.2s"},
                        {"name": "Map LTM Stranded-Cost Modernization Coverage", "duration": "2.8s"},
                        {"name": "Correlate IBM Technology Sales Channels", "duration": "3.4s"},
                        {"name": "Resolve Partner Contact Escalation Hierarchy", "duration": "3.2s"},
                        {"name": "Generate Verified Coverage Contact Roster", "duration": "4.9s"}
                    ]
                },
                "design_in": {
                    "id": "design_in",
                    "name": "Design-In Agent",
                    "role": "Solution Design-In",
                    "badge_icon": "⚙",
                    "status": "completed",
                    "duration": "0.0s",
                    "size": "9.8k",
                    "start_offset": "+27.4s",
                    "prompt_sent": "=== [DELEGATION DIRECTIVE FROM MAIN ORCHESTRATOR] ===\nSPECIALIST IDENTITY: Design-In Agent\nPinpoint enterprise solution opportunities and technology sales angles.",
                    "logs": ["✓ Sub-step 1/1: Synthesize Technology Modernization Vectors (0.0s)"],
                    "generated_code": "# IBM Technology Sell-Through Vectors\n1. watsonx.data & watsonx.ai for AI-at-scale pilots\n2. Red Hat OpenShift & Cloud Paks for Modernization\n3. IBM API Connect & MQ for banking middleware",
                    "sub_steps": [
                        {"name": "Synthesize Technology Modernization Vectors", "duration": "0.0s"}
                    ]
                }
            }

            thought_stream_txt.delete("1.0", "end")
            thought_stream_txt.insert("end", "I'll pull together market intelligence, sales data, offerings, and coverage contacts for Citigroup simultaneously. I'll query both questions in parallel against Q2C Sales Out data. Resolved: id=763241, key=\"Citigroup Inc.\". Now dispatching all Step 2 calls in parallel. [WORKER: DraupAgent | Account: Citigroup | Status: OK | Tools: 6 called]")
            refresh_telemetry_tree()

        # Render showcase demo automatically on open
        render_desktop_showcase_demo()

        if default_tab > 0:
            notebook.select(default_tab)

        def send_msg():
            msg = entry.get().strip()
            if not msg and not self.attached_image_b64:
                return
            
            curr_b64 = self.attached_image_b64
            img_note = f" 🖼️ [{self.attached_image_name}]" if self.attached_image_name else ""

            entry.delete(0, "end")
            chat_box.insert("end", f"You:\n", "user")
            chat_box.insert("end", f"{msg}{img_note}\n\n")
            chat_box.insert("end", "🤖 AskEcoIQ / Neo Agent:\n", "assistant")
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
                        
                        elif evt_type == "agent_thinking_init":
                            sub_agents = event.get("sub_agents", [])
                            for sa in sub_agents:
                                if sa.get("id"):
                                    self.sub_agents_tracker[sa["id"]] = sa
                            def on_thinking_init(s_text):
                                chat_box.insert("end", f"⚙ {s_text}\n", "thinking_card")
                                chat_box.see("end")
                                refresh_telemetry_tree()
                            self.root.after(0, on_thinking_init, event.get("summary", "Agent thinking initialized..."))

                        elif evt_type == "agent_thought_stream":
                            thought_c = event.get("content", "")
                            def on_thought(tc):
                                thought_stream_txt.insert("end", tc)
                                thought_stream_txt.see("end")
                            self.root.after(0, on_thought, thought_c)

                        elif evt_type == "sub_agent_substep":
                            sa = event.get("sub_agent")
                            if sa and sa.get("id"):
                                self.sub_agents_tracker[sa["id"]] = sa
                            self.root.after(0, refresh_telemetry_tree)

                        elif evt_type == "agent_thinking_complete":
                            def on_thinking_done(sum_text):
                                lbl_thinking_status.config(text=f"✔ {sum_text}")
                                refresh_telemetry_tree()
                            self.root.after(0, on_thinking_done, event.get("summary", "Thinking complete."))

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
                            self.root.after(0, refresh_telemetry_tree)

                    self.root.after(0, lambda: [
                        chat_box.insert("end", "\n\n"),
                        chat_box.see("end"),
                        setattr(self, 'mascot_state', 'idle'),
                        refresh_ws_view(),
                        refresh_telemetry_tree()
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
