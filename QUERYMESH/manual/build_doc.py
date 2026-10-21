"""Turn a lab-manual source file (.qm) into Google Docs batchUpdate requests for one EMPTY tab.

Source format, one paragraph per line:
  # / ## / ###        headings 1-3
  ```  ...  ```       code block (grey box, monospace, copied exactly)
  @code path          code block with the content of a project file
  - text              bullet
  § a § b § c         table row (first row = header). A line "!blue" before a table makes
                      its last column light blue. Inside a cell, "\\n" starts a new line.
  **bold**  `code`    inline styles; URLs become links
Lines starting with WHERE:, GOAL:, Step N., You should see:, Watch out:, CHECKPOINT:, If not:
get a bold label automatically.

Usage: python build_doc.py SOURCE.qm TAB_ID OUT_DIR
Writes OUT_DIR/batch_NN.json and OUT_DIR/expected.txt
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # the QUERYMESH project folder
BATCH_JSON_CHARS = 14000  # keep every update_doc call small

GREY = {"red": 0.95, "green": 0.95, "blue": 0.95}
HEADER_GREY = {"red": 0.88, "green": 0.88, "blue": 0.88}
LIGHT_BLUE = {"red": 0.812, "green": 0.886, "blue": 0.953}
BLUE_HEADER = {"red": 0.624, "green": 0.773, "blue": 0.91}
RED = {"red": 0.75, "green": 0.1, "blue": 0.1}
GREEN = {"red": 0.1, "green": 0.45, "blue": 0.2}
MONO = {"fontFamily": "Roboto Mono", "weight": 400}

LABEL_RE = re.compile(r"^(WHERE:|GOAL:|Step \d+[a-z]?\.|You should see:|Watch out:|CHECKPOINT:|If not:|Answer:|Why:)")
LABEL_COLOR = {"Watch out:": RED, "CHECKPOINT:": GREEN}
INLINE_RE = re.compile(r"\*\*(.+?)\*\*|`([^`]+)`")
URL_RE = re.compile(r"https?://[^\s<>\"'`]+[^\s<>\"'`.,;:)\]]")


def u16(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


# ---------------------------------------------------------------- parsing
def parse_inline(text: str):
    """Return (plain_text, spans) where spans = [(start, end, kind)] in UTF-16 units."""
    out, spans, pos = [], [], 0
    label = LABEL_RE.match(text)
    if label:
        spans.append((0, u16(label.group(1)), "label:" + label.group(1)))
    for m in INLINE_RE.finditer(text):
        out.append(text[pos:m.start()])
        start = u16("".join(out))
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        out.append(inner)
        spans.append((start, start + u16(inner), "bold" if m.group(1) is not None else "code"))
        pos = m.end()
    out.append(text[pos:])
    plain = "".join(out)
    for m in URL_RE.finditer(plain):
        start = u16(plain[:m.start()])
        spans.append((start, start + u16(m.group(0)), "link:" + m.group(0)))
    return plain, spans


def parse(source: str):
    """Return a list of blocks: ("para", style, text, spans) | ("table", rows, blue)."""
    blocks, lines, i = [], source.splitlines(), 0
    blue_next = False
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("```"):
            i += 1
            while not lines[i].startswith("```"):
                blocks.append(("para", "CODE", lines[i].rstrip(), []))
                i += 1
        elif line.startswith("@code "):
            for code_line in (ROOT / line[6:].strip()).read_text().rstrip("\n").split("\n"):
                blocks.append(("para", "CODE", code_line.rstrip(), []))
        elif line == "!blue":
            blue_next = True
        elif line.startswith("§"):
            rows = []
            while i < len(lines) and lines[i].startswith("§"):
                cells = [c.strip().replace("\\n", "\n") for c in lines[i].strip()[1:].split("§")]
                rows.append(cells)
                i += 1
            width = max(len(r) for r in rows)
            rows = [r + [""] * (width - len(r)) for r in rows]
            blocks.append(("table", rows, blue_next))
            blue_next = False
            continue
        elif not line.strip():
            pass
        else:
            for prefix, style in (("### ", "HEADING_3"), ("## ", "HEADING_2"), ("# ", "HEADING_1"),
                                  ("- ", "BULLET")):
                if line.startswith(prefix):
                    text, spans = parse_inline(line[len(prefix):])
                    blocks.append(("para", style, text, spans))
                    break
            else:
                text, spans = parse_inline(line)
                blocks.append(("para", "NORMAL_TEXT", text, spans))
        i += 1
    return blocks


# ---------------------------------------------------------------- request building
class Builder:
    def __init__(self, tab_id: str):
        self.tab = tab_id
        self.cursor = 1  # start of the tab's last (empty) paragraph
        self.requests: list[dict] = []
        self.expected: list[str] = []

    def rng(self, start, end):
        return {"startIndex": start, "endIndex": end, "tabId": self.tab}

    def add(self, request):
        self.requests.append(request)

    def batches(self) -> list[list[dict]]:
        """Requests run in order and use absolute positions, so any cut between two requests is safe."""
        out, current, size = [], [], 0
        for request in self.requests:
            length = len(json.dumps(request, ensure_ascii=False))
            if current and size + length > BATCH_JSON_CHARS:
                out.append(current)
                current, size = [], 0
            current.append(request)
            size += length
        if current:
            out.append(current)
        return out

    def span_requests(self, base, spans):
        for start, end, kind in spans:
            if end <= start:
                continue
            r = self.rng(base + start, base + end)
            if kind == "bold":
                self.add({"updateTextStyle": {"range": r, "textStyle": {"bold": True}, "fields": "bold"}})
            elif kind == "code":
                self.add({"updateTextStyle": {"range": r, "textStyle": {"weightedFontFamily": MONO, "backgroundColor": {"color": {"rgbColor": GREY}}},
                                              "fields": "weightedFontFamily,backgroundColor"}})
            elif kind.startswith("link:"):
                self.add({"updateTextStyle": {"range": r, "textStyle": {"link": {"url": kind[5:]}}, "fields": "link"}})
            elif kind.startswith("label:"):
                style, fields = {"bold": True}, "bold"
                color = LABEL_COLOR.get(kind[6:])
                if color:
                    style["foregroundColor"] = {"color": {"rgbColor": color}}
                    fields += ",foregroundColor"
                self.add({"updateTextStyle": {"range": r, "textStyle": style, "fields": fields}})

    def paragraphs(self, paras):
        """paras = [(style, text, spans)] inserted as one block."""
        text = "".join(p[1] + "\n" for p in paras)
        start = self.cursor
        self.add({"insertText": {"location": {"index": start, "tabId": self.tab}, "text": text}})
        end = start + u16(text)
        self.add({"updateTextStyle": {"range": self.rng(start, end), "textStyle": {},
                                      "fields": "bold,italic,underline,weightedFontFamily,fontSize,foregroundColor,backgroundColor,link"}})
        # paragraph styles, grouped into runs of the same kind
        pos, runs = start, []
        for style, ptext, spans in paras:
            length = u16(ptext) + 1
            runs.append((style, pos, pos + length, ptext, spans))
            pos += length
        group_start = 0
        for idx in range(1, len(runs) + 1):
            if idx == len(runs) or runs[idx][0] != runs[group_start][0]:
                style, s, e = runs[group_start][0], runs[group_start][1], runs[idx - 1][2]
                named = style if style.startswith("HEADING") else "NORMAL_TEXT"
                pstyle = {"namedStyleType": named}
                fields = "namedStyleType"
                if style == "CODE":
                    pstyle["shading"] = {"backgroundColor": {"color": {"rgbColor": GREY}}}
                    pstyle["spaceAbove"] = {"magnitude": 0, "unit": "PT"}
                    pstyle["spaceBelow"] = {"magnitude": 0, "unit": "PT"}
                    fields += ",shading.backgroundColor,spaceAbove,spaceBelow"
                self.add({"updateParagraphStyle": {"range": self.rng(s, e), "paragraphStyle": pstyle, "fields": fields}})
                if style == "CODE":
                    self.add({"updateTextStyle": {"range": self.rng(s, e), "textStyle": {"weightedFontFamily": MONO, "fontSize": {"magnitude": 9.5, "unit": "PT"}},
                                                  "fields": "weightedFontFamily,fontSize"}})
                if style == "BULLET":
                    self.add({"createParagraphBullets": {"range": self.rng(s, e), "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"}})
                if style.startswith("HEADING"):
                    self.add({"updateParagraphStyle": {"range": self.rng(s, e), "paragraphStyle": {"keepWithNext": True}, "fields": "keepWithNext"}})
                group_start = idx
        for style, s, e, ptext, spans in runs:
            if spans:
                self.span_requests(s, spans)
            self.expected.append(ptext)
        self.cursor = end

    def table(self, rows, blue):
        n_rows, n_cols = len(rows), len(rows[0])
        cells = [[parse_inline(c) for c in row] for row in rows]
        size = sum(u16(t) for row in cells for t, _ in row)
        at = self.cursor - 1  # the end of the paragraph before the table
        table_start = at + 1
        stride = 2 * n_cols + 1

        def cell_para(r, c):
            return table_start + 3 + r * stride + 2 * c

        empty_end = table_start + 2 + n_rows * stride
        self.add({"insertTable": {"rows": n_rows, "columns": n_cols, "location": {"index": at, "tabId": self.tab}}})
        self.add({"updateParagraphStyle": {"range": self.rng(empty_end, empty_end + 1),
                                           "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"}, "fields": "namedStyleType"}})
        for r in range(n_rows - 1, -1, -1):
            for c in range(n_cols - 1, -1, -1):
                text = cells[r][c][0]
                if text:
                    self.add({"insertText": {"location": {"index": cell_para(r, c), "tabId": self.tab}, "text": text}})
        total = size
        table_end = empty_end + total
        self.add({"updateParagraphStyle": {"range": self.rng(table_start, table_end),
                                           "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"}, "fields": "namedStyleType"}})
        self.add({"updateTextStyle": {"range": self.rng(table_start, table_end), "textStyle": {},
                                      "fields": "bold,italic,underline,weightedFontFamily,fontSize,foregroundColor,backgroundColor,link"}})
        shift = 0
        for r in range(n_rows):
            for c in range(n_cols):
                text, spans = cells[r][c]
                base = cell_para(r, c) + shift
                if r == 0 and text:
                    self.add({"updateTextStyle": {"range": self.rng(base, base + u16(text)), "textStyle": {"bold": True}, "fields": "bold"}})
                self.span_requests(base, spans)
                shift += u16(text)
                self.expected.append(text)

        def fill(row0, rows_n, col0, cols_n, color):
            self.add({"updateTableCellStyle": {
                "tableRange": {"tableCellLocation": {"tableStartLocation": {"index": table_start, "tabId": self.tab},
                                                     "rowIndex": row0, "columnIndex": col0},
                               "rowSpan": rows_n, "columnSpan": cols_n},
                "tableCellStyle": {"backgroundColor": {"color": {"rgbColor": color}}},
                "fields": "backgroundColor"}})

        fill(0, 1, 0, n_cols, HEADER_GREY)
        if blue:
            fill(0, 1, n_cols - 1, 1, BLUE_HEADER)
            if n_rows > 1:
                fill(1, n_rows - 1, n_cols - 1, 1, LIGHT_BLUE)
        if n_cols == 3 and blue:
            self.add({"updateTableColumnProperties": {
                "tableStartLocation": {"index": table_start, "tabId": self.tab}, "columnIndices": [0],
                "tableColumnProperties": {"widthType": "FIXED_WIDTH", "width": {"magnitude": 80, "unit": "PT"}},
                "fields": "width,widthType"}})
        self.cursor = table_end + 1  # skip the empty paragraph Google keeps after every table


def build(source_path: str, tab_id: str, out_dir: str) -> None:
    blocks = parse(Path(source_path).read_text())
    if not blocks or blocks[0][0] != "para":
        raise SystemExit("a tab must start with a paragraph or heading, not a table")
    b = Builder(tab_id)
    pending, last_was_table = [], False
    for block in blocks:
        if block[0] == "para":
            pending.append(block[1:])
            last_was_table = False
            if sum(len(p[1]) for p in pending) > 2500:
                b.paragraphs(pending)
                pending = []
        else:
            if not last_was_table:
                # Google rebuilds the paragraph a table is inserted into and drops its text
                # styles, so every table goes into an empty paragraph of its own.
                pending.append(("NORMAL_TEXT", "", []))
            if pending:
                b.paragraphs(pending)
                pending = []
            b.table(block[1], block[2])
            last_was_table = True
    if pending:
        b.paragraphs(pending)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("batch_*.json"):
        old.unlink()
    batches = b.batches()
    for n, requests in enumerate(batches, start=1):
        (out / f"batch_{n:02d}.json").write_text(json.dumps(requests, ensure_ascii=False))
    (out / "expected.txt").write_text("\n".join(b.expected))
    sizes = [len(json.dumps(x, ensure_ascii=False)) for x in batches]
    print(f"{source_path}: {len(batches)} batches, largest {max(sizes)} chars, final index {b.cursor}")


if __name__ == "__main__":
    build(*sys.argv[1:4])
