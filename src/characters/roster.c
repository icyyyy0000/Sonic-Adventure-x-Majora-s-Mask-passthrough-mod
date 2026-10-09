#include "characters/roster.h"
const TA_CharacterDef ta_roster[TA_CHARACTER_COUNT] = {
    { "Link", "Zelda controls", -1, 6.0f, 6.0f, 1.0f, NULL },
    { "Sonic", "B charge/release; air A/B homing", 0, 11.0f, 10.5f, 2.8f, ta_sonic_update },
    { "Tails", "Press A again, hold to fly", 2, 8.0f, 9.5f, 2.8f, ta_tails_update },
    { "Knuckles", "A glide/latch; stick climb; B punch", 3, 8.0f, 10.0f, 2.8f, ta_knuckles_update },
    { "Amy", "B hammer; A hammer jump", 5, 7.0f, 13.0f, 2.8f, ta_amy_update },
    { "Big", "Tap B grapple; air hold B stomp", 7, 4.5f, 8.0f, 2.5f, ta_big_update },
    { "E-102 Gamma", "B lock-on shot; hold A hover", 6, 7.0f, 9.0f, 2.5f, ta_gamma_update },
};
