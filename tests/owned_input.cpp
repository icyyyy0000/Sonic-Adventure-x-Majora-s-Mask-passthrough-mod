#include <stdio.h>
#include <windows.h>
#include <string>
#include "SADXModInfo.h"
#include "owned_input.h"
int main() {
    ControllerData pad{};
    pad.HeldButtons=pad.PressedButtons=pad.ReleasedButtons=Buttons_Start|Buttons_A|Buttons_B;
    pad.NotHeldButtons=0;pad.LeftStickX=42;pad.LeftStickY=-90;
    int held=pad.HeldButtons,pressed=pad.PressedButtons;
    ta_filter_owned_start(pad,held,pressed);
    if ((pad.HeldButtons|pad.PressedButtons|pad.ReleasedButtons|held|pressed)&Buttons_Start) return 1;
    if (!(pad.NotHeldButtons&Buttons_Start)) return 2;
    if (pad.HeldButtons!=(Buttons_A|Buttons_B) || held!=(Buttons_A|Buttons_B) || pressed!=(Buttons_A|Buttons_B)) return 3;
    if (pad.LeftStickX!=42 || pad.LeftStickY!=-90) return 4;
    pad.HeldButtons=pad.PressedButtons=Buttons_D|Buttons_Z|Buttons_C|Buttons_R|Buttons_L|Buttons_Left;
    ta_clear_owned_pad(pad);
    if (pad.HeldButtons || pad.PressedButtons || pad.ReleasedButtons || pad.LeftStickX || pad.LeftStickY ||
        pad.LTriggerPressure || pad.RTriggerPressure || pad.NotHeldButtons!=~0u) return 5;
    puts("PASS: Start isolation and raw character-selection/teleport/redirection controls cleared before Character Select.");
}
