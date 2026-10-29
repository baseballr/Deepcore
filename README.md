# Deepcore Quarry

Deepcore Quarry is a Minecraft Bedrock add-on: powered quarries, machines in three tiers, power networks,
item pipes, crates, gear and a mining dimension.

**Wiki:** https://baseballr.github.io/Deepcore/
**Download:** the [latest release](https://github.com/baseballr/Deepcore/releases/latest).

## How the wiki is built

The wiki is a Blazor WebAssembly site in `src/DeepcoreWiki`. Its pages are not written by hand:
`tools/extract.py` opens the `.mcaddon` in `addon/`, reads the in-game Guide Book
(`DQ_BP/scripts/guide_data.js`), the block and item definitions and the textures, and writes
`wwwroot/data/wiki.json`, `wwwroot/data/release.json` and the icons.

On every push to `main`, `.github/workflows/deploy.yml`:

1. creates the GitHub release `v<version>` with the `.mcaddon` attached, if it doesn't exist yet,
2. runs the extractor,
3. publishes the Blazor app and deploys it to GitHub Pages.

## Publishing a new version

1. Delete the old `.mcaddon` from `addon/` and copy the new one in.
2. Update `addon/release.json`: `version`, `file`, `notes`, and `minecraftMin` / `minecraftMax`
   (lowest and highest Minecraft Bedrock version it works on).
3. Commit and push to `main`.

The extractor stops the build if `release.json` and the pack's manifest disagree on the version.

## Running locally

```sh
pip install pillow
python3 tools/extract.py
cd src/DeepcoreWiki && dotnet run
```

Vanilla ingredient icons are cached in `tools/vanilla/`. To add icons for new vanilla ingredients, unpack the
`minecraft-textures` npm package and run `python3 tools/extract.py --vanilla-src path/to/package`.
