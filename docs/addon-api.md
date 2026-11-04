# Deepcore for add-on makers

Other add-ons can plug into Deepcore Quarry with **script events**. They are one-way messages: your script sends one,
and Deepcore reads it if it is installed. If Deepcore is not installed, nothing happens.

Deepcore does not save what you send. Send it again every time the world loads, for example in
`world.afterEvents.worldLoad`:

```js
import { system, world } from "@minecraft/server";

world.afterEvents.worldLoad.subscribe(() => {
  system.sendScriptEvent("dq:add_recipe", JSON.stringify([ /* recipes */ ]));
  system.sendScriptEvent("dq:add_ore", JSON.stringify([ /* ores */ ]));
  system.sendScriptEvent("dq:add_icon", JSON.stringify({ /* crate pictures */ }));
  system.sendScriptEvent("dq:add_smelt", JSON.stringify([ /* furnace recipes */ ]));
});
```

Each event takes one object or a list of them. Anything Deepcore refuses is written to the content log as
`[DQ] dq:add_…: reason`.

Deepcore's own `dq:` items can't be changed with these events. `dq:add_ore` and `dq:add_icon` also refuse `minecraft:`
ids, so use them only for your own add-on's blocks and items.

Some things need no script at all: see [Item tags](#item-tags-food-in-pipe-filters-since-4720).

## dq:add_recipe: crafting recipes (since 4.61.0)

After you send a recipe, Deepcore's Network Crafter can order the item, Assemblers can make it, and the Deepcore
Crafting Table shows it.

```json
{ "o": "ee:example", "n": 1, "s": ["###", "###", "###"], "k": { "#": "ee:example_essence" }, "name": "Example" }
```

| Field | Meaning |
| --- | --- |
| `o` | The item it makes |
| `n` | How many it makes, 1 to 64 (default 1) |
| `s` + `k` | A shaped recipe: up to 3 rows, and a key from each letter to an item id |
| `i` | A shapeless recipe instead: a list of 1 to 9 item ids |
| `name` | The name to show (optional) |

## dq:add_ore: ores (since 4.61.0)

After you send an ore, the Geo Scanner, its hologram and the Mining Suit's Ore Sense count it.

```json
{ "k": "essence", "name": "Essence", "blocks": ["ee:essence_ore", "ee:deepslate_essence_ore"], "rgb": [0.4, 0.9, 0.6] }
```

| Field | Meaning |
| --- | --- |
| `k` | A key that groups the blocks in results: 1 to 32 characters, using only `a-z`, `0-9` and `_` |
| `blocks` | Your ore block ids, for example the stone and deepslate versions |
| `name` | The name to show (optional) |
| `rgb` | The hologram colour, 0 to 1 or 0 to 255 (optional) |

## dq:add_icon: pictures on crate fronts (since 4.65.0)

Deep Storage Crates already store items from any add-on, as long as they are plain stackable items. The front of a
crate shows a picture of the item and how many there are. Bedrock only draws textures that a resource pack lists ahead
of time, so Deepcore can't draw your item textures. Your items show a **?** plate until you give Deepcore a picture.

To give Deepcore pictures, your add-on ships one small **picture entity**. It uses your textures on Deepcore's
`geometry.dq_crate_icon`. An `int` property named `dq:icon` picks the picture: 1 is your first picture, 2 the second,
and so on, with 0 meaning nothing. Then tell Deepcore which number is which item:

```json
{ "entity": "ee:dq_icons", "icons": { "ee:ruby": 1, "ee:essence_dust": 2 } }
```

When a crate holds `ee:ruby`, Deepcore hides its own picture, puts your entity on the same spot facing the same way,
and sets its `dq:icon` to 1. Deepcore removes the entity when the crate changes item, empties or is mined.

A complete example is in [`docs/examples/crate-pictures`](examples/crate-pictures):

- `BP/entities/dq_icons.json`: the entity. Copy the components exactly as they are, because they stop it from moving,
  being hit or taking damage. Set `dq:icon`'s `range` to `[0, number of pictures]`.
- `RP/entity/dq_icons.entity.json`: lists your textures and uses `geometry.dq_crate_icon` with the
  `entity_alphatest` material.
- `RP/render_controllers/dq_icons.render_controllers.json`: `Array.icon` lists your textures in number order. Its
  first entry is a placeholder for 0, so for 2 pictures the array has 3 entries.
- `BP/scripts/deepcore_pictures.js`: sends the event when the world loads.

Rules:

- Deepcore keeps its own picture for items it already has one for, such as UtilityCraft and Tiered Machinery items.
- If your entity can't be spawned (for example, a misspelt id), your items show **?** and Deepcore stops trying until
  you send the event again.
- If a number is outside your `dq:icon` range, that one item shows **?** and the content log says so.
- A picture is 16 x 16, the same size as an inventory icon, so your item textures work as they are.

## dq:add_smelt: Electric Furnace recipes (since 4.72.0)

Deepcore's Electric Furnace has its own recipe list and does not use the game's furnace recipes. After you send a
smelt, the Electric Furnace cooks it, the Robit smelts it, On demand furnaces can keep it stocked and network orders
can make it.

```json
{ "in": "minecraft:carrot", "out": "rc:roasted_carrot", "filter": "#rawfood" }
```

| Field | Meaning |
| --- | --- |
| `in` | The item that goes in (one in, one out). It can be a `minecraft:` item |
| `out` | The item it smelts into |
| `filter` | A pipe filter category, or a list of them, that `in` also joins (optional) |

`filter` takes `#ores`, `#raw`, `#gems`, `#stone`, `#soil`, `#wood`, `#rawfood`, `#cooked` or `#ingots`. Use it for
vanilla items you give a new furnace use, because you can't tag a vanilla item. With the example above, a pipe set to
`[Raw food]` sends carrots to the furnace only while your add-on is installed.

Rules:

- Items Deepcore's furnace already smelts keep Deepcore's recipe, and the first add-on to send a smelt for an `in` keeps it.
- `dq:` items can't be `in` or `out`.
- `out` must be an item that exists in the world.

## Item tags: food in pipe filters (since 4.72.0)

Your own items can join Deepcore's `[Raw food]` and `[Cooked food]` pipe filter categories with an item tag. This
needs no script and does nothing when Deepcore is not installed.

```json
"components": {
  "minecraft:tags": { "tags": ["dq:cooked_food"] }
}
```

| Tag | Pipe filter category |
| --- | --- |
| `dq:raw_food` | `[Raw food]` |
| `dq:cooked_food` | `[Cooked food]` |

A tag only sorts the item. To make the Electric Furnace cook your raw food, also send `dq:add_smelt`.
