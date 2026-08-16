"""Unit tests for code formatting, unescaping, and component auto-synthesis."""

import os
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.code_formatter import (
    unescape_string_literals,
    format_json_code,
    format_css_code,
    format_javascript_code,
    format_code_content,
    auto_generate_missing_components,
)
from agent.core import extract_multi_file_blocks
from tools import file_tools


class TestCodeFormatter(unittest.TestCase):
    """Test suite verifying code formatting and component auto-generation."""

    def test_unescape_string_literals(self):
        """Test unescaping of escaped string literals from LLM responses."""
        escaped = '"use client";\\nimport React from "react";\\nexport default function Home() {\\n  return <div>Home</div>;\\n}'
        unescaped = unescape_string_literals(escaped)
        self.assertIn('\n', unescaped)
        self.assertNotIn('\\n', unescaped)
        self.assertIn('export default function Home()', unescaped)

    def test_format_json_code(self):
        """Test JSON pretty printing."""
        single_line_json = '{"name":"my-app","version":"0.1.0","dependencies":{"react":"^18.2.0","next":"^14.0.0"}}'
        formatted = format_json_code(single_line_json)
        self.assertIn('\n', formatted)
        self.assertIn('  "name": "my-app"', formatted)
        self.assertIn('  "dependencies": {', formatted)

    def test_format_css_code(self):
        """Test CSS multi-line formatting."""
        single_line_css = '@import "tailwindcss/base"; @import "tailwindcss/components"; body { background-color: #090d16; color: #fff; }'
        formatted = format_css_code(single_line_css)
        self.assertIn('@import "tailwindcss/base";\n', formatted)
        self.assertIn('body {', formatted)
        self.assertIn('background-color: #090d16;', formatted)

    def test_format_javascript_code(self):
        """Test JS/JSX unminification and line separation."""
        single_line_jsx = '"use client"; import React, { useState } from "react"; import Navbar from "@/components/Navbar"; export default function Home() { const [count, setCount] = useState(0); return (<main className="p-8"><Navbar /><h1>Title</h1></main>); }'
        formatted = format_javascript_code(single_line_jsx)
        self.assertTrue(formatted.startswith('"use client";\n\n'))
        self.assertIn('import React, { useState } from "react";\n', formatted)
        self.assertIn('import Navbar from "@/components/Navbar";\n', formatted)
        self.assertIn('export default function Home()', formatted)
        self.assertIn('<Navbar />', formatted)

    def test_auto_generate_missing_components(self):
        """Test auto-synthesis of missing Next.js imported components."""
        page_code = '''"use client";
import React from "react";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import DashboardPreview from "@/components/DashboardPreview";

export default function Home() {
  return (
    <main>
      <Navbar />
      <Hero />
      <DashboardPreview />
    </main>
  );
}'''
        parsed = {"app/page.jsx": page_code}
        resolved = auto_generate_missing_components(parsed)
        self.assertIn("app/page.jsx", resolved)
        self.assertIn("components/Navbar.jsx", resolved)
        self.assertIn("components/Hero.jsx", resolved)
        self.assertIn("components/DashboardPreview.jsx", resolved)
        self.assertIn("export default function Navbar", resolved["components/Navbar.jsx"])
        self.assertIn("export default function Hero", resolved["components/Hero.jsx"])
        self.assertIn("export default function DashboardPreview", resolved["components/DashboardPreview.jsx"])

    def test_extract_multi_file_blocks_with_formatter(self):
        """Test that extract_multi_file_blocks produces clean multi-line formatted files."""
        raw_llm_response = '''Here is your Next.js application:

### FILE: package.json
```json
{"name":"test-app","version":"0.1.0","private":true}
```

### FILE: app/page.jsx
```jsx
"use client"; import React from "react"; import Navbar from "@/components/Navbar"; export default function Home() { return <Navbar />; }
```
'''
        files = extract_multi_file_blocks(raw_llm_response)
        self.assertIn("package.json", files)
        self.assertIn("app/page.jsx", files)
        # Verify JSON is formatted multi-line
        self.assertIn('\n', files["package.json"])
        self.assertIn('  "name": "test-app"', files["package.json"])
        # Verify JSX is formatted multi-line
        self.assertIn('\n', files["app/page.jsx"])
        self.assertIn('import Navbar from "@/components/Navbar";', files["app/page.jsx"])


if __name__ == "__main__":
    unittest.main()
