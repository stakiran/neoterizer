#!/usr/bin/env python3
import json, os, re
# --- Preprocess: mask sensitive fields ---
IN  = "neoterizer.json"
MID = "neoterizer_masked.json"
with open(IN, encoding="utf-8") as f:
    data = json.load(f)
for u in data.get("users", []):
    for key in ("id","email"):
        if key in u:
            u[key] = "X"*len(u[key])
with open(MID, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
# --- Helpers ---
def writable(name):
    return re.sub(r'[\\/:*?"<>| ]', "_", name)
# detect illegal filename chars including space
# build title→filename map
pages = data.get("pages", [])
title2file = {p["title"]: writable(p["title"])+".md" for p in pages}
# convert lines
def convert_lines(lines):
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        # skip empty lines => emit blank
        if not line.strip():
            out.append("")
            i += 1
            continue
        # code block?
        m = re.match(r'^code:(\S+)$', line.strip())
        if m:
            ext = m.group(1).split(".")[-1]
            out.append(f"```{ext}")
            i += 1
            # consume indented lines
            while i<n and (lines[i].startswith(" ") or lines[i].startswith("\t")):
                out.append(lines[i].lstrip())
                i += 1
            out.append("```")
            continue
        # table?
        if line.startswith("table:"):
            name = line[len("table:"):]
            rows = []
            i += 1
            while i<n and (lines[i].startswith("\t") or lines[i].startswith(" ")):
                # split by tab
                cells = re.split(r'\t+', lines[i].strip())
                rows.append(cells)
                i += 1
            # make markdown table
            if rows:
                # header
                out.append("| " + " | ".join(rows[0]) + " |")
                out.append("| " + " | ".join("---" for _ in rows[0]) + " |")
                for r in rows[1:]:
                    out.append("| " + " | ".join(r) + " |")
            continue
        # inline adjustments: gyazo image
        gy = re.match(r'^\[https://gyazo\.com/([0-9a-fA-F]+)\]$', line.strip())
        if gy:
            img = f"https://gyazo.com/{gy.group(1)}.png"
            out.append(f'<img src="{img}" />')
            i += 1
            continue
        # project link [/proj]
        pr = re.match(r'^\[/([^/\]]+)\]$', line.strip())
        if pr:
            proj = pr.group(1)
            out.append(f'🌎️[{proj}](https://scrapbox.io/{proj})')
            i += 1
            continue
        # external link [text URL] or [URL text]
        ex = re.match(r'^\[([^\]]+)\]$', line.strip())
        if ex:
            parts = ex.group(1).split()
            if len(parts)==2 and parts[0].startswith("http"):
                # [URL text]
                url,text = parts
                out.append(f'🌎️[{text}]({url})')
                i+=1; continue
            if len(parts)==2 and parts[1].startswith("http"):
                # [text URL]
                text,url = parts
                out.append(f'🌎️[{text}]({url})')
                i+=1; continue
        # internal link [title]
        il = re.findall(r'\[([^\]\.]+)\]', line)
        if il:
            def repl(m0):
                t = m0.group(1)
                if t.endswith(".icon"): return m0.group(0)
                if t in title2file:
                    fn=title2file[t]
                    return f'[{t}]({fn})'
                return m0.group(0)
            line = re.sub(r'\[([^\]]+)\]', repl, line)
        # inline icon [xxxx.icon]
        icon = re.findall(r'\[([^\]]+)\.icon\]', line)
        if icon:
            def ir(m0):
                name=m0.group(1)
                fn = title2file.get(name, name+".md")
                # placeholder small img
                return f'<a href="{fn}"><img src="{name}.png" alt="{name}" width="16"/></a>'
            line = re.sub(r'\[([^\]]+)\.icon\]', ir, line)
        # heading vs list vs paragraph
        indent = len(line) - len(line.lstrip(" \t　"))
        text = line.strip()
        if indent==0:
            out.append(f"# {text}")
        else:
            # indent>0 => list
            if indent == 1:
                spaces = ""
            else:
                spaces = " " * ((indent-1)*4)
            out.append(f"{spaces}- {text}")
        i += 1
    return out

# write docs
odir = "docs"
os.makedirs(odir, exist_ok=True)
for p in pages:
    title = p["title"]
    fn = title2file[title]
    md = []
    md.extend(convert_lines(p.get("lines", [])))
    path = os.path.join(odir, fn)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
print("Generated docs/ with Markdown files.")
