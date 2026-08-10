import os
import sys
import json
import asyncio
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import urllib.parse

from agent.core import NeoAgentCore
from tools.screen_perception import ScreenPerceptionEngine

class FloatingMascotApp:
    """Desktop Floating Mascot Companion Overlay for Windows with Real AI Streaming."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("my_neo-agent Desktop Mascot")
        
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
        mascot_x = screen_w - 180
        mascot_y = screen_h - 220
        self.root.geometry(f"160x170+{mascot_x}+{mascot_y}")

        # Dragging state
        self.start_x = 0
        self.start_y = 0

        # Agent & Screen Engine
        self.agent = NeoAgentCore()
        self.screen_engine = ScreenPerceptionEngine()

        # Create Canvas for pixel-art mascot rendering
        self.canvas = tk.Canvas(self.root, width=160, height=170, bg=self.trans_color, highlightthickness=0)
        self.canvas.pack()

        # Canvas Click & Drag Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", self.show_context_menu)

        # Animation ticker
        self.tick = 0
        self.mascot_state = "idle" # idle, thinking, permission, executing, success
        self.chat_window = None

        # Build Context Menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="💬 Ask Neo Mascot", command=self.open_chat_dialog)
        self.context_menu.add_command(label="👁️ See My Screen", command=self.perceive_screen_action)
        self.context_menu.add_command(label="🌐 Open Web Dashboard", command=self.open_dashboard_browser)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="❌ Exit Mascot", command=self.root.destroy)

        # Start animation loop
        self.animate()

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
        self.canvas.delete("all")
        self.tick += 1
        
        # Vertical floating bob
        import math
        bob_y = int(math.sin(self.tick * 0.1) * 4)

        # Mascot center coordinates
        cx = 80
        cy = 75 + bob_y

        # Aura Glow
        glow_color = "#9d4edd"
        if self.mascot_state == "thinking":
            glow_color = "#00f5d4"
        elif self.mascot_state == "permission":
            glow_color = "#f72585"
        elif self.mascot_state == "executing":
            glow_color = "#4cc9f0"
        elif self.mascot_state == "success":
            glow_color = "#00f5d4"

        self.canvas.create_oval(cx - 50, cy - 45, cx + 50, cy + 45, fill=glow_color, outline="", stipple="gray25")

        # Head / Body Cloud shape (Purple pixel robot)
        body_color = "#7b2cbf"
        self.canvas.create_oval(cx - 42, cy - 38, cx + 42, cy + 32, fill=body_color, outline="#3c096c", width=3)
        self.canvas.create_oval(cx - 28, cy - 48, cx + 28, cy - 10, fill=body_color, outline="#3c096c", width=2)
        
        # Legs
        self.canvas.create_rectangle(cx - 20, cy + 28, cx - 8, cy + 44, fill=body_color, outline="#3c096c", width=2)
        self.canvas.create_rectangle(cx + 8, cy + 28, cx + 20, cy + 44, fill=body_color, outline="#3c096c", width=2)

        # Screen Monitor Face
        self.canvas.create_rectangle(cx - 26, cy - 22, cx + 26, cy + 12, fill="#10002b", outline="#e0aaff", width=2)

        # Face Expression (e.g. > _ cursor face)
        face_text = "> _"
        if self.mascot_state == "thinking":
            face_text = "> ~"
        elif self.mascot_state == "permission":
            face_text = "! ?"
        elif self.mascot_state == "executing":
            face_text = "> >"
        elif self.mascot_state == "success":
            face_text = "^ ^"

        self.canvas.create_text(cx, cy - 5, text=face_text, fill="#00f5d4", font=("Courier", 14, "bold"))

        # Chest Emblem (> -)
        self.canvas.create_text(cx, cy + 20, text="> -", fill="#ffffff", font=("Courier", 10, "bold"))

        # Status text below mascot
        self.canvas.create_text(cx, 155, text="Neo Mascot", fill="#e0aaff", font=("Segoe UI", 9, "bold"))

    def animate(self):
        self.draw_mascot()
        self.root.after(50, self.animate)

    def perceive_screen_action(self):
        self.mascot_state = "thinking"
        res = self.screen_engine.capture_screen()
        if res["status"] == "success":
            messagebox.showinfo("Desktop Perception", f"👁️ Neo Mascot captured your desktop screen!\n\nSaved image: {res['filepath']}\nVision Model: {self.agent.VISION_MODEL}\n\nAsk Neo: 'What is on my screen?'")
        else:
            messagebox.showerror("Perception Error", res.get("message", "Screen capture failed"))
        self.mascot_state = "idle"

    def open_dashboard_browser(self):
        import webbrowser
        webbrowser.open("http://127.0.0.1:8000")

    def open_chat_dialog(self):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.lift()
            return

        self.chat_window = tk.Toplevel(self.root)
        self.chat_window.title("Ask Neo Mascot")
        self.chat_window.geometry("440x520")
        self.chat_window.attributes("-topmost", True)
        self.chat_window.config(bg="#0d0b18")

        # Chat display area
        chat_box = tk.Text(self.chat_window, bg="#161224", fg="#ffffff", font=("Segoe UI", 10), wrap="word", highlightthickness=0)
        chat_box.pack(fill="both", expand=True, padx=10, pady=10)
        chat_box.insert("end", f"🤖 Neo Mascot: Hello! Ask me anything or ask me to 'look at my screen' (using {self.agent.VISION_MODEL}).\n\n")

        # Entry frame
        frame = tk.Frame(self.chat_window, bg="#0d0b18")
        frame.pack(fill="x", padx=10, pady=(0, 10))

        entry = tk.Entry(frame, bg="#241e38", fg="#00f5d4", font=("Segoe UI", 11), insertbackground="#00f5d4")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        def capture_now():
            self.mascot_state = "thinking"
            res = self.screen_engine.capture_screen()
            if res["status"] == "success":
                chat_box.insert("end", f"📸 *Screen captured! Ask me: 'What is on my screen?' (analyzed via {self.agent.VISION_MODEL})*\n")
                chat_box.see("end")
            self.mascot_state = "idle"

        cap_btn = tk.Button(frame, text="📸", bg="#241e38", fg="#00f5d4", font=("Segoe UI", 10), command=capture_now)
        cap_btn.pack(side="left", padx=(0, 5))

        def send_msg():
            msg = entry.get().strip()
            if not msg:
                return
            entry.delete(0, "end")
            chat_box.insert("end", f"You: {msg}\n")
            chat_box.insert("end", "🤖 Neo Mascot: ")
            chat_box.see("end")

            self.mascot_state = "thinking"

            def stream_ai_worker():
                async def run_stream():
                    async for event in self.agent.stream_response(msg):
                        evt_type = event.get("type")
                        if evt_type == "state":
                            st = event.get("mascot_state", "thinking")
                            self.root.after(0, setattr, self, 'mascot_state', st)
                        elif evt_type == "token":
                            token = event.get("content", "")
                            def append_token(t):
                                chat_box.insert("end", t)
                                chat_box.see("end")
                            self.root.after(0, append_token, token)
                        elif evt_type == "permission_request":
                            req_id = event.get("id")
                            def handle_perm(r_id, action_str):
                                res = messagebox.askyesno("Permission Required", f"Agent request permission to:\n{action_str}")
                                self.agent.resolve_permission(r_id, res)
                            self.root.after(0, handle_perm, req_id, event.get("action"))

                    self.root.after(0, lambda: [
                        chat_box.insert("end", "\n\n"),
                        chat_box.see("end"),
                        setattr(self, 'mascot_state', 'idle')
                    ])

                asyncio.run(run_stream())

            threading.Thread(target=stream_ai_worker, daemon=True).start()

        send_btn = tk.Button(frame, text="Send", bg="#9d4edd", fg="#ffffff", font=("Segoe UI", 10, "bold"), command=send_msg)
        send_btn.pack(side="right")
        entry.bind("<Return>", lambda e: send_msg())

    def run(self):
        self.root.mainloop()

def launch_desktop_mascot():
    app = FloatingMascotApp()
    app.run()

if __name__ == "__main__":
    launch_desktop_mascot()
