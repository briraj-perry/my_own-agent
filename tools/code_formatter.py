"""Code Formatter, Literal Unescaper, and Component Synthesizer for Neo & Claw Agents.

Ensures that all code generated across the multi-agent system is written to disk in
clean, properly indented, multi-line format with no escaped newlines (\\n) or single-line minification.
"""

import json
import os
import re
from typing import Dict, Any, Optional


def unescape_string_literals(code: str) -> str:
    """Unescapes literal \\n, \\t, \\r, \\" when code was emitted as an escaped string literal by an LLM."""
    if not code:
        return code
    real_newlines = code.count('\n')
    literal_newlines = code.count('\\n')
    # If there are very few real newlines but multiple literal \\n sequences,
    # or if literal \\n is dominant, unescape them.
    if (real_newlines <= 2 and literal_newlines >= 2) or (literal_newlines > real_newlines * 2 and literal_newlines >= 4):
        code = (
            code.replace('\\r\\n', '\n')
            .replace('\\n', '\n')
            .replace('\\t', '  ')
            .replace('\\"', '"')
            .replace("\\'", "'")
        )
    return code


def format_json_code(code: str) -> str:
    """Formats JSON code with standard 2-space indentation."""
    code = unescape_string_literals(code).strip()
    try:
        data = json.loads(code)
        return json.dumps(data, indent=2) + "\n"
    except Exception:
        return code + ("\n" if not code.endswith("\n") else "")


def format_css_code(code: str) -> str:
    """Formats CSS stylesheets into clean multi-line rules with 2-space indentation."""
    code = unescape_string_literals(code).strip()

    # Check if CSS is already well-formatted multi-line
    if code.count('\n') > 5 and not bool(re.search(r'}\s*[.#a-zA-Z]', code)):
        return code + ("\n" if not code.endswith("\n") else "")

    # Separate @import, @tailwind, @layer, and @apply directives
    code = re.sub(r'(@(?:import|tailwind|layer|apply)\s+[^;]+;)\s*', r'\1\n', code)

    # Format rule blocks
    code = re.sub(r'\s*{\s*', ' {\n  ', code)
    code = re.sub(r';\s*(?!})', ';\n  ', code)
    code = re.sub(r';?\s*}\s*', ';\n}\n\n', code)
    
    # Clean up empty lines
    code = re.sub(r'\n{3,}', '\n\n', code).strip() + "\n"
    return code


def format_javascript_code(code: str) -> str:
    """Formats JS/JSX/TS/TSX code with clean multi-line indentation, statement separation, and JSX linebreaks."""
    code = unescape_string_literals(code).strip()

    # 1. Handle "use client" / "use server" directives at the top
    use_directive = ""
    match_directive = re.match(r'^([\"\']use (?:client|server)[\"\'];?)\s*', code)
    if match_directive:
        use_directive = match_directive.group(1).rstrip(';') + ';\n\n'
        code = code[match_directive.end():].strip()

    # 2. Check if the code is already multi-line and not minified
    lines = [l for l in code.splitlines() if l.strip()]
    is_single_line = len(lines) <= 3 and len(code) > 80
    has_crammed_imports = bool(re.search(r'import\s+[^;]+;\s*import\s+', code))

    if not is_single_line and not has_crammed_imports:
        return use_directive + code + ("\n" if not code.endswith("\n") else "")

    # 3. Separate multiple import statements
    code = re.sub(r'(import\s+[^;]+;?)\s*(?=import\s+)', r'\1\n', code)
    code = re.sub(r'(import\s+[^;]+;?)\s*(?!import\s+)', r'\1\n\n', code)

    # 4. Split top-level statements and declarations
    code = re.sub(r';\s*(?=(?:export|function|const|let|var|class|return|if|for|while)\b)', ';\n', code)
    code = re.sub(r'{\s*(?=(?:export|function|const|let|var|class|return|if|for|while)\b)', '{\n  ', code)

    # 5. Format JSX tags that are packed on a single line
    code = re.sub(r'(<[A-Za-z0-9_]+[^>]*>)\s*(?=<[A-Za-z0-9_]+)', r'\1\n  ', code)
    code = re.sub(r'(</[A-Za-z0-9_]+>)\s*(?=<[A-Za-z0-9_]+|export|function|const|return)', r'\1\n', code)
    code = re.sub(r'(/>)\s*(?=<[A-Za-z0-9_]+)', r'\1\n  ', code)

    # Clean up trailing spaces and empty lines
    cleaned = []
    for line in code.splitlines():
        cleaned.append(line.rstrip())

    result = "\n".join(cleaned).strip()
    return use_directive + result + "\n"


def format_code_content(filename: str, code: str) -> str:
    """Master formatting dispatcher for all code files generated across the multi-agent system."""
    if not code:
        return code

    code = unescape_string_literals(code)
    ext = filename.split('.')[-1].lower() if '.' in filename else ''

    if ext == 'json':
        return format_json_code(code)
    elif ext in ['css', 'scss', 'less']:
        return format_css_code(code)
    elif ext in ['js', 'jsx', 'ts', 'tsx', 'mjs', 'cjs']:
        return format_javascript_code(code)
    elif ext in ['html', 'htm']:
        return unescape_string_literals(code).strip() + "\n"
    elif ext in ['py', 'pyw']:
        return unescape_string_literals(code).strip() + "\n"
    return unescape_string_literals(code)


def auto_generate_missing_components(parsed_files: Dict[str, str], target_folder: str = ".") -> Dict[str, str]:
    """Detects missing component imports in Next.js / React JSX/TSX files and automatically synthesizes them.

    For example, if `app/page.jsx` has:
        `import Navbar from "@/components/Navbar";`
        `import Hero from "@/components/Hero";`
    and `components/Navbar.jsx` was omitted by the LLM, this function creates a beautiful,
    fully-functional fallback component to prevent Next.js 'Module not found' build crashes.
    """
    updated = dict(parsed_files)

    for filename, content in list(parsed_files.items()):
        if not filename.endswith(('.jsx', '.tsx', '.js', '.ts')):
            continue

        # Find imports from '@/components/...' or './components/...' or '../components/...'
        matches = re.finditer(
            r'import\s+(?:([A-Za-z0-9_]+)|\{\s*([^}]+)\s*\})\s+from\s+[\'"](?:@\/|\.\/|\.\.\/)?components\/([A-Za-z0-9_\-\/]+)[\'"]',
            content
        )
        for m in matches:
            default_import = m.group(1)
            named_imports = m.group(2)
            comp_path = m.group(3)

            # Target component filename
            comp_file = f"components/{comp_path}"
            if not comp_file.endswith(('.jsx', '.tsx', '.js', '.ts')):
                comp_file += ".jsx"

            # Check if this component file already exists in parsed_files or on disk
            possible_names = [
                comp_file.lower(),
                f"components/{comp_path}.tsx".lower(),
                f"components/{comp_path}.js".lower(),
                f"components/{comp_path}/index.jsx".lower(),
                f"components/{comp_path}/index.tsx".lower(),
            ]

            exists_in_parsed = any(fn.replace('\\', '/').lower() in possible_names for fn in updated.keys())
            
            exists_on_disk = False
            if target_folder and target_folder != ".":
                disk_path = os.path.join(target_folder, comp_file)
                exists_on_disk = os.path.exists(disk_path)

            if not exists_in_parsed and not exists_on_disk:
                # Synthesize a modern, beautiful matching component
                name = default_import or (named_imports.split(',')[0].strip() if named_imports else comp_path.split('/')[-1])
                
                # Context-aware styling for common component names
                lower_name = name.lower()
                if "nav" in lower_name or "header" in lower_name:
                    comp_code = (
                        '"use client";\n'
                        'import React from "react";\n\n'
                        f'export default function {name}(props) {{\n'
                        '  return (\n'
                        '    <nav className="w-full border-b border-slate-800 bg-slate-900/50 backdrop-blur-md px-6 py-4 flex items-center justify-between shadow-lg">\n'
                        '      <div className="text-xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">\n'
                        f'        {name}\n'
                        '      </div>\n'
                        '      <div className="flex items-center gap-4">\n'
                        '        <a href="#features" className="text-sm text-slate-300 hover:text-white transition-colors">Features</a>\n'
                        '        <a href="#about" className="text-sm text-slate-300 hover:text-white transition-colors">About</a>\n'
                        '        <button className="px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-all shadow-md shadow-blue-500/20">\n'
                        '          Get Started\n'
                        '        </button>\n'
                        '      </div>\n'
                        '    </nav>\n'
                        '  );\n'
                        '}\n'
                    )
                elif "hero" in lower_name:
                    comp_code = (
                        '"use client";\n'
                        'import React from "react";\n\n'
                        f'export default function {name}(props) {{\n'
                        '  return (\n'
                        '    <section className="py-16 px-6 text-center max-w-4xl mx-auto">\n'
                        '      <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent mb-6">\n'
                        '        Next-Gen Full-Stack Experience\n'
                        '      </h1>\n'
                        '      <p className="text-lg text-slate-300 mb-8 max-w-2xl mx-auto">\n'
                        '        Built autonomously with high-performance React and Next.js architecture.\n'
                        '      </p>\n'
                        '      <div className="flex justify-center gap-4">\n'
                        '        <button className="px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 font-semibold text-white transition-all shadow-xl shadow-blue-600/30">\n'
                        '          Explore Now\n'
                        '        </button>\n'
                        '      </div>\n'
                        '    </section>\n'
                        '  );\n'
                        '}\n'
                    )
                elif "footer" in lower_name:
                    comp_code = (
                        '"use client";\n'
                        'import React from "react";\n\n'
                        f'export default function {name}(props) {{\n'
                        '  return (\n'
                        '    <footer className="w-full border-t border-slate-800/80 py-8 px-6 text-center text-sm text-slate-500 mt-16">\n'
                        '      <p>© 2026 Next.js Application. Built with Claw Agent.</p>\n'
                        '    </footer>\n'
                        '  );\n'
                        '}\n'
                    )
                else:
                    comp_code = (
                        '"use client";\n'
                        'import React from "react";\n\n'
                        f'export default function {name}(props) {{\n'
                        '  return (\n'
                        '    <div className="w-full p-6 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-xl shadow-xl my-4 text-slate-100">\n'
                        '      <h3 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent mb-2">\n'
                        f'        {name}\n'
                        '      </h3>\n'
                        '      <p className="text-sm text-slate-400">\n'
                        '        Component initialized autonomously by Claw Agent.\n'
                        '      </p>\n'
                        '    </div>\n'
                        '  );\n'
                        '}\n'
                    )

                if named_imports:
                    for item in named_imports.split(','):
                        sub_name = item.strip()
                        if sub_name and sub_name != name:
                            comp_code += (
                                f'\nexport function {sub_name}(props) {{\n'
                                '  return (\n'
                                '    <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 text-slate-200">\n'
                                f'      <h4 className="font-semibold text-blue-400">{sub_name}</h4>\n'
                                '    </div>\n'
                                '  );\n'
                                '}\n'
                            )
                updated[comp_file] = format_code_content(comp_file, comp_code)

    return updated
