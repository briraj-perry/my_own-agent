"""Unit tests for extract_multi_file_blocks and is_web_intent helpers."""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent.core import extract_multi_file_blocks, is_web_intent



class TestHelpers(unittest.TestCase):
    """Test suite for helper extraction and intent functions."""

    def test_is_web_intent(self):
        self.assertTrue(is_web_intent("create a web app with buttons"))
        self.assertFalse(is_web_intent("write a python script"))
        self.assertTrue(is_web_intent("make an interactive page with buttons"))
        self.assertTrue(is_web_intent("build me a dashboard"))
        self.assertFalse(is_web_intent("create a calculator"))

    def test_extract_multi_file_blocks(self):
        test_response = """Here is your web app:

### FILE: index.html
```html
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Hello</h1><button id="btn">Click</button></body>
</html>
```

### FILE: style.css
```css
body { background: #0a0a0f; color: white; }
button { padding: 10px; border-radius: 8px; }
```

### FILE: script.js
```javascript
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btn').addEventListener('click', () => {
        console.log('Button clicked!');
    });
});
```
"""
        result = extract_multi_file_blocks(test_response)
        self.assertIn("index.html", result)
        self.assertIn("style.css", result)
        self.assertIn("script.js", result)
        self.assertIn("<h1>Hello</h1>", result["index.html"])
        self.assertIn("#0a0a0f", result["style.css"])
        self.assertIn("addEventListener", result["script.js"])

    def test_alt_file_format(self):
        test_alt = """
--- FILE: app.html ---
```html
<div>Alt format</div>
```
"""
        result_alt = extract_multi_file_blocks(test_alt)
        self.assertIn("app.html", result_alt)


if __name__ == "__main__":
    unittest.main()

