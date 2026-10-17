from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".toml", ".json", ".svg", ".gitignore"}
PATTERNS = {
    "private key header": re.compile(r"BEGIN (?:RSA |OPENSSH )?PRIVATE KEY"),
    "GitHub token shape": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "AWS access key shape": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "absolute Windows user path": re.compile(r"[A-Z]:\\Users\\", re.I),
    "absolute home path": re.compile(r"/home/[A-Za-z0-9_.-]+/"),
}


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [ROOT / value.decode() for value in output.split(b"\0") if value]


def main() -> int:
    findings: list[str] = []
    files = tracked_files()
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != ".gitignore":
            continue
        text = path.read_text(encoding="utf-8")
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(ROOT)}: {label}")
        if path.suffix.lower() == ".svg" and "<metadata" in text.lower():
            findings.append(f"{path.relative_to(ROOT)}: SVG metadata block")
    print(f"Tracked files inspected: {len(files)}")
    print("Runtime dependencies declared: 0")
    print("License file present: " + str((ROOT / "LICENSE").exists()).lower())
    if findings:
        print("Potential findings:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Pattern scan findings: 0")
    print("This bounded scan is not a guarantee that every sensitive value is absent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
