"""Test mascot theme loading and transparent image assets."""
import os
from desktop_mascot import MASCOT_THEMES

def test_mascot_assets():
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "assets", "mascots")
    assert os.path.exists(assets_dir), "Mascots directory must exist"
    
    for key, theme in MASCOT_THEMES.items():
        idle_file = os.path.join(assets_dir, theme["idle"])
        coding_file = os.path.join(assets_dir, theme["coding"])
        assert os.path.exists(idle_file), f"Missing idle image for {key}: {idle_file}"
        assert os.path.exists(coding_file), f"Missing coding image for {key}: {coding_file}"
        print(f"✅ Theme '{key}' ({theme['name']}): Assets verified")

if __name__ == "__main__":
    test_mascot_assets()
    print("\n🎉 Mascot assets verification test passed!")
