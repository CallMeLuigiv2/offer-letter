"""Parsing `git diff` output into the new-side line numbers a reviewer can comment on."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass
class FileDiff:
    path: str
    added: set[int] = field(default_factory=set)      # new-side lines starting with '+'
    visible: set[int] = field(default_factory=set)    # new-side lines shown in hunks (added + context)


def parse(diff_text: str) -> dict[str, FileDiff]:
    files: dict[str, FileDiff] = {}
    current: FileDiff | None = None
    in_header = False
    new_line = 0
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            current, in_header = None, True
            continue
        if in_header:
            if line.startswith("+++ "):
                target = line[4:]
                current = None if target == "/dev/null" else files.setdefault(target[2:], FileDiff(target[2:]))
            m = HUNK.match(line)
            if not m:
                continue
            in_header = False
        m = HUNK.match(line)
        if m:
            new_line = int(m.group(1))
            continue
        if current is None:
            continue
        if line.startswith("+"):
            current.added.add(new_line)
            current.visible.add(new_line)
            new_line += 1
        elif line.startswith(" "):
            current.visible.add(new_line)
            new_line += 1
        # '-' lines and '\ No newline at end of file' don't move the new side
    return files
