"""Record the installed revision and its actual validation boundaries."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1]

start='''TERMINA ADVENTURE - REVISION 0.1.2

1. Double-click Launch SADX Companion.cmd to see the original Sonic Adventure characters.
2. Double-click Launch Termina Adventure.cmd in this folder.
   SADX background updates are enabled so the companion runs while Zelda has focus.
3. Start Majora's Mask and choose FILE 2 (Link), the imported 100% test save.
   It skips the opening intro. Your previous FILE 1 is unchanged.
4. R + D-pad Right/Left: change character. R + D-pad Up: return to Link.
   The SADX companion automatically matches your selected Sonic character.
5. A: jump / air ability. B: character attack. No R modifier for abilities.
   Sonic: hold B on ground, release to spindash; A or B again in air to home/air-dash.
   Knuckles: hold A to glide onto a wall; stick to climb; A to jump away; B to punch.
6. Use Link for Zelda progression actions. Returning preserves your underlying mask form.

ROSTER: Link, Sonic, Tails, Knuckles, Amy, Big, E-102 Gamma. No Super Sonic.

For a standalone original SADX character preview, use a View SADX [character].cmd
launcher. Close an existing SADX session before launching another.

The SADX companion is installed and enabled. All six original character tasks
passed a live switching test. Zelda still uses the converted models and approximate
abilities; original SADX movement/world takeover is unfinished.
The shared model address bug has been corrected, but Zelda switching still needs
an in-game retest. Windows game-window capture timed out during this session.
If it crashes again, use Launch with diagnostics.cmd; the log goes to docs/game-diagnostics.log.
See docs/UPDATE-0.1.2.md for the exact changes and testing limits.

Save source: https://github.com/FSR-1/Zelda64Recompiled-100-save-file
Original save backup: save-backups/20261004T065133Z/mm.n64.us.1.0.bin

PowerShell launch commands:
'''
for name in ['Launch SADX Companion.cmd','Launch Termina Adventure.cmd']:
    start+='& "'+str(ROOT/name)+'"\n'
(ROOT/'START HERE.txt').write_text(start)

readme=ROOT/'README.md';text=readme.read_text()
text=text.replace('gameplay has not been verified in this session.','Zelda gameplay has not been verified in this session. All six original SADX character tasks passed a live companion switching test.')
text=text.replace('an optional SADX shared-memory observer','an installed SADX shared-memory companion')
text=text.replace('Double-click **Launch Termina Adventure.cmd** in this folder.','Double-click **Launch SADX Companion.cmd**, then **Launch Termina Adventure.cmd** in this folder. Choose File 2 for the imported 100% test save; File 1 was preserved. The companion matches your selected original SADX character through the installed Character Select mod.')
text=text.replace('The optional observer consists of','The companion consists of')
text=text.replace('The optional observer is compiled and cross-process tested, but not installed into your normal SADX installation. It exchanges state and nearby collision, and constructs SADX Ninja collision meshes. It does not yet install that geometry into an isolated stage or drive either game\'s player. The core runs independently of SADX once local models have been extracted.','The companion is installed and enabled in your active SADX profile after Character Select. Its original task switches for Sonic, Tails, Knuckles, Amy, Big and Gamma passed a live engine test. It also exchanges state and nearby collision and constructs SADX Ninja collision meshes. It does not yet install that geometry into an isolated stage or return original SADX movement to Zelda. Zelda still uses the converted models and approximate abilities. No Super Sonic is included.')
readme.write_text(text)

(ROOT/'docs/UPDATE-0.1.2.md').write_text('''# Revision 0.1.2

The reported Sonic and Knuckles crashes share the model renderer. Revision 0.1.1
used `gEXDisplayList`, which masks the model pointer to 28 bits. RT64 extended
RDRAM requires the high KSEG0 marker to bypass segmented addressing. Losing it
can translate an extended model address to unrelated display-list data.

The renderer now uses `gSPDisplayList`, preserving the full pointer. A regression
test using the actual GBI macros reproduces the previous incorrect translation
and passes for the corrected command across several extended-memory addresses.
The rebuilt 0.1.2 core is installed in the portable runtime. This establishes an
address bug correction, not proof that every reported gameplay crash is resolved.
Zelda game-window capture timed out on both attempts, so save loading, model
visibility and character switching remain unverified in the game.

## SADX companion

The 32-bit companion is installed at your SADX `mods/TerminaAdventureBridge`
folder and enabled last in the active Default profile. Other enabled mods and
settings were backed up under `install-backups`. Background updates are enabled
so the companion keeps running while Zelda has focus; other settings are preserved. The matching
Zelda bridge and 64-bit DLL are installed and enabled in the portable runtime.

The companion asks your existing Character Select mod to replace the actual
original character task, including its assets and physics. It does not just
change a character-ID byte. It displays connection status inside SADX.
`Launch SADX Companion.cmd` starts Station Square as Sonic; individual
`View SADX ...cmd` launchers preview each of the six original characters.

A live test started the actual installed SADX engine, published character
requests through the companion protocol, and verified fresh native task updates
for Sonic, Knuckles, Tails, Amy, Big, Gamma and Sonic again. All passed without
the game exiting. The temporary background-update setting was restored exactly.
See `sadx-live-test.json`. This tests original task replacement, not Zelda model
drawing or character movement over Zelda collision.

Original SADX movement taking over Zelda, active mirrored collision, enemy target
proxies, original attack routing and full guest-driven animation remain unfinished.
The Zelda-side A/B abilities and converted models remain the playable prototype.
The roster has no Super Sonic.

## Retest

Run both launchers and choose Zelda File 2. Switch through all six characters
with R + D-pad Left/Right, then return to Link with R + D-pad Up. If a crash
remains, run `Launch with diagnostics.cmd` to collect `game-diagnostics.log`.

## Sources inspected

- [RT64 extended/segmented address handling](https://github.com/rt64/rt64/blob/main/src/hle/rt64_rsp.cpp)
- [Official SADX Character Select implementation](https://github.com/X-Hax/SADXCharSel)
- [SADX Mod Loader SDK and callbacks](https://github.com/X-Hax/sadx-mod-loader)
''')

(ROOT/'docs/STATUS.md').write_text('''# Status: revision 0.1.2, crossover still in development

Installed October 4, 2026 for Zelda64 Recompiled 1.2.2 and the user's converted SADX.

## Verified

- Local SkyCraft architecture read; official recomp template and SDK references inspected.
- Six local SADX model trees, textures and selected animations extracted; CPU preview checked.
- Core and Zelda bridge compiled, accepted by RecompModTool and installed.
- Native 64-bit host / 32-bit guest bridge compiled and installed in both games.
- Actual cross-process state and collision conversion tests passed, including invalid data,
  stale state, abandoned mutex handling and Ninja mesh conversion.
- Real GBI-macro regression reproduces the previous model pointer bug and passes the fix.
- Original installed SADX engine switched to all six real character tasks and back to Sonic
  through companion requests; fresh task updates confirmed after each swap.
- Existing enabled SADX mods preserved; active profile backed up; temporary test setting restored.
- Portable Zelda File 2 contains a validated online completed save; File 1 preserved and backed up.

## Implemented, awaiting Zelda gameplay verification

- Converted character models, selected animation clips and original Link hiding/restoration.
- Any-mask-form switching; previous form preserved on returning to Link.
- Plain A/B abilities: Sonic charge/release and homing; Tails flight; Knuckles glide/climb/punch;
  Amy hammer; Big buoyancy/rod attack; Gamma hover/arrow-based shot.
- SADX companion selection follows the host character; status overlay and world receiver.

Windows game-window capture timed out twice. No blind UI interaction was used.
The address correction is tested independently; Zelda crash resolution and model appearance
must still be checked by loading a save and switching characters in the game.

## Remaining original-engine integration

- Isolated SADX mirror stage and safe installation/replacement of Zelda collision.
- Original guest movement/input stepping controlling the retained Zelda player puppet.
- Enemy target proxies, attack routing, guest-driven animation and original effects/upgrades.
- Big fishing, all original character mechanics and campaign compatibility.
- Full curled Sonic topology, original welding/shape animations and scene performance testing.

No Super Sonic is included. Original SADX movement is not yet controlling Zelda.
''')

research=ROOT/'docs/PASSTHROUGH-RESEARCH.md';text=research.read_text().replace('The observer does not replace SADX\'s current stage, inject inputs, select character tasks, or apply guest coordinates to Zelda.','The companion now selects original character tasks through the installed Character Select mod; all six passed a live engine test. It does not replace SADX\'s current stage, forward movement input, or apply guest coordinates to Zelda.')
research.write_text(text)
design=ROOT/'docs/DESIGN.md'
with design.open('a') as f:f.write('\n## Revision 0.1.2 companion boundary\n\nOriginal character matching is active through SADXCharSel, using its controller-selection\ncallback rather than writing character IDs. All six native task replacements passed a live\nSADX test. Existing mods remain enabled, so this is still a staging companion; the isolated\nmirror stage and original movement ownership described above remain unimplemented.\nZelda models now retain complete extended-RDRAM display-list pointers. See UPDATE-0.1.2.md.\n')

(ROOT/'release/observer/READ-ME-FIRST.md').write_text('''# Installed companion, revision 0.1.2

Both bridge components are installed in this user's portable Zelda runtime and
active SADX profile. Start `Launch SADX Companion.cmd`, then `Launch Termina Adventure.cmd`.
Selecting a Sonic character in Zelda requests the matching original SADX task
through the installed Character Select mod. Six original tasks passed a live test.

Zelda continues to use converted models and approximate abilities. Mirrored
collision activation and original SADX movement in Zelda remain unfinished.
See `../../docs/UPDATE-0.1.2.md` for evidence, backups and gameplay testing limits.
''')

report={'version':'0.1.2','installed_core':str(ROOT/'runtime/mods/termina_adventure-0.1.2.nrm'),
 'sha256':hashlib.sha256((ROOT/'runtime/mods/termina_adventure-0.1.2.nrm').read_bytes()).hexdigest(),
 'settings_preserved':True,'saves_preserved':True,'companion_installed':True,
 'sadx_original_character_switch_test':'passed all six and return',
 'zelda_gameplay_validation':'pending; Windows capture timed out','world_takeover_active':False}
(ROOT/'docs/update-install.json').write_text(json.dumps(report,indent=2)+'\n')
p=ROOT/'docs/companion-install.json';report=json.loads(p.read_text());report['in_game_validation']='SADX original six-character task switching passed; Zelda gameplay pending';p.write_text(json.dumps(report,indent=2)+'\n')
print('Revision documentation updated.')
