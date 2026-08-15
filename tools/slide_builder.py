import json
import os
import traceback
from typing import Dict, Any

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False


class SlideBuilder:
    """
    Renders structured JSON slide data into Reveal.js HTML and PowerPoint files.
    """

    def __init__(self):
        # Define some basic theme colors for PPTX
        self.themes = {
            "modern-dark": {
                "bg": RGBColor(34, 34, 34),
                "text": RGBColor(238, 238, 238),
                "accent": RGBColor(102, 178, 255)
            },
            "clean-light": {
                "bg": RGBColor(250, 250, 250),
                "text": RGBColor(51, 51, 51),
                "accent": RGBColor(0, 102, 204)
            },
            "academic": {
                "bg": RGBColor(255, 255, 240),
                "text": RGBColor(34, 34, 34),
                "accent": RGBColor(153, 0, 0)
            },
            "vibrant": {
                "bg": RGBColor(40, 15, 60),
                "text": RGBColor(255, 255, 255),
                "accent": RGBColor(255, 102, 204)
            }
        }
        
        self.reveal_themes = {
            "modern-dark": "black",
            "clean-light": "white",
            "academic": "serif",
            "vibrant": "dracula"
        }

    def _get_reveal_html_template(self, title: str, author: str, theme: str, transition: str, slides_html: str) -> str:
        reveal_theme = self.reveal_themes.get(theme, "black")
        
        return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">

    <title>{title}</title>
    <meta name="author" content="{author}">

    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reset.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/{reveal_theme}.css" id="theme">

    <!-- Theme used for syntax highlighted code -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/highlight/monokai.css">
    
    <style>
        .reveal .slides section .two-column {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-gap: 20px;
        }}
        .image-placeholder {{
            border: 2px dashed #888;
            padding: 40px;
            background: rgba(128, 128, 128, 0.1);
            border-radius: 10px;
            margin: 20px auto;
            max-width: 80%;
        }}
    </style>
</head>
<body>
    <div class="reveal">
        <div class="slides">
{slides_html}
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/notes/notes.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/markdown/markdown.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/highlight/highlight.js"></script>
    <script>
        // More info about initialization & config:
        // - https://revealjs.com/initialization/
        // - https://revealjs.com/config/
        Reveal.initialize({{
            hash: true,
            transition: '{transition}',
            // Learn about plugins: https://revealjs.com/plugins/
            plugins: [ RevealMarkdown, RevealHighlight, RevealNotes ]
        }});
    </script>
</body>
</html>"""

    def _render_reveal_slide(self, slide: Dict[str, Any]) -> str:
        slide_type = slide.get("type", "content")
        notes = slide.get("notes", "")
        notes_html = f"<aside class=\"notes\">\n{notes}\n</aside>" if notes else ""
        
        html = "<section>\n"
        
        if slide_type == "title":
            html += f"    <h2>{slide.get('title', '')}</h2>\n"
            if slide.get("subtitle"):
                html += f"    <h3>{slide.get('subtitle', '')}</h3>\n"
            
        elif slide_type == "content":
            html += f"    <h3>{slide.get('title', '')}</h3>\n"
            html += "    <ul>\n"
            for bullet in slide.get("bullets", []):
                html += f"        <li>{bullet}</li>\n"
            html += "    </ul>\n"
            
        elif slide_type == "two_column":
            html += f"    <h3>{slide.get('title', '')}</h3>\n"
            html += "    <div class=\"two-column\">\n"
            
            left = slide.get("left", {})
            html += "        <div>\n"
            if left.get("heading"):
                html += f"            <h4>{left.get('heading', '')}</h4>\n"
            html += "            <ul>\n"
            for bullet in left.get("bullets", []):
                html += f"                <li>{bullet}</li>\n"
            html += "            </ul>\n"
            html += "        </div>\n"
            
            right = slide.get("right", {})
            html += "        <div>\n"
            if right.get("heading"):
                html += f"            <h4>{right.get('heading', '')}</h4>\n"
            html += "            <ul>\n"
            for bullet in right.get("bullets", []):
                html += f"                <li>{bullet}</li>\n"
            html += "            </ul>\n"
            html += "        </div>\n"
            html += "    </div>\n"
            
        elif slide_type == "code":
            html += f"    <h3>{slide.get('title', '')}</h3>\n"
            lang = slide.get("language", "")
            code = slide.get("code", "")
            html += f"    <pre><code data-trim data-noescape class=\"language-{lang}\">\n{code}\n</code></pre>\n"
            
        elif slide_type == "section_header":
            html += f"    <h1>{slide.get('title', '')}</h1>\n"
            if slide.get("subtitle"):
                html += f"    <h3>{slide.get('subtitle', '')}</h3>\n"
                
        elif slide_type == "image":
            html += f"    <h3>{slide.get('title', '')}</h3>\n"
            html += f"    <div class=\"image-placeholder\">\n"
            html += f"        <p>🖼️ <i>{slide.get('image_description', 'Image Placeholder')}</i></p>\n"
            html += "    </div>\n"
            if slide.get("caption"):
                html += f"    <p><small>{slide.get('caption', '')}</small></p>\n"
        
        else:
            html += f"    <h3>Unsupported slide type: {slide_type}</h3>\n"
            
        html += notes_html
        html += "</section>\n"
        return html

    def build_revealjs(self, slide_data: dict, output_path: str) -> dict:
        """Generate Reveal.js HTML file. Returns {'status': 'success'|'error', 'file_path': str, 'slide_count': int}"""
        try:
            title = slide_data.get("title", "Presentation")
            author = slide_data.get("author", "Neo Agent")
            theme = slide_data.get("theme", "modern-dark")
            transition = slide_data.get("transition", "slide")
            
            slides = slide_data.get("slides", [])
            
            # Generate cover slide
            slides_html = "<section>\n"
            slides_html += f"    <h2>{title}</h2>\n"
            if slide_data.get("subtitle"):
                slides_html += f"    <h3>{slide_data.get('subtitle', '')}</h3>\n"
            slides_html += f"    <p><small>By {author}</small></p>\n"
            slides_html += "</section>\n"
            
            # Generate content slides
            for slide in slides:
                slides_html += self._render_reveal_slide(slide)
                
            full_html = self._get_reveal_html_template(title, author, theme, transition, slides_html)
            
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_html)
                
            return {
                "status": "success",
                "file_path": output_path,
                "slide_count": len(slides) + 1  # +1 for title slide
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Could not build Reveal.js presentation: {str(e)}",
                "details": traceback.format_exc()
            }

    def _apply_pptx_theme(self, slide, prs, theme_colors):
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = theme_colors["bg"]
        
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.color.rgb = theme_colors["text"]

    def _create_pptx_slide(self, prs, slide_data: dict, theme_colors: dict):
        slide_type = slide_data.get("type", "content")
        
        if slide_type == "title" or slide_type == "section_header":
            slide_layout = prs.slide_layouts[0] # Title slide
            slide = prs.slides.add_slide(slide_layout)
            self._apply_pptx_theme(slide, prs, theme_colors)
            title = slide.shapes.title
            subtitle = slide.placeholders[1]
            title.text = slide_data.get("title", "")
            title.text_frame.paragraphs[0].runs[0].font.color.rgb = theme_colors["text"]
            subtitle.text = slide_data.get("subtitle", "")
            if subtitle.text:
                subtitle.text_frame.paragraphs[0].runs[0].font.color.rgb = theme_colors["accent"]
                
        elif slide_type == "content":
            slide_layout = prs.slide_layouts[1] # Title and Content
            slide = prs.slides.add_slide(slide_layout)
            self._apply_pptx_theme(slide, prs, theme_colors)
            title = slide.shapes.title
            title.text = slide_data.get("title", "")
            title.text_frame.paragraphs[0].runs[0].font.color.rgb = theme_colors["text"]
            
            body = slide.placeholders[1]
            tf = body.text_frame
            tf.text = "" # Clear placeholder
            bullets = slide_data.get("bullets", [])
            for i, bullet in enumerate(bullets):
                p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
                p.text = bullet
                p.level = 0
                p.runs[0].font.color.rgb = theme_colors["text"]
                
        elif slide_type == "two_column":
            slide_layout = prs.slide_layouts[3] # Two Content
            slide = prs.slides.add_slide(slide_layout)
            self._apply_pptx_theme(slide, prs, theme_colors)
            title = slide.shapes.title
            title.text = slide_data.get("title", "")
            title.text_frame.paragraphs[0].runs[0].font.color.rgb = theme_colors["text"]
            
            left_placeholder = slide.placeholders[1]
            right_placeholder = slide.placeholders[2]
            
            left_data = slide_data.get("left", {})
            left_tf = left_placeholder.text_frame
            left_tf.text = left_data.get("heading", "")
            if left_tf.text:
                left_tf.paragraphs[0].runs[0].font.color.rgb = theme_colors["accent"]
            
            for bullet in left_data.get("bullets", []):
                p = left_tf.add_paragraph()
                p.text = bullet
                p.level = 0 if left_tf.text == "" else 1
                p.runs[0].font.color.rgb = theme_colors["text"]
                
            right_data = slide_data.get("right", {})
            right_tf = right_placeholder.text_frame
            right_tf.text = right_data.get("heading", "")
            if right_tf.text:
                right_tf.paragraphs[0].runs[0].font.color.rgb = theme_colors["accent"]
                
            for bullet in right_data.get("bullets", []):
                p = right_tf.add_paragraph()
                p.text = bullet
                p.level = 0 if right_tf.text == "" else 1
                p.runs[0].font.color.rgb = theme_colors["text"]
                
        elif slide_type == "code":
            slide_layout = prs.slide_layouts[1]
            slide = prs.slides.add_slide(slide_layout)
            self._apply_pptx_theme(slide, prs, theme_colors)
            title = slide.shapes.title
            title.text = slide_data.get("title", "")
            title.text_frame.paragraphs[0].runs[0].font.color.rgb = theme_colors["text"]
            
            body = slide.placeholders[1]
            tf = body.text_frame
            tf.text = f"Language: {slide_data.get('language', 'text')}\n\n"
            tf.paragraphs[0].runs[0].font.color.rgb = theme_colors["accent"]
            
            code_lines = slide_data.get("code", "").split("\n")
            for line in code_lines:
                p = tf.add_paragraph()
                p.text = line
                p.level = 0
                p.font.name = 'Courier New'
                p.font.size = Pt(14)
                if p.runs:
                    p.runs[0].font.color.rgb = theme_colors["text"]
                
        elif slide_type == "image":
            slide_layout = prs.slide_layouts[1]
            slide = prs.slides.add_slide(slide_layout)
            self._apply_pptx_theme(slide, prs, theme_colors)
            title = slide.shapes.title
            title.text = slide_data.get("title", "")
            title.text_frame.paragraphs[0].runs[0].font.color.rgb = theme_colors["text"]
            
            body = slide.placeholders[1]
            tf = body.text_frame
            tf.text = f"[Image Placeholder: {slide_data.get('image_description', '')}]\n"
            if slide_data.get("caption"):
                p = tf.add_paragraph()
                p.text = slide_data.get("caption", "")
                if p.runs:
                    p.runs[0].font.color.rgb = theme_colors["accent"]
                
        else:
            slide_layout = prs.slide_layouts[1]
            slide = prs.slides.add_slide(slide_layout)
            self._apply_pptx_theme(slide, prs, theme_colors)
            title = slide.shapes.title
            title.text = "Unsupported Slide Type"
            body = slide.placeholders[1]
            body.text = f"Type: {slide_type}"

        # Add notes
        if slide.has_notes_slide and slide_data.get("notes"):
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = slide_data.get("notes", "")

        return slide

    def build_pptx(self, slide_data: dict, output_path: str) -> dict:
        """Generate PowerPoint file. Returns {'status': 'success'|'error', 'file_path': str, 'slide_count': int}"""
        if not PPTX_AVAILABLE:
            return {
                "status": "error",
                "error_message": "The python-pptx library is not installed. Please install it using 'pip install python-pptx' to generate PowerPoint files."
            }
            
        try:
            prs = Presentation()
            theme_name = slide_data.get("theme", "modern-dark")
            theme_colors = self.themes.get(theme_name, self.themes["modern-dark"])
            
            # Title slide
            title_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(title_layout)
            self._apply_pptx_theme(slide, prs, theme_colors)
            title = slide.shapes.title
            subtitle = slide.placeholders[1]
            
            title.text = slide_data.get("title", "Presentation")
            if title.text_frame.paragraphs and title.text_frame.paragraphs[0].runs:
                title.text_frame.paragraphs[0].runs[0].font.color.rgb = theme_colors["text"]
                
            author = slide_data.get("author", "")
            pres_subtitle = slide_data.get("subtitle", "")
            subtitle_text = pres_subtitle
            if author:
                subtitle_text += f"\nBy {author}" if subtitle_text else f"By {author}"
            subtitle.text = subtitle_text
            
            if subtitle.text_frame.paragraphs:
                for p in subtitle.text_frame.paragraphs:
                    if p.runs:
                        p.runs[0].font.color.rgb = theme_colors["accent"]
            
            slides = slide_data.get("slides", [])
            for s_data in slides:
                self._create_pptx_slide(prs, s_data, theme_colors)
                
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            prs.save(output_path)
            
            return {
                "status": "success",
                "file_path": output_path,
                "slide_count": len(slides) + 1
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Could not build PPTX presentation: {str(e)}",
                "details": traceback.format_exc()
            }
            
    def build_both(self, slide_data: dict, output_dir: str, base_name: str = 'presentation') -> dict:
        """Generate both formats. Returns {'status': 'success'|'error', 'revealjs_path': str, 'pptx_path': str, 'slide_count': int}"""
        reveal_path = os.path.join(output_dir, f"{base_name}.html")
        pptx_path = os.path.join(output_dir, f"{base_name}.pptx")
        
        reveal_result = self.build_revealjs(slide_data, reveal_path)
        pptx_result = self.build_pptx(slide_data, pptx_path)
        
        if reveal_result["status"] == "success" and pptx_result["status"] == "success":
            return {
                "status": "success",
                "revealjs_path": reveal_path,
                "pptx_path": pptx_path,
                "slide_count": reveal_result["slide_count"]
            }
        elif reveal_result["status"] == "success":
            return {
                "status": "partial_success",
                "revealjs_path": reveal_path,
                "slide_count": reveal_result["slide_count"],
                "error_message": f"PPTX failed: {pptx_result.get('error_message')}"
            }
        elif pptx_result["status"] == "success":
            return {
                "status": "partial_success",
                "pptx_path": pptx_path,
                "slide_count": pptx_result["slide_count"],
                "error_message": f"Reveal.js failed: {reveal_result.get('error_message')}"
            }
        else:
            return {
                "status": "error",
                "error_message": f"Both builds failed. HTML: {reveal_result.get('error_message')} | PPTX: {pptx_result.get('error_message')}"
            }
            
    def update_pptx(self, file_path: str, changes: dict) -> dict:
        """Modify an existing .pptx file. Changes dict can specify: add_slide, remove_slide, update_slide."""
        if not PPTX_AVAILABLE:
            return {
                "status": "error",
                "error_message": "The python-pptx library is not installed."
            }
            
        try:
            prs = Presentation(file_path)
            
            action = changes.get("action")
            if action == "add_slide":
                theme_colors = self.themes["modern-dark"]
                self._create_pptx_slide(prs, changes.get("slide_data", {}), theme_colors)
                prs.save(file_path)
                return {"status": "success", "file_path": file_path, "message": "Slide added."}
            else:
                return {
                    "status": "error",
                    "error_message": f"Action '{action}' is not fully supported for PPTX updates yet. Try 'add_slide_to_pptx'."
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Could not update PPTX presentation: {str(e)}",
                "details": traceback.format_exc()
            }
            
    def add_slide_to_pptx(self, file_path: str, slide_data: dict, position: int = -1) -> dict:
        """Insert a new slide at a specific position (-1 = end)."""
        if not PPTX_AVAILABLE:
            return {
                "status": "error",
                "error_message": "The python-pptx library is not installed."
            }
            
        try:
            prs = Presentation(file_path)
            theme_colors = self.themes["modern-dark"]
            
            new_slide = self._create_pptx_slide(prs, slide_data, theme_colors)
            
            if position != -1 and 0 <= position < len(prs.slides):
                xml_slides = prs.slides._sldIdLst
                slides = list(xml_slides)
                xml_slides.remove(slides[-1])
                xml_slides.insert(position, slides[-1])
                
            prs.save(file_path)
            return {
                "status": "success",
                "file_path": file_path,
                "message": f"Slide added at position {position if position != -1 else 'end'}."
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Could not add slide to PPTX: {str(e)}",
                "details": traceback.format_exc()
            }
