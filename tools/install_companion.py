"""Deploy the user's requested companion and enable its two existing profiles."""
import argparse
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--sadx',type=Path,required=True);args=p.parse_args()
    game=args.sadx.resolve()
    assert (game/'sonic.exe').is_file() and (game/'mods/.modloader/SADXModLoader.dll').is_file()
    profiles=game/'mods/.modloader/profiles'
    listing=json.loads((profiles/'Profiles.json').read_text())
    profile=(profiles/listing['ProfilesList'][listing['ProfileIndex']]['Filename']).resolve()
    assert profile.parent==profiles.resolve()
    original=profile.read_bytes();config=json.loads(original)
    assert 'Character Select Mod' in config['EnabledMods'],'Enable the installed Character Select Mod first'
    dll=ROOT/'build/native/TerminaAdventureSADX.dll'
    assert dll.read_bytes()[:2]==b'MZ'
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup=ROOT/'install-backups'/stamp;backup.mkdir(parents=True)
    shutil.copy2(profile,backup/profile.name)
    target=game/'mods/TerminaAdventureBridge';target.mkdir(exist_ok=True)
    for filename,source in [('TerminaAdventureSADX.dll',dll),('mod.ini',ROOT/'guest/mod.ini'),('config.ini',ROOT/'guest/config.ini')]:
        dest=target/filename
        if dest.exists(): shutil.copy2(dest,backup/filename)
        if filename!='config.ini' or not dest.exists(): shutil.copy2(source,dest)
        if filename=='config.ini':
            import configparser
            settings=configparser.ConfigParser();settings.optionxform=str;settings.read(dest)
            if not settings.has_section('Bridge'):settings.add_section('Bridge')
            settings.set('Bridge','ShowHUD','0')
            if not settings.has_option('Bridge','CharacterSounds'):settings.set('Bridge','CharacterSounds','1')
            if not settings.has_option('Bridge','MuteStageMusic'):settings.set('Bridge','MuteStageMusic','1')
            with dest.open('w') as handle:settings.write(handle)
    # Keep every existing mod; isolate raw input before Character Select sees it.
    for key in ['EnabledMods','ModsList']:
        config[key]=['TerminaAdventureBridge']+[m for m in config[key] if m!='TerminaAdventureBridge']
    # The companion must continue simulating while Zelda has focus.
    config['Graphics']['EnablePauseOnInactive']=False
    assert profile.read_bytes()==original,'SAModManager changed the profile during installation'
    temp=profile.with_suffix('.termina.tmp');temp.write_text(json.dumps(config,indent=2)+'\n');temp.replace(profile)
    mods=ROOT/'runtime/mods';mods.mkdir(exist_ok=True)
    bridge=ROOT/'build/termina_adventure_bridge-0.1.22.nrm'
    with zipfile.ZipFile(bridge) as z:
        assert z.testzip() is None and json.loads(z.read('mod.json'))['version']=='0.1.22'
    shutil.copy2(bridge,mods/bridge.name);shutil.copy2(ROOT/'build/native/termina_bridge.dll',mods/'termina_bridge.dll')
    modlist=ROOT/'runtime/mods.json';shutil.copy2(modlist,backup/'zelda-mods.json')
    conf=json.loads(modlist.read_text())
    for key in ['enabled_mods','mod_order']:
        for identifier in ['termina_adventure','termina_adventure_bridge']:
            if identifier not in conf[key]: conf[key].append(identifier)
    modlist.write_text(json.dumps(conf,indent=2)+'\n')
    (ROOT/'Launch SADX Companion.cmd').write_text('@echo off\ncd /d "'+str(game)+'"\nstart "Termina Adventure SADX" "sonic.exe" --level stationsquare --act 0 --character sonic\n',encoding='utf-8')
    for character in ['sonic','tails','knuckles','amy','big','gamma']:
        (ROOT/f'View SADX {character.title()}.cmd').write_text('@echo off\ncd /d "'+str(game)+'"\nstart "SADX character preview" "sonic.exe" --level stationsquare --act 0 --character '+character+'\n',encoding='utf-8')
    report={'version':'0.1.22','sadx_mod':str(target),'enabled_profile':str(profile),'existing_mods_preserved':True,
        'companion_isolates_input_before_character_select':True,'zelda_bridge_enabled':True,'background_updates_enabled':True,'backup':str(backup.resolve()),
        'dll_sha256':hashlib.sha256(dll.read_bytes()).hexdigest(),'full_world_takeover':False,'in_game_validation':'pending'}
    (ROOT/'docs/companion-install.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
