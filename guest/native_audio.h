#ifndef TA_NATIVE_AUDIO_H
#define TA_NATIVE_AUDIO_H
// Original character tasks choose the tone and loaded SADX bank. Only their
// queue mutations are made non-positional: Zelda coordinates are unrelated to
// the staging camera. Other mods' untouched queue entries retain their settings.
static bool nativeCharacterSounds=true;
static bool nativeAudioAllowed=true;
static unsigned audioEvents[7];
static int ownedAudioTone[36],ownedAudioId[36];
static bool ownedAudio[36];
static void ta_audio_audible(_SEcallbuf& sound) {
    sound.mode &= ~(0x100|0x1000|0x4000); // distance/QSound/Dolby; 0x800 is PITCH
    sound.angle=0;
    // Native tasks advance three simulation steps per Zelda tick, but the
    // sound manager still runs every SADX frame. Short refresh loops must live
    // across that interval instead of expiring/restarting twenty times a second.
    if ((sound.mode&0x10) && sound.timer>0 && sound.timer<8) sound.timer=8;
}
struct TA_SilentAudioScope {
    _SEcallbuf before[36];
    TA_SilentAudioScope(){memcpy(before,reinterpret_cast<void*>(0x3B292F8),sizeof(before));}
    ~TA_SilentAudioScope(){memcpy(reinterpret_cast<void*>(0x3B292F8),before,sizeof(before));}
};
static void ta_stop_owned_audio() {
    auto queue=reinterpret_cast<_SEcallbuf*>(0x3B292F8);
    for(unsigned i=0;i<36;i++) if(ownedAudio[i]) {
        if(queue[i].mode && queue[i].tone==ownedAudioTone[i] && queue[i].id==ownedAudioId[i])
            reinterpret_cast<void(__cdecl*)(int)>(0x424240)(queue[i].id);
        ownedAudio[i]=false;
    }
}
struct TA_NativeAudioScope {
    _SEcallbuf before[36];
    unsigned character;
    TA_NativeAudioScope(unsigned c):character(c) {
        memcpy(before,reinterpret_cast<void*>(0x3B292F8),sizeof(before));
    }
    bool queued(int tone) const {
        auto queue=reinterpret_cast<_SEcallbuf*>(0x3B292F8);
        for (unsigned i=0;i<36;i++) if (queue[i].tone==tone && queue[i].mode &&
            (queue[i].mode!=before[i].mode || queue[i].timer!=before[i].timer ||
             queue[i].id!=before[i].id || queue[i].tone!=before[i].tone)) return true;
        return false;
    }
    void landing(EntityData1* p) const {
        if (!nativeCharacterSounds || !nativeAudioAllowed) return;
        int tone=character==6 ? 0x33e : character==5 ? 0x349 : 0x13;
        if (!queued(tone)) reinterpret_cast<int(__cdecl*)(int,int,int,int)>(0x423D70)(tone,
            static_cast<int>(reinterpret_cast<uintptr_t>(p)),1,0);
    }
    ~TA_NativeAudioScope() {
        if (!nativeCharacterSounds || !nativeAudioAllowed) {memcpy(reinterpret_cast<void*>(0x3B292F8),before,sizeof(before));return;}
        auto queue=reinterpret_cast<_SEcallbuf*>(0x3B292F8);
        for (unsigned i=0;i<36;i++) {
            auto& s=queue[i];auto& b=before[i];
            if (!s.mode || s.tone<0 || (s.mode==b.mode && s.tone==b.tone && s.id==b.id && s.timer==b.timer)) continue;
            if(character==1 && s.tone==0x2ff && (s.mode&1) && (!(b.mode&1) || s.tone!=b.tone || s.id!=b.id) && logFile){fprintf(logFile,"Spindash charge stream started\n");fflush(logFile);}
            int spatial=s.mode&(0x100|0x800|0x1000|0x4000);
            ta_audio_audible(s);
            ownedAudio[i]=true;ownedAudioTone[i]=s.tone;ownedAudioId[i]=s.id;
            if (character<7 && audioEvents[character]++<24 && logFile) {
                fprintf(logFile,"Native audio: char=%u tone=%d spatial=%x -> audible original bank\n",character,s.tone,spatial);
                fflush(logFile);
            }
        }
    }
};
#endif
