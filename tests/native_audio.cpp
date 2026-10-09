#include <windows.h>
#include <string>
#include <stdio.h>
#include "SADXModInfo.h"
static FILE* logFile;
#include "native_audio.h"
int main() {
    static_assert(sizeof(_SEcallbuf)==56,"Original SDK sound queue stride");
    _SEcallbuf s{};s.mode=1|0x10|0x100|0x200|0x800|0x1000|0x2000|0x4000;
    s.tone=0x30d;s.timer=10;s.id=45;s.pitch=120;s.vol=-12;s.angle=60;
    ta_audio_audible(s);
    if(s.mode!=(1|0x10|0x200|0x800|0x2000) || s.tone!=0x30d || s.timer!=10 || s.pitch!=120 || s.vol!=-12 || s.id!=45 || s.angle!=0) return 1;
    s.mode=0x811;s.timer=3;ta_audio_audible(s);if(s.timer!=8 || !(s.mode&0x800))return 2;
    puts("PASS: native audio preserves original tone, timing, volume, pitch and looping; staging distance/pan filtering removed.");
}
