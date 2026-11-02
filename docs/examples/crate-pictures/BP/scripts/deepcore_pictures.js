// Tells Deepcore which picture (dq:icon number) each of your items is. Import this from your main script.
import { system, world } from "@minecraft/server";

world.afterEvents.worldLoad.subscribe(() => {
  system.sendScriptEvent("dq:add_icon", JSON.stringify({
    entity: "ee:dq_icons",
    icons: { "ee:ruby": 1, "ee:essence_dust": 2 },
  }));
});
