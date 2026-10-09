# YOU NEED TO INSTALL THE MAJORA'S MASK RECOMPILED AND HAVE SONIC ADVENTURE DX ON STEAM FOR THIS MOD TO WORK

# Termina Adventure

Play **Majora's Mask: Recompiled** as Sonic, Tails, Knuckles, Amy, Big the Cat, or E-102 Gamma, and switch back to Link whenever you need Zelda's items, masks, or progression mechanics.

**Current build: 0.1.22 · Windows · Experimental**

Termina Adventure uses a companion mod for **Sonic Adventure DX**. Both games run together: the companion runs the original SADX character tasks against collision streamed from Majora's Mask, then sends movement and animation state back to Zelda, where the character models are rendered. The approach is inspired by [SkyCraft](https://github.com/chasmlol/SkyCraft).

## Features

- Six playable Sonic Adventure characters with their original models, animation motions, and character sound effects.
- Sonic's momentum, spindash, homing attacks, and homing chains against eligible enemies.
- Tails' flight and tail spin; Knuckles' glide, climbing, and punches; Amy's hammer attacks and running hammer vault.
- Big's facing-directed grapple, airborne stomp, and optional original fishing-rod swing.
- Gamma's shots and hover, with adjustable hover speed and firing rate.
- A standing emote for each character on **L**.
- A character-follow camera with adjustable response, compact control hints, and a single-screen settings menu.
- Switching from any Link mask form and returning to the underlying form.

No Super Sonic is included.

## Requirements

- **Zelda 64: Recompiled**, with Majora's Mask configured using your own supported ROM. The mod manifests require Recompiled **1.2.2 or newer**; compatibility with every newer release has not been tested.
- **Sonic Adventure DX for PC**, configured for the **SADX Mod Loader** through SAModManager. Development used the Steam installation converted for the mod loader.
- **MainMemory's Character Select Mod**, installed and enabled in SADX.
- Both games running at the same time, with SADX allowed to update while its window is inactive.

The export includes the two Zelda mods, native bridge DLL, SADX companion, recommended settings, launchers, and source. It does not include the games, ROM, save files, mod loader, or Character Select Mod.

## Installation

Close both games before replacing files. Back up any existing mod files and settings.

1. Copy all four files from the export's `Zelda64Recompiled/mods/` folder into Zelda Recompiled's mod directory:

   ```text
   termina_adventure-0.1.22.nrm
   termina_adventure_bridge-0.1.22.nrm
   termina_bridge.dll
   termina-adventure-settings.ini
   ```

2. Remove earlier versions of **these two Termina Adventure `.nrm` files**, leaving unrelated mods alone. Enable both supplied mods in Zelda's mod menu. Set **Original SADX physics**, **SADX character models**, and **Character HUD** to On, and **Starting character** to Link.
3. Copy the export's `SADX/mods/TerminaAdventureBridge/` folder into SADX's `mods/` directory.
4. In SAModManager, enable **Termina Adventure SADX Companion** and **Character Select Mod**. Place the companion **before Character Select Mod** in the load order, then save/apply the profile.
5. Disable SADX's **Pause on inactive window** setting. Keep its sound effects volume audible; the companion mutes stage music separately.
6. Copy **Launch SADX Companion.cmd** beside `sonic.exe`, and **Launch Termina Adventure.cmd** beside `Zelda64Recompiled.exe`. Launch the SADX companion first, then Zelda. Keep both running while playing.

For a portable Zelda installation, the mod directory is the `mods/` folder beside `Zelda64Recompiled.exe`. For other installations, use the game's mod-folder location.

Existing settings can override defaults. Copying the supplied INI replaces the mod's saved settings with the defaults below; back up your old INI first if you want to keep it.

## Controls

Button names refer to the **N64 controls mapped in Zelda Recompiled**, not keyboard keys or the labels printed on your physical controller.

| Input | Action |
| --- | --- |
| R + D-pad Left / Right | Switch character |
| R + D-pad Up | Return to Link |
| Z + D-pad Down | Open or close settings |
| R + D-pad Down | Alternate settings shortcut |
| L while standing still | Character emote |

In settings, **D-pad Up/Down** selects an option, **Left/Right** adjusts it, and **B or Start** saves and closes.

| Character | Abilities |
| --- | --- |
| **Sonic** | A jumps. Release and press A again in the air to home toward an eligible enemy; release/press again after a bounce to chain. Hold B on the ground to charge a spindash, then release to launch. |
| **Tails** | A jumps. Release A, then press A again in the air and hold to fly. Release to descend. B performs a tail spin. Holding the initial jump does not start flight. |
| **Knuckles** | A jumps; hold A to glide or latch near a surface. Use the stick to climb. Release A or press B to drop. B punches when not climbing. |
| **Amy** | A jumps. B uses the hammer; hold B for a spinning hammer attack. Build running speed and press B for a hammer vault. |
| **Big** | A jumps. On the ground, B grapples in Big's facing direction. In the air, tap/release B to grapple or hold B for about 0.25 seconds to stomp. A or a fresh B press cancels a pull. Disable **Big new mechanics** for B's original rod swing. |
| **E-102 Gamma** | A jumps; keep A held to hover during descent. Release to fall normally. B fires a Zelda-side shot; Z targeting aims at the selected enemy. |
| **Link** | Normal Zelda controls, items, masks, and progression actions. |

Emotes cancel when moving or pressing A/B/L. Link retains his normal L behavior.

## Default settings

| Setting | Default |
| --- | --- |
| Starting character | Link |
| Original SADX physics / character models | On |
| Character speed / gravity | 100% / 100% |
| Camera follow speed | **25%** |
| Camera smoothing | On |
| Control hints | **On** |
| Character HUD | On, briefly after switching |
| Character sounds | On |
| SADX stage music | Muted |
| Knuckles climb any surface | On |
| Big new mechanics | On |
| Big grapple range / speed | Normal / Normal |
| Gamma hover speed | 100% |
| Gamma firing speed | Normal |
| Amy hammer jump height | 100% |

Character speed and gravity can be adjusted from **25% to 300%** in 25% increments. Gamma's horizontal hover speed goes up to **500%**. Gamma firing speed and Big grapple speed each have five named choices: **Slowest, Slow, Normal, Fast, Fastest**. Big grapple range uses **Shortest, Short, Normal, Long, Longest**.

The export's defaults are set in both the supplied INI and its compiled core mod. Preferences save to `termina-adventure-settings.ini` beside `termina_bridge.dll`.

## How the bridge works

```text
Majora's Mask: Recompiled                 Sonic Adventure DX
  Input + scene collision  ----------->    Companion character task
  Render model + apply pose <-----------    Movement + animation state
```

The Zelda side supplies input, nearby authored terrain, and gameplay state. The SADX side temporarily runs its character task against that mirrored terrain and returns its position, velocity, and animation state through shared memory. Zelda renders the extracted character model and handles host-game damage and progression integration.

The terrain observer and collision behavior retain the **0.1.18 baseline**. The companion also contains subsequent Tails input and animation fixes; its DLL is not byte-identical to 0.1.18.

## Building from source

The export's `Source/` directory includes project code, generated model/animation code, Zelda reference headers and symbols, and SADX SDK headers. Generated assets are already present, so re-extraction is unnecessary for that source export.

Use **Python 3**, **LLVM 18.1.8**, **Zig 0.13.0**, and **RecompModTool**. Run the following from the directory containing `mod.toml`, replacing tool paths with your installation paths:

```powershell
python tools/build.py --llvm "C:\tools\llvm18\bin" --mod-tool "C:\tools\RecompModTool.exe"
python tools/build.py --bridge --llvm "C:\tools\llvm18\bin" --mod-tool "C:\tools\RecompModTool.exe"
python tools/build_native.py --zig "C:\tools\zig-0.13.0\zig.exe" --sdk "dependencies/SADXModLoader/include"
```

These produce the two `.nrm` files in `build/` and the native DLLs in `build/native/`. Compiler binaries are separate prerequisites for rebuilding; playing the prebuilt mods does not require them.

A repository checkout may need its reference dependencies initialized and its model code generated from a local SADX installation. The export includes those source inputs. Historical test and installation scripts may reference the development workstation or older release archives; adjust those paths before using them.

**Do not build with `--restore-018-companion` for this version:** that option is for earlier builds and excludes the later Tails changes.

## Known limitations

This is an experimental integration. Collision on complex surfaces, moving platforms, water, and some camera angles still needs gameplay testing. Big's rod and grapple line are procedural, and full fishing mechanics are not implemented.

Character attacks integrate with Zelda's enemy damage handling, but not every enemy or boss interaction is verified. Shields, immunity, weak points, and progression requirements still apply. For example, thaw Goht using Link and fire arrows before switching characters.

Use Link for items, masks, and progression actions. Both games must remain running. Tests cover bridge behavior and controlled native movement, including Tails' second-press flight and rotor progression; they do not establish complete gameplay parity or verify every animation visually in Zelda.

## Credits and source notices

- [SkyCraft](https://github.com/chasmlol/SkyCraft) — inspiration for the cross-game passthrough approach.
- [Zelda 64: Recompiled](https://github.com/Zelda64Recomp/Zelda64Recomp) and [Zelda64RecompSyms](https://github.com/Zelda64Recomp/Zelda64RecompSyms).
- [zeldaret/mm](https://github.com/zeldaret/mm) — Majora's Mask reference source and headers.
- [SADX Mod Loader](https://github.com/X-Hax/sadx-mod-loader) and MainMemory's Character Select Mod.

Project code is accompanied by its [LICENSE](LICENSE). Third-party code, game models, animations, audio, and other assets retain their respective ownership; the project license does not grant rights to those assets. The source export contains generated game assets, so review the contents before publishing the entire export to GitHub. Keep ROMs, game executables, saves, and personal settings out of the repository.

# AI DISCLAIMER - THIS MOD IS AI SLOP OBVIOUSLY AND WAS MADE ALMOST ENTIRELY WITH CHATGPT AGENT MODE, DOWNLOAD ONLY IF YOU'RE OKAY WITH THAT
