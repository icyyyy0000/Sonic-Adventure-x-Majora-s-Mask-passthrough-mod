#include "mod_recomp.h"
#include "transport.h"
#include <string.h>
#include <string>
#include <stdio.h>
#include <windows.h>
// Native mod libraries must export API metadata as a data symbol.
// N64ModernRuntime validates this before resolving any bridge functions.
extern "C" {
__declspec(dllexport) uint32_t recomp_api_version = 1;
}
// A restarted Zelda process must not reuse the previous process's scene epoch.
// SADX can remain alive throughout the restart with an old foreign-world task.
extern "C" __declspec(dllexport) void ta_bridge_next_epoch(uint8_t*, recomp_context* ctx) {
    static uint32_t epoch=[]() {
        LARGE_INTEGER counter;QueryPerformanceCounter(&counter);
        return static_cast<uint32_t>(counter.QuadPart) ^ static_cast<uint32_t>(counter.QuadPart>>32) ^
               (GetCurrentProcessId()*2654435761u);
    }();
    if (++epoch==0) ++epoch;
    ctx->r2=epoch;
}
// Recomp native functions receive the emulated CPU context, NOT normal C args.
// RDRAM stores each 32-bit word in host order, while byte/halfword accesses swap.
static int valid(gpr addr, size_t bytes) {
    uint32_t p = static_cast<uint32_t>(addr);
    return p >= 0x80000000u && p <= 0x88000000u - bytes && !(p & 3);
}
extern "C" __declspec(dllexport) void ta_bridge_publish(uint8_t* rdram, recomp_context* ctx) {
    TA_HostFrame frame{};
    ctx->r2 = 0;
    if (!valid(ctx->r4, sizeof(frame)) || ctx->r5 != sizeof(frame) / 4) return;
    memcpy(&frame, rdram + static_cast<uint32_t>(ctx->r4) - 0x80000000u, sizeof(frame));
    ctx->r2 = ta_transport_write_host(&frame);
}
extern "C" __declspec(dllexport) void ta_bridge_poll(uint8_t* rdram, recomp_context* ctx) {
    TA_GuestFrame frame{};
    ctx->r2 = 0;
    if (!valid(ctx->r4, sizeof(frame)) || ctx->r5 != sizeof(frame) / 4) return;
    if (!ta_transport_read_guest(&frame)) return;
    memcpy(rdram + static_cast<uint32_t>(ctx->r4) - 0x80000000u, &frame, sizeof(frame));
    ctx->r2 = 1;
}
extern "C" __declspec(dllexport) void ta_bridge_close(uint8_t*, recomp_context*) {
    ta_transport_close();
}
extern "C" __declspec(dllexport) void ta_bridge_publish_world(uint8_t* rdram, recomp_context* ctx) {
    // This packet contains only complete 32-bit words; preserve host word order.
    static TA_WorldFrame frame;
    ctx->r2 = 0;
    if (!valid(ctx->r4, sizeof(frame)) || ctx->r5 != sizeof(frame) / 4) return;
    memcpy(&frame, rdram + static_cast<uint32_t>(ctx->r4) - 0x80000000u, sizeof(frame));
    ctx->r2 = ta_transport_write_world(&frame);
}

static std::wstring ta_settings_path(){
    HMODULE module=nullptr;wchar_t path[32768]{};
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
        reinterpret_cast<LPCWSTR>(&ta_settings_path),&module);
    DWORD length=GetModuleFileNameW(module,path,32768);
    if(!length || length>=32768)return L"";
    std::wstring result(path,length);auto slash=result.find_last_of(L"\\/");
    if(slash==std::wstring::npos)return L"";
    return result.substr(0,slash+1)+L"termina-adventure-settings.ini";
}
static const wchar_t* ta_setting_keys[]={L"Hud",L"CameraSmoothing",L"CharacterSounds",L"MuteMusic",L"UniversalClimb",L"GrappleRange",L"GrappleSpeed",L"Models",L"GammaHoverPercent",L"BigNewMechanics",L"AmyHammerHeightPercent",L"GravityPercent",L"GammaFireTicks",L"SpeedPercent",L"CameraFollowPercent",L"ControlHints"};
extern "C" __declspec(dllexport) void ta_settings_load(uint8_t* rdram,recomp_context* ctx){
    ctx->r2=0;if(ctx->r5!=16 || !valid(ctx->r4,64))return;
    auto path=ta_settings_path();if(path.empty())return;
    uint32_t values[16];auto memory=rdram+static_cast<uint32_t>(ctx->r4)-0x80000000u;
    memcpy(values,memory,64);
    for(unsigned i=0;i<16;i++)values[i]=GetPrivateProfileIntW(L"Settings",ta_setting_keys[i],values[i],path.c_str());
    memcpy(memory,values,64);ctx->r2=1;
}
extern "C" __declspec(dllexport) void ta_settings_save(uint8_t* rdram,recomp_context* ctx){
    ctx->r2=0;if(ctx->r5!=16 || !valid(ctx->r4,64))return;
    auto path=ta_settings_path();if(path.empty())return;
    uint32_t values[16];memcpy(values,rdram+static_cast<uint32_t>(ctx->r4)-0x80000000u,64);
    bool okay=true;
    for(unsigned i=0;i<16;i++){wchar_t text[16];_snwprintf(text,16,L"%u",values[i]);
        if(!WritePrivateProfileStringW(L"Settings",ta_setting_keys[i],text,path.c_str()))okay=false;}
    ctx->r2=okay;
}
