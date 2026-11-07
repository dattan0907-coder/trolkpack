# Troll Pack → NeoForge 1.21.1 (GeckoLib)

Port of Little Room's *Troll Pack* (Paper: MythicMobs + ModelEngine) to a NeoForge 1.21.1 mod.

## Build
Needs JDK 21 and internet. `./gradlew build` (add the Gradle wrapper with `gradle wrapper` first), jar in `build/libs`.
`gradle.properties` pins `neo_version=21.1.172`, `geckolib_version=4.7.5` and `build.gradle` uses ModDevGradle `2.0.78`.
**These were not test-resolved** — bump them to the latest 21.1.x / 4.x / 2.x if Gradle can't find them.
GeckoLib is a required dependency (put the GeckoLib jar in `mods/`).

## What was converted automatically (`tools/convert_bbmodel.py`)
Re-run with `python3 tools/convert_bbmodel.py <unzipped TROLLPACK> src/main/resources/assets/trollpack`.
- 9 `.bbmodel` -> GeckoLib `geo.json` + `animation.json` (troll, elite, voodoo, chief, pig, pot, totem, bedmat, throne)
- all textures of a model are merged into one atlas (GeckoLib binds one texture per model); voodoo's `_e` texture -> `_glowmask`
- `lr_troll_parts` / `lr_troll_pots_parts` (ModelEngine `changepart` skins, heads, armor, shield, spear, gold tusks) -> hidden "alt" bones that are sibling bones of the bone they replace and share its animation
- hitbox sizes from the `hitbox` bones, sounds, item models (custom_model_data 1-8 -> real items)

## Java (`src/main/java/com/trollpack`)
Replaces the MythicMobs skills: troll variants (`TrollVariant`), melee, spear throw, leap attack, sit/sleep,
elite dance (golden apple), voodoo spell (tracking skull + chain), chief hand_out, decor interactions
(rotate = right-click, remove = sneak + right-click, pig drops cooked porkchop, pot nudges), spawn eggs for everything.

## Known gaps — not ported
- Health bar above heads (`lr_healthbar`), name-tag bone, NPC greeting bubble (`npcgreeting`)
- Foraging / eating / campfire / swimming-up behaviours, mushroom/berry markers, sit_getup / sleep_getup transitions
- Troll "skin" scoreboard logic beyond appearance, factions, threat table; chief throne seating
- Helmet items are plain items (no worn-on-head rendering); troll_shield has a `blocking` model override only
- ~116 hair-top/bottom faces use a 90°/270° UV rotation that GeckoLib geo can't express (they render un-rotated)
- Elite's head is hidden in Blockbench (a helmet item was attached in ModelEngine); here the head is shown
- Nothing was compiled or run in the build sandbox (no Maven access): expect to fix a few API-signature errors
  and eyeball the models in-game (first suspects: head-bone look rotation sign, catmullrom `lerp_mode` support).

Original art/sounds © Little Room (patreon.com/littleroomdev) — check their license before redistributing.
