#!/usr/bin/env python3
"""Builds the wiki data from the Deepcore .mcaddon.

Reads the guide book (DQ_BP/scripts/guide_data.js), the block and item
definitions and the textures, and writes:

  src/DeepcoreWiki/wwwroot/data/wiki.json     categories, entries, recipes
  src/DeepcoreWiki/wwwroot/data/release.json  latest download + Minecraft range
  src/DeepcoreWiki/wwwroot/img/icons/*.png    block and item icons

Usage: python3 tools/extract.py [--repo owner/name] [--vanilla-src DIR]

--vanilla-src points at an unpacked `minecraft-textures` npm package and
refreshes tools/vanilla/ (icons for vanilla ingredients). Without it the
cached icons in tools/vanilla/ are used.
"""
import argparse, html, io, json, re, shutil, subprocess, zipfile
from pathlib import Path
from PIL import Image

import tiers

ROOT = Path(__file__).resolve().parent.parent
WWW = ROOT / "src" / "DeepcoreWiki" / "wwwroot"
VANILLA = ROOT / "tools" / "vanilla"

# Sidebar groups, in order. Guide categories not listed land in "More".
GROUPS = [
    ("Getting started", ["Progression", "This book"]),
    ("Power", ["Power sources", "Power network", "Big power"]),
    ("Machines", ["Machines", "Ore processing", "Quarry", "Chips"]),
    ("Logistics", ["Pipes and logistics", "Materials"]),
    ("Gear and worlds", ["Gear", "Mining World"]),
]

# Entry names whose icon can't be found by name.
ICON_HINTS = {
    "Tiers": "Basic Machine Casing", "Machine Casings": "Basic Machine Casing",
    "Plates": "Iron Plate", "Gears": "Iron Gear", "Wire and Coils": "Copper Wire",
    "Alloys": "Steel Ingot", "Obsidian and Diamond Dust": "Obsidian Dust",
    "Circuits": "Basic Circuit", "Battery Banks": "Stone Battery Bank",
    "Power Cables": "Copper Power Cable", "Quarry Controllers": "Quarry Controller",
    "Item Pipes": "Iron Item Pipe", "Keeping a chest stocked": "Stock Upgrade",
    "Machine screens": "Crusher", "Machine tiers": "Steel Machine Upgrade",
    "On demand machines": "Assembler", "Deep Storage Crates": "Steel Crate",
    "Factory lanes": "Electric Furnace", "Machine sides": "Pipe Wrench",
    "Suit modules": "Mining Suit Helmet", "Mining World": "Portal Core",
    "Mining Portal": "Portal Frame", "Core Reactor": "Reactor Controller",
    "Induction Matrix": "Matrix Port", "Crate Network": "Network Core", "Dust": "Iron Dust",
    "Clean Dust": "Clean Iron Dust", "Pure Dust": "Pure Iron Dust",
    "Reactor parts": "Reactor Casing", "Mining Suit": "Mining Suit Helmet",
    "Deepcore Drill": "Deepcore Drill", "Jetpack": "Jetpack",
    "Tanks": "Tank", "All tiers": "Deepcore Machine Casing",
}

COLORS = set("0123456789abcdef")

# Entry name -> page href, filled in before the bodies are parsed, for [[links]] in the wiki-only text (tiers.py).
LINKS = {}
LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
bad_links = set()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def clean_name(s):
    s = s.split("\\n")[0].split("\n")[0]
    s = re.sub(r"§.", "", s)
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s)
    return s.strip()


class Pack:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.names = self.z.namelist()

    def find(self, suffix):
        for n in self.names:
            if n.endswith(suffix):
                return n
        raise FileNotFoundError(suffix)

    def read(self, name):
        return self.z.read(name)

    def json(self, name):
        txt = self.read(name).decode("utf-8-sig")
        txt = re.sub(r"^\s*//.*$", "", txt, flags=re.M)
        return json.loads(txt)

    def glob(self, prefix, ext=".json"):
        return [n for n in self.names if prefix in n and n.endswith(ext)]

    def image(self, base):
        for ext in (".png", ".tga"):
            for n in self.names:
                if n.endswith(base + ext) and "DQ_RP/" in n:
                    return Image.open(io.BytesIO(self.read(n))).convert("RGBA")
        return None


def tex_path(entry):
    t = entry["textures"]
    if isinstance(t, list):
        t = t[0]
    if isinstance(t, dict):
        t = t["path"]
    return t


def iso_cube(top, left, right, size=64):
    """Draws an isometric block icon from 16x16 faces."""
    s = size // 2
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    def face(img, coeffs, shade):
        img = img.resize((16, 16), Image.NEAREST)
        px = img.load()
        for y in range(16):
            for x in range(16):
                r, g, b, a = px[x, y]
                px[x, y] = (int(r * shade), int(g * shade), int(b * shade), a)
        big = img.resize((s * 4, s * 4), Image.NEAREST)
        return big.transform((size, size), Image.AFFINE, coeffs, Image.NEAREST)

    def affine(dst, src):
        # dst/src: three (x, y) pairs; returns coefficients mapping dst -> src.
        (x1, y1), (x2, y2), (x3, y3) = dst
        (u1, v1), (u2, v2), (u3, v3) = src
        det = x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)
        a = (u1 * (y2 - y3) + u2 * (y3 - y1) + u3 * (y1 - y2)) / det
        b = (u1 * (x3 - x2) + u2 * (x1 - x3) + u3 * (x2 - x1)) / det
        c = (u1 * (x2 * y3 - x3 * y2) + u2 * (x3 * y1 - x1 * y3) + u3 * (x1 * y2 - x2 * y1)) / det
        d = (v1 * (y2 - y3) + v2 * (y3 - y1) + v3 * (y1 - y2)) / det
        e = (v1 * (x3 - x2) + v2 * (x1 - x3) + v3 * (x2 - x1)) / det
        f = (v1 * (x2 * y3 - x3 * y2) + v2 * (x3 * y1 - x1 * y3) + v3 * (x1 * y2 - x2 * y1)) / det
        return (a, b, c, d, e, f)

    W = s * 4
    q = s / 2
    top_img = face(top, affine([(s, 0), (2 * s, q), (0, q)], [(0, 0), (W, 0), (0, W)]), 1.0)
    left_img = face(left, affine([(0, q), (s, 2 * q), (0, q + s)], [(0, 0), (W, 0), (0, W)]), 0.82)
    right_img = face(right, affine([(s, 2 * q), (2 * s, q), (s, 2 * q + s)], [(0, 0), (W, 0), (0, W)]), 0.64)
    for im in (left_img, right_img, top_img):
        out.alpha_composite(im)
    return out


def flat_icon(img, size=64):
    img = img.copy()
    if img.height > img.width:  # flipbook strip: first frame
        img = img.crop((0, 0, img.width, img.width))
    return img.resize((size, size), Image.NEAREST)


def span_html(text):
    """Turns §-formatted guide text into HTML spans."""
    out, open_tags = [], []
    parts = re.split(r"(§.)", text)
    for p in parts:
        if len(p) == 2 and p[0] == "§":
            code = p[1].lower()
            if code == "r":
                out.extend("</span>" for _ in open_tags)
                open_tags = []
            elif code in COLORS or code in "lo":
                out.append(f'<span class="mc-{code}">')
                open_tags.append(code)
        elif p:
            out.append(html.escape(p))
    out.extend("</span>" for _ in open_tags)
    return LINK.sub(link_html, "".join(out))


def link_html(m):
    target, label = m.group(1), m.group(2) or m.group(1)
    href = LINKS.get(html.unescape(target))
    if not href:
        bad_links.add(target)
        return label
    return f'<a href="{href}">{label}</a>'


def table_html(rows):
    head = "".join(f"<th>{span_html(c)}</th>" for c in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{span_html(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
    return f'<div class="table-wrap"><table class="wiki-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


GRID_HEAD = re.compile(r"^(.*?)rows from the top(?: \(makes (\d+)\))?:\s*$")
ROW = re.compile(r"^§7(\d+):§r\s*(.*)$")
H2 = re.compile(r"^§6(.+?)§r$")
H3 = re.compile(r"^§e(.+?)§r$")


def parse_body(body, entry_name, icon_for):
    lines = body.split("\n")
    blocks, para, i = [], [], 0
    sub = None

    def flush():
        nonlocal para
        if para:
            blocks.append({"t": "p", "html": "<br>".join(span_html(l) for l in para)})
            para = []

    while i < len(lines):
        line = lines[i]
        if line.startswith("@icons "):
            flush()
            cells = [c.strip() for c in re.split(r"\s+\|\s+", line[7:])]
            blocks.append({"t": "icons", "text": " ".join(cells),
                           "rows": [[{"name": c, "icon": icon_for(c)} for c in cells]]})
            i += 1
            continue
        if line.strip() == "@table":
            flush()
            rows = []
            i += 1
            while i < len(lines) and lines[i].strip():
                rows.append([c.strip() for c in re.split(r"\s+\|\s+", lines[i].strip())])
                i += 1
            blocks.append({"t": "table", "html": table_html(rows)})
            continue
        m = GRID_HEAD.match(line)
        if m:
            flush()
            rows = []
            i += 1
            while i < len(lines) and ROW.match(lines[i]):
                cells = [c.strip() for c in ROW.match(lines[i]).group(2).split("|")]
                rows.append([{"name": "" if c == "-" else c, "icon": None if c == "-" else icon_for(c)}
                             for c in cells])
                i += 1
            prefix = m.group(1).strip().rstrip(",")
            if blocks and blocks[-1]["t"] == "h3" and blocks[-1]["text"] == sub:
                blocks.pop()  # the grid card shows the subheading itself
            blocks.append({"t": "grid", "title": sub or entry_name, "note": prefix,
                           "makes": int(m.group(2) or 1), "rows": rows})
            continue
        m2, m3 = H2.match(line), H3.match(line)
        if m2:
            flush()
            if m2.group(1) != entry_name or blocks:
                blocks.append({"t": "h2", "text": m2.group(1)})
            sub = None
        elif m3:
            flush()
            sub = m3.group(1)
            blocks.append({"t": "h3", "text": sub})
        elif line.strip() == "":
            flush()
        else:
            para.append(line)
        i += 1
    flush()
    return blocks


def summary_of(body):
    for line in body.split("\n")[1:]:
        if line.strip() and not line.startswith("§"):
            s = re.sub(r"§.", "", line).strip()
            return s if len(s) < 180 else s[:177].rsplit(" ", 1)[0] + "…"
    return ""


def load_guide(pack):
    src = pack.read(pack.find("scripts/guide_data.js")).decode("utf-8")
    start = src.index("[", src.index("export const GUIDE"))
    # The file is a JSON array literal followed by ";".
    depth, end, in_str, esc = 0, None, False, False
    for j in range(start, len(src)):
        ch = src[j]
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
        elif ch == '"': in_str = True
        elif ch == "[": depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    return json.loads(src[start:end])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="baseballr/Deepcore")
    ap.add_argument("--vanilla-src")
    args = ap.parse_args()

    rel = json.loads((ROOT / "addon" / "release.json").read_text())
    pack = Pack(ROOT / "addon" / rel["file"])
    bp_manifest = pack.json(pack.find("DQ_BP/manifest.json"))
    ver = ".".join(map(str, bp_manifest["header"]["version"]))
    if ver != rel["version"]:
        raise SystemExit(f"addon/release.json says {rel['version']} but the pack is {ver}")

    icons_dir = WWW / "img" / "icons"
    if icons_dir.exists():
        shutil.rmtree(icons_dir)
    icons_dir.mkdir(parents=True)

    terrain = pack.json(pack.find("DQ_RP/textures/terrain_texture.json"))["texture_data"]
    itemtex = pack.json(pack.find("DQ_RP/textures/item_texture.json"))["texture_data"]
    lang = {}
    for line in pack.read(pack.find("DQ_RP/texts/en_US.lang")).decode("utf-8-sig").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            lang[k.strip()] = v.strip()

    names = {}  # display name -> icon file
    things = {"blocks": 0, "items": 0}

    def save(img, ident):
        fn = ident.replace(":", "_") + ".png"
        img.save(icons_dir / fn)
        return "img/icons/" + fn

    def tex(key, table):
        e = table.get(key)
        return pack.image(tex_path(e)) if e else None

    # Items first so a block's own item icon (if any) wins for odd shapes.
    item_icons = {}
    for f in pack.glob("DQ_BP/items/"):
        d = pack.json(f)["minecraft:item"]
        ident = d["description"]["identifier"]
        c = d.get("components", {})
        icon = c.get("minecraft:icon")
        if isinstance(icon, dict):
            icon = icon.get("texture") or (icon.get("textures") or {}).get("default")
        disp = (c.get("minecraft:display_name") or {}).get("value") or lang.get(f"item.{ident}") or lang.get(f"item.{ident}.name")
        if not icon or not disp:
            continue
        img = tex(icon, itemtex)
        if img is None:
            continue
        things["items"] += 1
        path = save(flat_icon(img), ident)
        placer = (c.get("minecraft:block_placer") or {}).get("block")
        if placer:
            item_icons.setdefault(placer, path)
        nm = clean_name(lang.get(disp, disp) if disp.startswith(("item.", "tile.")) else disp)
        if "dyed" not in ident:
            names.setdefault(nm, path)

    for f in pack.glob("DQ_BP/blocks/"):
        d = pack.json(f)["minecraft:block"]
        ident = d["description"]["identifier"]
        c = d.get("components", {})
        disp = (c.get("minecraft:display_name") or "")
        disp = lang.get(disp, "") if disp else ""
        disp = disp or lang.get(f"tile.{ident}.name", "")
        if not disp:
            continue
        things["blocks"] += 1
        geo = c.get("minecraft:geometry")
        geo = geo if isinstance(geo, str) else (geo or {}).get("identifier", "")
        mats = c.get("minecraft:material_instances") or {}
        def mt(*keys):
            for k in keys:
                if k in mats:
                    return tex(mats[k]["texture"], terrain)
            return None
        path = None
        if geo == "minecraft:geometry.full_block" and mats:
            front = mt("north", "*")
            side = mt("east", "west", "*")
            top = mt("up", "*")
            if front and side and top:
                path = save(iso_cube(top, front, side), ident)
        if path is None:
            path = item_icons.get(ident)
        if path is None and mats:
            img = mt("north", "*", "up")
            if img:
                path = save(flat_icon(img), ident)
        if path:
            names.setdefault(clean_name(disp), path)

    # Vanilla ingredient icons.
    vanilla_map = {}
    if args.vanilla_src:
        base = Path(args.vanilla_src) / "dist" / "textures"
        idx = json.loads((base / "manifest" / "index.json").read_text())
        latest = sorted(idx.get("versions", []), key=lambda v: [int(x) for x in re.findall(r"\d+", v)])[-1] if isinstance(idx, dict) and idx.get("versions") else "26.3"
        man = json.loads((base / "manifest" / f"{latest}.json").read_text())
        vanilla_map = {it["readable"]: base / "assets" / it["texture"] for it in man["items"]}
    VANILLA.mkdir(parents=True, exist_ok=True)
    vdir = WWW / "img" / "vanilla"
    if vdir.exists():
        shutil.rmtree(vdir)
    vdir.mkdir(parents=True)

    VANILLA_ALIAS = {"Oak Planks": "Oak Planks", "Any Planks": "Oak Planks", "Planks": "Oak Planks",
                     "Wool": "White Wool", "Dye": "White Dye", "Log": "Oak Log", "Any Log": "Oak Log",
                     "Diamond Block": "Block of Diamond", "Emerald Block": "Block of Emerald",
                     "Iron Block": "Block of Iron", "Lapis Block": "Block of Lapis Lazuli",
                     "Redstone Block": "Block of Redstone", "Gold Block": "Block of Gold",
                     "Ender Eye": "Eye of Ender", "Quartz": "Nether Quartz"}

    def vanilla_icon(name):
        n = VANILLA_ALIAS.get(name, name)
        cached = VANILLA / (slug(n) + ".png")
        if not cached.exists() and n in vanilla_map:
            shutil.copy(vanilla_map[n], cached)
        if not cached.exists() and n.endswith("s") and n[:-1] in vanilla_map:
            shutil.copy(vanilla_map[n[:-1]], cached)
        if cached.exists():
            dst = vdir / cached.name
            if not dst.exists():
                shutil.copy(cached, dst)
            return "img/vanilla/" + cached.name
        return None

    missing = set()

    def icon_for(raw):
        n = clean_name(raw)
        if not n:
            return None
        if n in names:
            return names[n]
        v = vanilla_icon(n)
        if v:
            return v
        missing.add(n)
        return None

    def entry_icon(name):
        for cand in (ICON_HINTS.get(name), name, clean_name(name), name.rstrip("s"), name + " Controller"):
            if cand and cand in names:
                return names[cand]
        for n, p in names.items():
            if n.startswith(name.rstrip("s")):
                return p
        return None

    def full_name(sub, entry):
        """'Stone' under 'Battery Banks' -> 'Stone Battery Bank' when that item exists."""
        if clean_name(sub) in names:
            return sub
        single = entry[:-1] if entry.endswith("s") else entry
        for cand in (f"{sub} {single}", f"{sub} {entry}", f"{sub} {single.split()[-1]}",
                     f"{sub.removesuffix(' pipe')} Item Pipe"):
            if clean_name(cand) in names:
                return cand
        return f"{single} ({sub})" if " " not in sub else sub

    guide = load_guide(pack)
    for w in tiers.apply(guide):
        print("Warning:", w)
    cats, recipes = [], []
    by_title = {c["title"]: c for c in guide}
    ordered = []
    for group, titles in GROUPS:
        for t in titles:
            if t in by_title:
                ordered.append((group, by_title.pop(t)))
    ordered += [("More", c) for c in by_title.values()]
    for _, c in ordered:
        for e in c["entries"]:
            LINKS.setdefault(e["name"], f"wiki/{slug(c['title'])}/{slug(e['name'])}")

    for group, c in ordered:
        cs = slug(c["title"])
        entries = []
        for e in c["entries"]:
            es = slug(e["name"])
            blocks = parse_body(e["body"], e["name"], icon_for)
            icon = entry_icon(e["name"])
            for b in blocks:
                if b["t"] == "grid":
                    title = full_name(b["title"], e["name"])
                    b["title"] = title
                    out_icon = names.get(clean_name(title)) or icon
                    b["icon"] = out_icon
                    recipes.append({"name": title if title != e["name"] else e["name"],
                                    "entry": e["name"], "cat": cs, "slug": es,
                                    "icon": out_icon, "makes": b["makes"], "rows": b["rows"]})
            if not icon:
                print("No entry icon:", e["name"])
            entries.append({"slug": es, "name": e["name"], "icon": icon,
                            "summary": summary_of(e["body"]), "blocks": blocks})
        cats.append({"slug": cs, "title": c["title"], "blurb": c.get("blurb", ""),
                     "group": group, "icon": entries[0]["icon"] if entries else None,
                     "entries": entries})

    wiki = {
        "version": ver,
        "stats": {"topics": sum(len(c["entries"]) for c in cats), "blocks": things["blocks"],
                  "items": things["items"], "recipes": len(recipes)},
        "categories": cats,
        "recipes": recipes,
    }
    (WWW / "data").mkdir(parents=True, exist_ok=True)
    (WWW / "data" / "wiki.json").write_text(json.dumps(wiki, ensure_ascii=False, separators=(",", ":")))

    repo = args.repo
    tag = "v" + ver
    release = dict(rel)
    release["tag"] = tag
    release["download"] = f"https://github.com/{repo}/releases/download/{tag}/{rel['file']}"
    release["releasePage"] = f"https://github.com/{repo}/releases/tag/{tag}"
    release["allReleases"] = f"https://github.com/{repo}/releases"
    release["sizeBytes"] = (ROOT / "addon" / rel["file"]).stat().st_size
    try:
        release["date"] = subprocess.check_output(
            ["git", "log", "-1", "--format=%cs", "--", "addon/release.json"], cwd=ROOT, text=True).strip() or None
    except Exception:
        release["date"] = None
    (WWW / "data" / "release.json").write_text(json.dumps(release, indent=2))

    # Pack icon for the header.
    for n in pack.names:
        if n.endswith("DQ_BP/pack_icon.png"):
            Image.open(io.BytesIO(pack.read(n))).save(WWW / "img" / "pack_icon.png")
            break

    lineup(pack, terrain, WWW / "img" / "lineup.png")

    print(f"v{ver}: {len(cats)} categories, {wiki['stats']['topics']} topics, {len(recipes)} recipes, "
          f"{len(names)} named icons")
    if missing:
        print("No icon for:", ", ".join(sorted(missing)))
    if bad_links:
        print("Warning: links to no page:", ", ".join(sorted(bad_links)))


def lineup(pack, terrain, dest):
    """A row of machine blocks for the home page hero."""
    picks = ["quarry_deepcore", "crusher", "induction_smelter", "assembler", "plate_press",
             "electric_furnace", "magma_generator", "washer", "fuel_generator", "geo_scanner"]
    tiles = []
    for p in picks:
        cand = [n for n in pack.names if n.endswith(f"DQ_BP/blocks/{p}.json")]
        if not cand:
            continue
        c = pack.json(cand[0])["minecraft:block"]["components"]
        mats = c.get("minecraft:material_instances") or {}
        def mt(*keys):
            for k in keys:
                if k in mats and mats[k]["texture"] in terrain:
                    return pack.image(tex_path(terrain[mats[k]["texture"]]))
            return None
        f, s, t = mt("north", "*"), mt("east", "*"), mt("up", "*")
        if f and s and t:
            tiles.append(iso_cube(t, f, s, 128))
    if not tiles:
        return
    W = 108 * (len(tiles) - 1) + 128
    out = Image.new("RGBA", (W, 128), (0, 0, 0, 0))
    for k, im in enumerate(tiles):
        out.alpha_composite(im, (108 * k, 0))
    out.save(dest)


if __name__ == "__main__":
    main()
