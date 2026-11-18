#!/usr/bin/env python3
"""dist/ の中のサイト内リンク・画像・CSS/JS の参照先が、すべて存在するかを確かめる。"""
import os
import re
import sys
import urllib.parse
from pathlib import Path

DIST = Path(__file__).resolve().parent / "dist"
BASE_PATH = os.environ.get("BASE_PATH", "").rstrip("/")
ref_re = re.compile(r'(srcset|href|src|data-src)="([^"]+)"|url\(["\']?([^)"\']+)["\']?\)')
# 移行前（Shifter 時代）から存在しなかった参照。ここに載っているものはエラーにしない
KNOWN = set()
known_file = Path(__file__).resolve().parent / "known_missing.txt"
if known_file.exists():
    KNOWN = {l.strip() for l in known_file.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}

missing = {}
for f in DIST.rglob("*"):
    if f.suffix not in (".html", ".css"):
        continue
    s = f.read_text(encoding="utf-8", errors="ignore")
    for m in ref_re.finditer(s):
        vals = re.split(r",\s*", m.group(2)) if m.group(1) == "srcset" else [m.group(2) or m.group(3)]
        for u in vals:
            u = u.strip().split(" ")[0]
            if not u or u.startswith(("http:", "https:", "//", "data:", "#", "mailto:", "tel:", "javascript:")):
                continue
            u = urllib.parse.unquote(u.split("#")[0].split("?")[0])
            if not u:
                continue
            if u.startswith("/"):
                if BASE_PATH:
                    if not u.startswith(BASE_PATH + "/") and u != BASE_PATH:
                        missing.setdefault(u + "  (BASE_PATH なし)", set()).add(str(f.relative_to(DIST)))
                        continue
                    u = u[len(BASE_PATH):] or "/"
                target = DIST / u.lstrip("/")
            else:
                target = (f.parent / u)
            if target.is_dir() or u.endswith("/"):
                target = target / "index.html"
            if not target.exists() and u not in KNOWN:
                missing.setdefault(u, set()).add(str(f.relative_to(DIST)))

for u, pages in sorted(missing.items()):
    print(f"見つからない: {u}  ← {', '.join(sorted(pages)[:3])}{' ほか' if len(pages) > 3 else ''}")
print(f"リンク切れ {len(missing)} 件")
sys.exit(1 if missing else 0)
