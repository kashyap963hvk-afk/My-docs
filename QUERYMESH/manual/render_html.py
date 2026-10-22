"""Turn a lab-manual source file (.qm, see build_doc.py) into HTML that Google Drive converts
into a formatted Google Doc (headings, grey code boxes, tables, light-blue AWS column, links).

Usage: python render_html.py SOURCE.qm OUT_PREFIX [MAX_HTML_CHARS]
"""
import html
import re
import sys
from pathlib import Path

from build_doc import INLINE_RE, LABEL_RE, ROOT, URL_RE

LABEL_COLOR = {"Watch out:": "#bf1a1a", "CHECKPOINT:": "#1a7333"}
CODE_STYLE = "font-family:Roboto Mono;font-size:9.5pt;background-color:#f2f2f2"  # grey code boxes
SPAN_STYLE = "font-family:Roboto Mono"  # inline code


def inline(text: str) -> str:
    """Escape text and turn **bold**, `code`, labels and URLs into HTML."""
    out, pos = [], 0
    label = LABEL_RE.match(text)
    if label:
        color = LABEL_COLOR.get(label.group(1))
        style = f' style="color:{color}"' if color else ""
        out.append(f"<b{style}>{html.escape(label.group(1))}</b>")
        pos = label.end()
    for m in INLINE_RE.finditer(text, pos):
        out.append(links(text[pos:m.start()]))
        if m.group(1) is not None:
            out.append(f"<b>{links(m.group(1))}</b>")
        else:
            out.append(f'<span style="{SPAN_STYLE}">{links(m.group(2))}</span>')
        pos = m.end()
    out.append(links(text[pos:]))
    return "".join(out)


def links(text: str) -> str:
    out, pos = [], 0
    for m in URL_RE.finditer(text):
        out.append(html.escape(text[pos:m.start()]))
        url = html.escape(m.group(0))
        out.append(f'<a href="{url}">{url}</a>')
        pos = m.end()
    out.append(html.escape(text[pos:]))
    return "".join(out)


def code_block(lines: list[str]) -> str:
    body = "\n".join(html.escape(line) for line in lines)
    return f'<pre style="{CODE_STYLE}">{body}</pre>'


def table(rows: list[list[str]], blue: bool) -> str:
    out = ['<table border="1" cellpadding="5" style="border-collapse:collapse;width:100%">']
    last = len(rows[0]) - 1
    for r, row in enumerate(rows):
        cells = []
        for c, cell in enumerate(row):
            if r == 0:
                color = "#9fc5e8" if blue and c == last else "#e0e0e0"
            else:
                color = "#cfe2f3" if blue and c == last else ""
            style = f' style="background-color:{color}"' if color else ""
            text = "<br>".join(inline(part) for part in cell.split("\n"))
            if r == 0:
                text = f"<b>{text}</b>"
            cells.append(f"<td{style}>{text}</td>")
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def render(source: str) -> str:
    lines, i, out, bullets, blue_next = source.splitlines(), 0, [], [], False

    def flush_bullets():
        if bullets:
            out.append("<ul>" + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>")
            bullets.clear()

    while i < len(lines):
        line = lines[i].rstrip()
        if not line.startswith("- "):
            flush_bullets()
        if line.startswith("```"):
            block = []
            i += 1
            while not lines[i].startswith("```"):
                block.append(lines[i].rstrip())
                i += 1
            out.append(code_block(block))
        elif line.startswith("@code "):
            out.append(code_block((ROOT / line[6:].strip()).read_text().rstrip("\n").split("\n")))
        elif line == "!blue":
            blue_next = True
        elif line.startswith("§"):
            rows = []
            while i < len(lines) and lines[i].startswith("§"):
                rows.append([c.strip().replace("\\n", "\n") for c in lines[i].strip()[1:].split("§")])
                i += 1
            width = max(len(r) for r in rows)
            out.append(table([r + [""] * (width - len(r)) for r in rows], blue_next))
            blue_next = False
            continue
        elif line.startswith("### "):
            out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("- "):
            bullets.append(inline(line[2:]))
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
        i += 1
    flush_bullets()
    return ('<html><head><meta charset="utf-8"></head><body style="font-family:Arial">\n'
            + "\n".join(out) + "\n</body></html>\n")


def split_source(source: str, max_html: int) -> list[str]:
    """Cut a long source at '## ' headings so that each piece renders to at most max_html chars."""
    sections, current = [], []
    for line in source.splitlines():
        if line.startswith("## ") and current:
            sections.append(current)
            current = []
        current.append(line)
    sections.append(current)
    pieces, piece = [], []
    for section in sections:
        if piece and len(render("\n".join(piece + section))) > max_html:
            pieces.append("\n".join(piece))
            piece = []
        piece += section
    pieces.append("\n".join(piece))
    return pieces


if __name__ == "__main__":
    # python render_html.py SOURCE.qm OUT_PREFIX [MAX_HTML]  ->  OUT_PREFIX_1.html, OUT_PREFIX_2.html ...
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 60000
    for n, piece in enumerate(split_source(Path(sys.argv[1]).read_text(), limit), start=1):
        out = Path(f"{sys.argv[2]}_{n}.html")
        out.write_text(render(piece))
        print(out, len(out.read_text()), "chars")
