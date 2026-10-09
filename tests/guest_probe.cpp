#include "transport.h"
#include <windows.h>
#include <math.h>
int main(int argc, char**) {
    if (argc > 1) {
        HANDLE lock = OpenMutexW(SYNCHRONIZE, FALSE, TA_MUTEX_NAME);
        if (!lock || WaitForSingleObject(lock, 1000) != WAIT_OBJECT_0) return 4;
        // Exit while owning the mutex, simulating a mid-publication crash.
        return 0;
    }
    TA_HostFrame host{};
    for (int attempt = 0; attempt < 100; attempt++) {
        if (ta_transport_read_host(&host)) break;
        Sleep(10);
    }
    if (host.frame != 123 || host.character != 3 || fabsf(host.position[1] - 12.5f) > 0.001f) return 2;
    TA_GuestFrame guest{};
    guest.frame = 456;
    guest.character = host.character;
    guest.flags = TA_GUEST_HAS_PLAYER | TA_GUEST_MATCHING_CHARACTER;
    guest.position[0] = host.position[0] + 2.0f;
    guest.position[1] = host.position[1];
    guest.position[2] = -9.0f;
    guest.animation = 17;
    guest.modelOffsetY=2.85f;guest.previousActionIndex=82;
    guest.previousAnimationFrame=7.5f;guest.animationBlend=.25f;
    if (!ta_transport_write_guest(&guest)) return 3;
    Sleep(250);
    // Deliberately omit close: exercise crash/heartbeat expiry in the parent.
    return 0;
}
