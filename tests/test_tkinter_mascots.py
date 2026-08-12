"""Test Tkinter PhotoImage creation for all 4 mascot themes."""
import os
import tkinter as tk
from desktop_mascot import MASCOT_THEMES

def test_tkinter_photos():
    root = tk.Tk()
    root.withdraw() # Hide test window
    
    mascot_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "assets", "mascots")
    
    loaded_images = {}
    for key, theme in MASCOT_THEMES.items():
        idle_path = os.path.join(mascot_dir, theme["idle"])
        coding_path = os.path.join(mascot_dir, theme["coding"])
        
        img_idle = tk.PhotoImage(file=idle_path)
        img_coding = tk.PhotoImage(file=coding_path)
        
        assert img_idle.width() > 0 and img_idle.height() > 0, f"Idle image {key} empty"
        assert img_coding.width() > 0 and img_coding.height() > 0, f"Coding image {key} empty"
        
        loaded_images[key] = (img_idle, img_coding)
        print(f"✅ Tkinter PhotoImage loaded for '{key}': {img_idle.width()}x{img_idle.height()}px")
        
    root.destroy()
    print("\n🎉 Tkinter PhotoImage loading test passed!")

if __name__ == "__main__":
    test_tkinter_photos()
