#include <stdint.h>
#include <stdio.h>
#include "ultra64.h"
#include "rt64_extended_gbi.h"
static uint32_t resolve(uint32_t address) {
    // RT64 RSP::fromSegmentedMasked with extended RDRAM enabled.
    if (address & 0x80000000u) return address - 0x80000000u;
    uint32_t segments[16] = {0, 0x123000, 0x456000};
    return (segments[(address >> 24) & 15] + (address & 0xffffff)) & 0xfffff8;
}
int main(void) {
    uint32_t addresses[] = {0x80812340u, 0x81812340u, 0x82812340u, 0x87812340u};
    for (unsigned i=0; i<4; i++) {
        Gfx commands[2] = {0}; Gfx* next = commands;
        gSPDisplayList(next++, (void*)addresses[i]);
        if (next != commands+1 || commands[0].words.w1 != addresses[i] ||
            resolve(commands[0].words.w1) != addresses[i]-0x80000000u) return 1;
        if (i==1) {
            next = commands;
            gEXDisplayList(next++, (void*)addresses[i]);
            uint32_t hookAddress = commands[0].words.w1 & 0x0fffffffu;
            if (resolve(hookAddress) == addresses[i]-0x80000000u) return 2;
        }
    }
    puts("PASS: real display-list macros retain extended RDRAM addresses; old command reproduces bad translation.");
    return 0;
}
