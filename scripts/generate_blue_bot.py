import os
from PIL import Image

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "assets")
MASCOTS_DIR = os.path.join(ASSETS_DIR, "mascots")
os.makedirs(MASCOTS_DIR, exist_ok=True)

def create_blue_bot(src_name, out_name):
    src_path = os.path.join(ASSETS_DIR, src_name)
    out_path = os.path.join(MASCOTS_DIR, out_name)
    
    img = Image.open(src_path).convert("RGBA")
    data = img.getdata()
    
    # Corner background color
    bg_r, bg_g, bg_b = data[0][0], data[0][1], data[0][2]
    
    new_pixels = []
    for item in data:
        r, g, b, a = item
        # If dark background pixel, make 100% transparent
        if abs(r - bg_r) < 30 and abs(g - bg_g) < 30 and abs(b - bg_b) < 30:
            new_pixels.append((0, 0, 0, 0))
        else:
            # Shift purple hues to electric blue / cyan
            # If purple body (r > 80 and b > 120 and g < r):
            if r > 60 and b > 120 and r < b:
                # Electric blue hue shift
                new_r = int(r * 0.3)
                new_g = int(g * 0.7 + 100)
                new_b = min(255, int(b * 1.1 + 40))
                new_pixels.append((new_r, new_g, new_b, a))
            else:
                new_pixels.append((r, g, b, a))
                
    img.putdata(new_pixels)
    img.save(out_path, "PNG")
    print(f"Created Classic Blue Bot: {out_path}")

create_blue_bot("neo-mascot-idle.png", "blue_bot_idle.png")
create_blue_bot("neo-mascot-coding.png", "blue_bot_coding.png")
