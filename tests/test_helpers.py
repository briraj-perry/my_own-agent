"""Quick test for extract_multi_file_blocks and is_web_intent."""
from agent.core import extract_multi_file_blocks, is_web_intent

# Test is_web_intent
assert is_web_intent("create a web app with buttons") == True
assert is_web_intent("write a python script") == False
assert is_web_intent("make an interactive page with buttons") == True
assert is_web_intent("build me a dashboard") == True
assert is_web_intent("create a calculator") == False
print("✅ is_web_intent: All tests passed")

# Test extract_multi_file_blocks
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
print(f"Files found: {list(result.keys())}")
assert "index.html" in result, f"Missing index.html, got: {list(result.keys())}"
assert "style.css" in result, f"Missing style.css, got: {list(result.keys())}"
assert "script.js" in result, f"Missing script.js, got: {list(result.keys())}"
assert "<h1>Hello</h1>" in result["index.html"]
assert "#0a0a0f" in result["style.css"]
assert "addEventListener" in result["script.js"]
print("✅ extract_multi_file_blocks: All tests passed")

# Test the --- FILE: --- variant
test_alt = """
--- FILE: app.html ---
```html
<div>Alt format</div>
```
"""
result_alt = extract_multi_file_blocks(test_alt)
assert "app.html" in result_alt, f"Alt format failed, got: {list(result_alt.keys())}"
print("✅ extract_multi_file_blocks (alt format): Passed")

print("\n🎉 All helper function tests passed!")
