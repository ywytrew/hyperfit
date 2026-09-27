"""Render the project's small Markdown subset without a runtime dependency."""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/ywytrew/hyperfit/blob/main/docs/"
LANGUAGES = {"zh": ("zh-CN", "返回应用"), "en": ("en", "Back to app"), "ja": ("ja", "アプリに戻る")}


def inline(text):
    def link(match):
        label, target = match.groups()
        local = re.fullmatch(r"(manual|deployment)\.(zh|en|ja)\.md", target)
        if local:
            target = f"{local[1]}-{local[2]}.html"
        elif target.endswith(".md") and "/" not in target:
            target = REPO + target
        if not (target.startswith(("https://", "http://")) or re.fullmatch(r"(manual|deployment)-(zh|en|ja)\.html", target)):
            return escape(label)
        return f'<a href="{escape(target, quote=True)}">{escape(label)}</a>'
    parts = []
    cursor = 0
    for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
        parts.extend((escape(text[cursor:match.start()]), link(match)))
        cursor = match.end()
    parts.append(escape(text[cursor:]))
    return "".join(parts)


def render(source, lang):
    out, paragraph, code = [], [], None
    in_list = False

    def flush():
        if paragraph:
            out.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    for line in source.splitlines():
        if code is not None:
            if line.startswith("```"):
                out.append("<pre><code>" + escape("\n".join(code)) + "</code></pre>")
                code = None
            else:
                code.append(line)
            continue
        if line.startswith("```"):
            flush()
            if in_list:
                out.append("</ul>")
                in_list = False
            code = []
        elif line.startswith("- "):
            flush()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append("<li>" + inline(line[2:]) + "</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            if line.startswith("#"):
                flush()
                level = min(6, len(line) - len(line.lstrip("#")))
                out.append(f"<h{level}>" + inline(line[level:].strip()) + f"</h{level}>")
            elif not line.strip():
                flush()
            else:
                paragraph.append(line.strip())
    flush()
    if in_list:
        out.append("</ul>")
    if code is not None:
        raise ValueError("Unclosed code fence")
    html_lang, back = LANGUAGES[lang]
    title = source.splitlines()[0].lstrip("# ")
    return f"""<!doctype html>
<html lang="{html_lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><link rel="stylesheet" href="style.css">
<style>.manual {{max-width: 920px; line-height: 1.85; background: white; margin: 24px auto; border-radius: 12px;}}
.manual h2 {{margin-top: 32px; font-size: 20px;}} .manual h1 {{line-height: 1.3;}}
.manual pre {{white-space: pre-wrap; overflow-wrap: anywhere; background: #f2f5f9; padding: 18px;}}
.manual a {{color: #215ed4;}} .manual p,.manual li {{overflow-wrap: anywhere;}}
</style></head><body><main class="manual"><nav><a href="./?lang={lang}">← {back}</a></nav>
{chr(10).join(out)}
</main></body></html>
"""


def main():
    for lang in LANGUAGES:
        for kind in ("manual", "deployment"):
            source = (ROOT / "docs" / f"{kind}.{lang}.md").read_text(encoding="utf-8")
            (ROOT / "hyperfit/frontend" / f"{kind}-{lang}.html").write_text(render(source, lang), encoding="utf-8")
    print("Generated six browser manuals and deployment guides.")


if __name__ == "__main__":
    main()
