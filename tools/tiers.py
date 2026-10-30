"""Wiki-only pages about tiers, added to the Guide Book text by extract.py.

The Guide Book explains each tier ladder where it lives, but nothing in it lists them all, and the Steel and
Deepcore machines (which have no crafting recipe) are only mentioned on the Machine tiers page. This adds:

  * an "All tiers" page at the top of Progression: every tier ladder in the add-on, in one table,
  * a "Tiers" section on every machine that takes Machine Upgrades (and on Tanks),
  * a table and the missing facts (lanes, bonus dust, no recipe) on the Machine tiers page.

The text uses the Guide Book's format plus three wiki-only marks that extract.py understands:
  [[Entry name]]          a link to that wiki page
  @icons A | B | C        a row of block or item icons with their names
  @table                  a table: the next lines are rows of cells split by "|", the first row is the header,
                          and a blank line ends it

The numbers come from the add-on's code (core.js TIERS / TIER_CHIPS / LANES / CONFIG / RANGE_STEP, recipes.js
TIER_BONUS, quarry.js CONTROLLERS, tanks.js). Keep them in step when those change.
"""

GET = {
    0: "Craft it",
    1: "[[Steel Machine Upgrade]] on a Basic one",
    2: "[[Deepcore Machine Upgrade]] on a Steel one",
}
TIERS = ["Basic", "Steel", "Deepcore"]
SAVED = {3: "45%", 4: "60%", 5: "75%"}  # Efficiency Chips: 15% less power each

LANED = ["Electric Furnace", "Crusher", "Plate Press", "Gear Press", "Wire Mill", "Washer", "Purifier", "Sifter"]
ONE_LANE = ["Induction Smelter", "Assembler"]
RANGED = {  # entry: (what Range Chips raise, value at Basic / Steel / Deepcore)
    "Item Vacuum": ("Largest radius", ["16 blocks", "20 blocks (+4 per chip)", "24 blocks"]),
    "Mob Repeller": ("Largest radius", ["32 blocks", "40 blocks (+8 per chip)", "48 blocks"]),
    "Chunk Loader": ("Largest area", ["7 x 7 chunks", "9 x 9 chunks (+1 ring per chip)", "11 x 11 chunks"]),
    "Lava Pump": ("Reach", ["8 blocks", "12 blocks (+4 per chip)", "16 blocks"]),
}
BONUS = {"Washer": ["50%", "50%", "67%"], "Purifier": ["33%", "50%", "50%"]}


def an(name):
    return ("an " if name[0] in "AEIOU" else "a ") + name


def _lead(name):
    return (f"@icons {name} | Steel {name} | Deepcore {name}\n"
            f"Every {name} is §lBasic§r when you craft it. There is §lno crafting recipe§r for the Steel {name} or "
            f"the Deepcore {name}: place {an(name)}, hold a [[Steel Machine Upgrade]] and tap it to make it Steel, then "
            f"use a [[Deepcore Machine Upgrade]] on it to make it Deepcore. Tiers go in order, and the machine keeps its "
            f"tier (blue trim for Steel, teal for Deepcore) when you mine or wrench it. See [[Machine tiers]].")


def machine_section(name):
    lines = ["§6Tiers§r", _lead(name), ""]
    if name in RANGED:
        what, vals = RANGED[name]
        lines.append(f"A higher tier adds 2 chip slots: one more Efficiency Chip and one more Range Chip. Range Chips "
                     f"only fit from Steel up.")
        lines.append("\n@table")
        lines.append(f"Tier | How you get it | Chip slots | Efficiency Chips (power saved) | Range Chips | {what}")
        for t in range(3):
            lines.append(f"{TIERS[t]} | {GET[t]} | {3 + 2 * t} | {3 + t} ({SAVED[3 + t]}) | {t} | {vals[t]}")
        return "\n".join(lines)
    extra_cols = ""
    if name in LANED:
        extra_cols += " | Lanes (stacks at once)"
    if name in BONUS:
        extra_cols += " | Bonus dust chance"
    adds = "2 chip slots: one more Speed Chip and one more Efficiency Chip"
    if name in LANED:
        adds += ", and more lanes: it works several stacks side by side (see [[Factory lanes]]). Each busy lane pays its own power"
    if name in BONUS:
        adds += ". It also gets a better chance of a second dust"
    lines.append(f"A higher tier adds {adds}.")
    lines.append("")
    if name in ONE_LANE:
        lines.append(f"The {name} keeps one lane at every tier: Steel and Deepcore only give it more chip slots, so it "
                     f"can run faster and cheaper.")
    lines.append("\n@table")
    lines.append(f"Tier | How you get it | Chip slots | Speed Chips (fastest) | Efficiency Chips (power saved){extra_cols}")
    for t in range(3):
        row = f"{TIERS[t]} | {GET[t]} | {6 + 2 * t} | {3 + t} ({4 + t}x as fast) | {3 + t} ({SAVED[3 + t]})"
        if name in LANED:
            row += f" | {[1, 3, 5][t]}"
        if name in BONUS:
            row += f" | {BONUS[name][t]}"
        lines.append(row)
    return "\n".join(lines)


TESSERACT = """§6Tiers§r
@icons Tesseract | Steel Tesseract | Deepcore Tesseract
There is §lno crafting recipe§r for the Steel or Deepcore Tesseract: use a [[Steel Machine Upgrade]] on a placed Tesseract, then a [[Deepcore Machine Upgrade]]. It keeps its tier when mined. Each tier adds 2 chip slots: one more Speed Chip and one more Efficiency Chip.
@table
Tier | How you get it | Chip slots | Speed Chips (most it moves a second) | Efficiency Chips (loss and item cost cut)
Basic | Craft it | 6 | 3 (4,000 power, 64 items) | 3 (60%)
Steel | [[Steel Machine Upgrade]] on a Basic one | 8 | 4 (5,000 power, 80 items) | 4 (80%)
Deepcore | [[Deepcore Machine Upgrade]] on a Steel one | 10 | 5 (6,000 power, 96 items) | 5 (free)"""

TANKS = """§6Tiers§r
@icons Tank | Steel Tank | Deepcore Tank
@table
Tier | Holds | How you get it
Tank | 16 buckets | Craft it
Steel Tank | 32 buckets | [[Steel Machine Upgrade]] on a placed Tank (keeps what it holds), or craft it around a Tank
Deepcore Tank | 64 buckets | [[Deepcore Machine Upgrade]] on a placed Steel Tank (keeps what it holds), or craft it around a Steel Tank

The [[Ender Tank]] has no tiers: every Ender Tank on the same colours shares 64 buckets."""

MACHINE_TIERS = """§6Which machines have tiers§r
@table
Machine | Basic | Steel | Deepcore | A higher tier also gives
[[Electric Furnace]], [[Crusher]], [[Plate Press]], [[Gear Press]], [[Wire Mill]], [[Sifter]] | 6 slots: 3 Speed, 3 Efficiency | 8 slots: 4 Speed, 4 Efficiency | 10 slots: 5 Speed, 5 Efficiency | Lanes: 1, 3, 5 stacks at once
[[Washer]] | 6 slots | 8 slots | 10 slots | Lanes 1, 3, 5. Bonus dust 50%, 50%, 67%
[[Purifier]] | 6 slots | 8 slots | 10 slots | Lanes 1, 3, 5. Bonus dust 33%, 50%, 50%
[[Induction Smelter]], [[Assembler]] | 6 slots: 3 Speed, 3 Efficiency | 8 slots: 4 Speed, 4 Efficiency | 10 slots: 5 Speed, 5 Efficiency | Chip slots only (one lane)
[[Item Vacuum]], [[Mob Repeller]], [[Chunk Loader]], [[Lava Pump]] | 3 slots: 3 Efficiency | 5 slots: 4 Efficiency, 1 Range | 7 slots: 5 Efficiency, 2 Range | A bigger radius or reach from Range Chips
[[Tesseract]] | 6 slots | 8 slots | 10 slots | Up to 6,000 power and 96 items a second

§6Getting a Steel or Deepcore machine§r
Steel and Deepcore machines have §lno crafting recipe§r, so a normal crafting table never shows them. The Deepcore Crafting Table lists them so you can look them up, but marks them red with "no crafting recipe". The only way to get one is to place the Basic machine and use a [[Steel Machine Upgrade]] on it, then a [[Deepcore Machine Upgrade]]. After that it is its own block: mine or wrench it and it drops as the Steel or Deepcore machine, and places back at that tier.

§6What does not have machine tiers§r
Generators, Solar Panels, turbines, the Geo Scanner, the Power Converter, the Chargepad, crates and network blocks take no Machine Upgrades. Quarry controllers, crates, tanks, batteries, cables and pipes have tier ladders of their own: see [[All tiers]]."""

ALL_TIERS = """§6All tiers§r
Deepcore has a few different kinds of tiers. This page lists every one of them; each name links to the page with the details.

§6The progression tiers§r
Every machine is crafted around a §lMachine Casing§r, and each casing is crafted around the one below it, so you unlock things in order: by hand (T0), Basic Casing (T1), Steel Casing (T2), Hardened Casing (T3), Deepcore Casing (T4). See [[Tiers]] for what each one unlocks.

§6Machine tiers: Basic, Steel and Deepcore§r
@icons Assembler | Steel Assembler | Deepcore Assembler
Every machine that takes chips is Basic when crafted. Use a [[Steel Machine Upgrade]] on the placed machine to make it Steel, then a [[Deepcore Machine Upgrade]] to make it Deepcore. Each tier adds 2 chip slots, so the machine can run faster and on less power, and ore machines also get more lanes and more bonus dust. Steel and Deepcore machines have no crafting recipe: an upgrade is the only way to make one. See [[Machine tiers]].

§6Everything with tiers§r
@table
What | Tiers | What a higher tier gives | How to move up
[[Machine tiers|Machines]] (15 kinds) and the [[Tesseract]] | Basic, Steel, Deepcore | 2 more chip slots; lanes and bonus dust on ore machines | A Machine Upgrade on the placed machine
[[Tanks]] | Tank, Steel Tank, Deepcore Tank | Holds 16, 32, 64 buckets | A Machine Upgrade on the placed tank, or craft around the smaller tank
[[Quarry Controllers]] | Basic, Reinforced, Deepcore | Dig area up to 12 x 12, 24 x 24, 36 x 36; 3, 6, 10 chip slots; 2, 4, 6 blocks a second | Craft the bigger controller
[[Deep Storage Crates]] | Steel, Hardened, Deepcore | Holds 8,192, 32,768, 131,072 of one item | A Hardened Casing on a Steel Crate, a Deepcore Casing on a Hardened one (keeps what it holds)
[[Battery Banks]] | Stone, Copper, Iron, Gold, Redstone, Diamond, Netherite | Stores 6,400 doubling each tier up to 409,600, and charges faster | Craft the bank in the middle of the next tier's ring
[[Power Cables]] | Copper, Iron, Gold, Redstone, Diamond, Netherite | Carries 100, 250, 500, 1,000, 2,000, 6,000 power a second | Craft one cable with the next material
[[Item Pipes]] | Wooden, Stone, Copper, Iron, Gold, Redstone, Diamond, Netherite | Moves 2, 4, 8, 12, 20, 32, 48, 96 items a second | Craft one pipe with the next material
[[Induction Matrix|Matrix Cells]] | Steel, Deepcore | Stores 2,000,000 or 8,000,000 power | Craft (a Deepcore Cell uses Steel Cells)
[[Machine Casings]] | Basic, Steel, Hardened, Deepcore | Unlocks the next machines | Craft around the casing below
[[Circuits]] | Basic, Advanced, Elite | Ingredients for higher-tier recipes | Craft
[[Jetpack]] | Jetpack, Deepcore Jetpack | Holds 40,000 or 80,000 power; the Deepcore one climbs faster and can hover | Craft around a Jetpack
[[Deepcore Drill]] | Deepcore Drill, Mk II | Vein mode up to 64 or 128 blocks, Tunnel mode 3 x 3 or 5 x 5 | Craft around the Drill
[[Portable Terminal]] | Portable, Deepcore Portable | Reaches the Network Core in its own dimension, or from any dimension | Craft around the Portable Terminal
[[Teleporter Pad]] | Teleporter Pad, Deepcore Teleporter Pad | Reaches pads in its own dimension, or in every dimension | Craft around a Teleporter Pad

§6Chips and tiers§r
Speed and Efficiency Chips fit 3 to a Basic machine, 4 to a Steel one and 5 to a Deepcore one (see [[Speed Chip]] and [[Efficiency Chip]]). Range Chips fit 3 to a quarry controller, and 1 or 2 to a Steel or Deepcore Item Vacuum, Mob Repeller, Chunk Loader or Lava Pump (see [[Range Chip]]). Quarry controllers have their own chip slots and take no Machine Upgrades."""


def apply(guide):
    """Adds the tier pages and sections to the parsed Guide Book (a list of categories). Returns warnings."""
    entries = {e["name"]: e for c in guide for e in c["entries"]}
    warn = []

    def append(name, text):
        if name in entries:
            entries[name]["body"] = entries[name]["body"].rstrip() + "\n\n" + text
        else:
            warn.append(f"tiers.py: no Guide Book entry called {name!r}")

    for name in LANED + ONE_LANE + list(RANGED):
        append(name, machine_section(name))
    append("Tesseract", TESSERACT)
    append("Tanks", TANKS)
    append("Machine tiers", MACHINE_TIERS)

    prog = next((c for c in guide if c["title"] == "Progression"), None)
    if prog is None:
        warn.append("tiers.py: no Progression category for the All tiers page")
    else:
        prog["entries"].insert(0, {"name": "All tiers", "body": ALL_TIERS})
    return warn
