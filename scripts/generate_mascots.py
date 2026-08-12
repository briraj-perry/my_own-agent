import os
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "assets")
MASCOTS_DIR = os.path.join(ASSETS_DIR, "mascots")
os.makedirs(MASCOTS_DIR, exist_ok=True)

def remove_background(img_path, out_path):
    """Removes dark background pixels around the mascot image to make it 100% transparent."""
    img = Image.open(img_path).convert("RGBA")
    data = img.getdata()
    
    # Get corner pixel as reference background color
    bg_r, bg_g, bg_b = data[0][0], data[0][1], data[0][2]
    
    new_data = []
    for item in data:
        r, g, b, a = item
        # If pixel color is close to the dark background color, make it transparent
        if abs(r - bg_r) < 25 and abs(g - bg_g) < 25 and abs(b - bg_b) < 25:
            new_data.append((0, 0, 0, 0))
        else:
            new_data.append((r, g, b, a))
            
    img.putdata(new_data)
    img.save(out_path, "PNG")
    print(f"Cleaned background: {out_path}")

# 1. Clean existing mascot images
idle_src = os.path.join(ASSETS_DIR, "neo-mascot-idle.png")
coding_src = os.path.join(ASSETS_DIR, "neo-mascot-coding.png")

if os.path.exists(idle_src):
    remove_background(idle_src, os.path.join(MASCOTS_DIR, "pixel_bot_idle.png"))
if os.path.exists(coding_src):
    remove_background(coding_src, os.path.join(MASCOTS_DIR, "pixel_bot_coding.png"))

# Helper to create mascot canvas
def create_canvas(w=160, h=160):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))

# 2. Generate Cyber Cat Mascot (Idle & Coding)
def draw_cyber_cat(is_coding=False):
    img = create_canvas()
    draw = ImageDraw.Draw(img)
    cx, cy = 80, 80
    
    # Glow aura
    aura_color = (0, 245, 212, 40) if not is_coding else (247, 37, 133, 50)
    draw.ellipse([cx - 50, cy - 45, cx + 50, cy + 45], fill=aura_color)
    
    # Cat Ears
    draw.polygon([(cx - 35, cy - 25), (cx - 48, cy - 65), (cx - 15, cy - 38)], fill=(123, 44, 191, 255), outline=(0, 245, 212, 255), width=2)
    draw.polygon([(cx + 35, cy - 25), (cx + 48, cy - 65), (cx + 15, cy - 38)], fill=(123, 44, 191, 255), outline=(0, 245, 212, 255), width=2)
    
    # Inner Ear Glow
    draw.polygon([(cx - 32, cy - 30), (cx - 42, cy - 55), (cx - 20, cy - 38)], fill=(0, 245, 212, 200))
    draw.polygon([(cx + 32, cy - 30), (cx + 42, cy - 55), (cx + 20, cy - 38)], fill=(0, 245, 212, 200))
    
    # Head Base
    draw.ellipse([cx - 40, cy - 40, cx + 40, cy + 30], fill=(20, 15, 38, 255), outline=(157, 78, 221, 255), width=3)
    
    # Cyber Visor (Eyes)
    draw.rounded_rectangle([cx - 30, cy - 20, cx + 30, cy + 10], radius=10, fill=(10, 8, 20, 255), outline=(0, 245, 212, 255), width=2)
    
    if not is_coding:
        # Cat Eyes (Neon Cyan Slits)
        draw.ellipse([cx - 20, cy - 12, cx - 8, cy + 2], fill=(0, 245, 212, 255))
        draw.ellipse([cx + 8, cy - 12, cx + 20, cy + 2], fill=(0, 245, 212, 255))
        draw.rectangle([cx - 15, cy - 12, cx - 13, cy + 2], fill=(10, 8, 20, 255))
        draw.rectangle([cx + 13, cy - 12, cx + 15, cy + 2], fill=(10, 8, 20, 255))
    else:
        # Coding Visor Display: "^ ^"
        draw.line([(cx - 22, cy - 2), (cx - 15, cy - 12), (cx - 8, cy - 2)], fill=(247, 37, 133, 255), width=3)
        draw.line([(cx + 8, cy - 2), (cx + 15, cy - 12), (cx + 22, cy - 2)], fill=(247, 37, 133, 255), width=3)
        # Whiskers
        draw.line([(cx - 38, cy), (cx - 50, cy - 5)], fill=(0, 245, 212, 255), width=2)
        draw.line([(cx - 38, cy + 8), (cx - 52, cy + 10)], fill=(0, 245, 212, 255), width=2)
        draw.line([(cx + 38, cy), (cx + 50, cy - 5)], fill=(0, 245, 212, 255), width=2)
        draw.line([(cx + 38, cy + 8), (cx + 52, cy + 10)], fill=(0, 245, 212, 255), width=2)
    
    # Body
    draw.ellipse([cx - 25, cy + 20, cx + 25, cy + 65], fill=(30, 20, 55, 255), outline=(157, 78, 221, 255), width=2)
    # Chest Emblem
    draw.polygon([(cx, cy + 30), (cx - 8, cy + 42), (cx + 8, cy + 42)], fill=(0, 245, 212, 255))
    
    # Paws
    draw.ellipse([cx - 20, cy + 58, cx - 6, cy + 68], fill=(157, 78, 221, 255))
    draw.ellipse([cx + 6, cy + 58, cx + 20, cy + 68], fill=(157, 78, 221, 255))
    
    return img

cat_idle = draw_cyber_cat(False)
cat_idle.save(os.path.join(MASCOTS_DIR, "cyber_cat_idle.png"))
cat_coding = draw_cyber_cat(True)
cat_coding.save(os.path.join(MASCOTS_DIR, "cyber_cat_coding.png"))

# 3. Generate Neon Dragon Mascot (Idle & Coding)
def draw_neon_dragon(is_coding=False):
    img = create_canvas()
    draw = ImageDraw.Draw(img)
    cx, cy = 80, 80
    
    # Glow
    glow = (16, 185, 129, 45) if not is_coding else (0, 245, 212, 60)
    draw.ellipse([cx - 52, cy - 52, cx + 52, cy + 52], fill=glow)
    
    # Wings
    draw.polygon([(cx - 25, cy - 10), (cx - 65, cy - 40), (cx - 45, cy + 10)], fill=(6, 95, 70, 255), outline=(16, 185, 129, 255), width=2)
    draw.polygon([(cx + 25, cy - 10), (cx + 65, cy - 40), (cx + 45, cy + 10)], fill=(6, 95, 70, 255), outline=(16, 185, 129, 255), width=2)
    
    # Dragon Horns
    draw.polygon([(cx - 20, cy - 30), (cx - 32, cy - 60), (cx - 10, cy - 40)], fill=(245, 158, 11, 255))
    draw.polygon([(cx + 20, cy - 30), (cx + 32, cy - 60), (cx + 10, cy - 40)], fill=(245, 158, 11, 255))
    
    # Dragon Head
    draw.ellipse([cx - 35, cy - 40, cx + 35, cy + 20], fill=(4, 120, 87, 255), outline=(16, 185, 129, 255), width=3)
    
    # Eyes
    if not is_coding:
        draw.ellipse([cx - 22, cy - 18, cx - 8, cy - 4], fill=(245, 158, 11, 255))
        draw.ellipse([cx + 8, cy - 18, cx + 22, cy - 4], fill=(245, 158, 11, 255))
        draw.rectangle([cx - 16, cy - 18, cx - 14, cy - 4], fill=(0, 0, 0, 255))
        draw.rectangle([cx + 14, cy - 18, cx + 16, cy - 4], fill=(0, 0, 0, 255))
    else:
        # Glowing Cyber Goggles
        draw.rounded_rectangle([cx - 26, cy - 20, cx + 26, cy - 2], radius=6, fill=(0, 245, 212, 255), outline=(255, 255, 255, 255), width=2)
        draw.text((cx - 18, cy - 18), "⚡⚡", fill=(0, 0, 0, 255))
        
    # Cute Snout & Nostrils
    draw.ellipse([cx - 18, cy + 2, cx + 18, cy + 18], fill=(6, 95, 70, 255))
    draw.ellipse([cx - 8, cy + 8, cx - 4, cy + 12], fill=(0, 0, 0, 255))
    draw.ellipse([cx + 4, cy + 8, cx + 8, cy + 12], fill=(0, 0, 0, 255))
    
    # Body & Belly
    draw.ellipse([cx - 25, cy + 15, cx + 25, cy + 65], fill=(4, 120, 87, 255), outline=(16, 185, 129, 255), width=2)
    draw.ellipse([cx - 14, cy + 25, cx + 14, cy + 55], fill=(245, 158, 11, 200))
    
    return img

dragon_idle = draw_neon_dragon(False)
dragon_idle.save(os.path.join(MASCOTS_DIR, "neon_dragon_idle.png"))
dragon_coding = draw_neon_dragon(True)
dragon_coding.save(os.path.join(MASCOTS_DIR, "neon_dragon_coding.png"))

# 4. Generate Cosmic Orb Mascot (Idle & Coding)
def draw_cosmic_orb(is_coding=False):
    img = create_canvas()
    draw = ImageDraw.Draw(img)
    cx, cy = 80, 80
    
    # Outer Orbital Rings
    ring_color = (0, 245, 212, 180) if not is_coding else (247, 37, 133, 200)
    draw.ellipse([cx - 60, cy - 25, cx + 60, cy + 25], outline=ring_color, width=3)
    draw.ellipse([cx - 25, cy - 60, cx + 25, cy + 60], outline=(157, 78, 221, 180), width=2)
    
    # Floating Satellites
    draw.ellipse([cx - 55, cy - 12, cx - 43, cy], fill=(0, 245, 212, 255))
    draw.ellipse([cx + 43, cy, cx + 55, cy + 12], fill=(247, 37, 133, 255))
    
    # Core Crystal Orb
    core_color = (30, 25, 60, 255)
    draw.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill=core_color, outline=(0, 245, 212, 255), width=3)
    
    # Face Screen / Core Matrix
    draw.ellipse([cx - 25, cy - 25, cx + 25, cy + 25], fill=(10, 8, 25, 255), outline=(157, 78, 221, 255), width=2)
    
    if not is_coding:
        # Star Pupil
        draw.text((cx - 14, cy - 14), "✦ ✦", fill=(0, 245, 212, 255))
    else:
        # Glowing Matrix Sparkles
        draw.text((cx - 18, cy - 14), "⚙ ⚙", fill=(247, 37, 133, 255))
        
    return img

orb_idle = draw_cosmic_orb(False)
orb_idle.save(os.path.join(MASCOTS_DIR, "cosmic_orb_idle.png"))
orb_coding = draw_cosmic_orb(True)
orb_coding.save(os.path.join(MASCOTS_DIR, "cosmic_orb_coding.png"))

print("🎉 All 4 Mascots successfully generated with 100% TRANSPARENT backgrounds in ui/assets/mascots/!")
