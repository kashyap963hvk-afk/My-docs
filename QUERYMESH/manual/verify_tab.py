"""Check that a tab's text in Google Docs matches what build_doc.py produced.

Usage: python verify_tab.py DRIVE_EXPORT.json "TAB TITLE" "NEXT TAB TITLE" expected.txt
DRIVE_EXPORT.json = saved result of Drive read_file_content ({"fileContent": "..."}).
"""
import json
import re
import sys


def norm(text: str) -> str:
    text = text.replace("\\", "").replace("**", "").replace("|", " ")
    text = re.sub(r"<(https?://[^>]+)>", r"\1", text)
    text = re.sub(r"^#+ ", "", text, flags=re.M)
    text = re.sub(r":-+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main(export_path, title, next_title, expected_path):
    content = json.load(open(export_path))["fileContent"]
    start = content.find(f"\n# {title}\n")
    if start < 0:
        raise SystemExit(f"tab heading '# {title}' not found")
    end = content.find(f"\n# {next_title}\n", start + 1)
    section = norm(content[start:end if end > 0 else None])
    expected = [norm(p) for p in open(expected_path).read().split("\n") if p.strip()]
    pos, missing = 0, []
    for paragraph in expected:
        probe = paragraph[:60]
        found = section.find(probe, pos)
        if found < 0:
            missing.append(paragraph[:100])
        else:
            pos = found + len(probe)
    print(f"{title}: {len(expected) - len(missing)}/{len(expected)} paragraphs found in order")
    for m in missing[:15]:
        print("  MISSING:", m)


if __name__ == "__main__":
    main(*sys.argv[1:5])
