#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全站 GEO 体检：链接可达、JSON-LD 合法、必备 meta 齐全、图片存在。"""
import json, re, sys, urllib.request
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8123"

class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.imgs, self.lds, self.metas = [], [], [], {}
        self._in_ld = False; self._buf = ""
        self.title = ""; self._in_title = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"): self.links.append(a["href"])
        if tag == "img": self.imgs.append(a)
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True; self._buf = ""
        if tag == "meta":
            key = a.get("name") or a.get("property")
            if key: self.metas[key] = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.metas["canonical"] = a.get("href", "")
        if tag == "title": self._in_title = True
    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld:
            self._in_ld = False; self.lds.append(self._buf)
        if tag == "title": self._in_title = False
    def handle_data(self, data):
        if self._in_ld: self._buf += data
        if self._in_title: self.title += data

pages = sorted(p for p in ROOT.rglob("*.html"))
errors, warnings = [], []
all_internal = set()

for pg in pages:
    rel = pg.relative_to(ROOT).as_posix()
    p = P(); p.feed(pg.read_text(encoding="utf-8"))
    # 1) JSON-LD 全部可解析
    for i, blk in enumerate(p.lds):
        try: json.loads(blk)
        except Exception as e: errors.append(f"{rel}: JSON-LD#{i} 解析失败 {e}")
    # 2) 必备 meta
    if not p.title.strip(): errors.append(f"{rel}: 缺 <title>")
    if not p.metas.get("description"): errors.append(f"{rel}: 缺 description")
    if rel != "404.html":
        if not p.metas.get("canonical"): errors.append(f"{rel}: 缺 canonical")
        if p.metas.get("robots") != "index,follow,max-image-preview:large":
            warnings.append(f"{rel}: robots meta = {p.metas.get('robots')}")
    # 3) 图片存在且有 alt
    for img in p.imgs:
        src = img.get("src", "")
        if src and not src.startswith("http"):
            t = (pg.parent / src).resolve()
            if not t.exists(): errors.append(f"{rel}: 图片缺失 {src}")
        if not img.get("alt"): errors.append(f"{rel}: <img> 缺 alt: {src}")
    # 4) 收集内部链接
    for href in p.links:
        if href.startswith(("http", "tel:", "mailto:", "#", "javascript")): continue
        h = href.split("#")[0]
        target = (ROOT / h.lstrip("/")).resolve() if h.startswith("/") else (pg.parent / h).resolve()
        all_internal.add(target)

# CSS 背景图检查
for m in re.finditer(r'url\("([^"]+)"\)', (ROOT / "index.html").read_text(encoding="utf-8")):
    t = (ROOT / m.group(1)).resolve()
    if not t.exists(): errors.append(f"index.html: CSS 背景图缺失 {m.group(1)}")

# 内部链接 HTTP 可达
dead = []
for t in sorted(all_internal):
    if not t.exists(): dead.append(f"{t.relative_to(ROOT)} (文件不存在)"); continue
    rel = t.relative_to(ROOT).as_posix()
    code = urllib.request.urlopen(f"{BASE}/{rel}").getcode()
    if code != 200: dead.append(f"{rel} (HTTP {code})")
for d in dead: errors.append("死链: " + d)

# sitemap 与页面一致性
smap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
n_urls = smap.count("<url>")
print(f"页面 {len(pages)} 个 | 内部链接目标 {len(all_internal)} 个 | sitemap {n_urls} 条")
print(f"robots.txt {'OK' if (ROOT/'robots.txt').exists() else '缺失'} | llms.txt {'OK' if (ROOT/'llms.txt').exists() else '缺失'}")
if warnings: print("警告:"); [print("  -", w) for w in warnings]
if errors: print("错误:"); [print("  -", e) for e in errors]; sys.exit(1)
print("全部通过 ✓")
