#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>
#include "transport.h"
#include <cmath>
static HANDLE mapping, mutex;
static HANDLE worldMapping;
struct WorldShared { uint32_t magic, bytes, owner, time; TA_WorldFrame frame; };
static WorldShared* world;
static TA_Shared* shared;
static int acquire() {
    if (!shared) {
        mutex = CreateMutexW(nullptr, FALSE, TA_MUTEX_NAME);
        if (!mutex) return 0;
        mapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0, sizeof(TA_Shared), TA_MAPPING_NAME);
        if (!mapping) { CloseHandle(mutex); mutex = nullptr; return 0; }
        shared = static_cast<TA_Shared*>(MapViewOfFile(mapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(TA_Shared)));
        if (!shared) { CloseHandle(mapping); CloseHandle(mutex); mapping = mutex = nullptr; return 0; }
    }
    DWORD result = WaitForSingleObject(mutex, 0); // Never block either game's frame.
    if (result != WAIT_OBJECT_0 && result != WAIT_ABANDONED) return 0;
    if (result == WAIT_ABANDONED) {
        // A process can die in the middle of copying a frame. Invalidate both
        // snapshots before readers can mistake a partial copy for a live one.
        shared->hostPid = shared->guestPid = shared->hostTime = shared->guestTime = 0;
    }
    if (!shared->magic) {
        memset(shared, 0, sizeof(*shared));
        shared->version = TA_VERSION;
        shared->bytes = sizeof(*shared);
        shared->magic = TA_MAGIC;
    }
    if (shared->magic != TA_MAGIC || shared->version != TA_VERSION || shared->bytes != sizeof(*shared)) {
        ReleaseMutex(mutex);
        return 0;
    }
    return 1;
}
static int live(uint32_t pid, uint32_t time) {
    return pid && static_cast<uint32_t>(GetTickCount64() - time) < TA_TIMEOUT_MS;
}
static int open_world() {
    if (world) return 1;
    worldMapping = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0, sizeof(WorldShared), TA_WORLD_MAPPING);
    if (!worldMapping) return 0;
    world = static_cast<WorldShared*>(MapViewOfFile(worldMapping, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(WorldShared)));
    if (!world) { CloseHandle(worldMapping); worldMapping = nullptr; return 0; }
    return 1;
}
extern "C" __declspec(dllexport) int ta_transport_write_world(const TA_WorldFrame* frame) {
    if (!frame || frame->count > TA_WORLD_CAPACITY || !std::isfinite(frame->radius) || frame->radius <= 0) return 0;
    for (float v : frame->center) if (!std::isfinite(v)) return 0;
    for (uint32_t i = 0; i < frame->count; i++)
        for (float v : frame->triangles[i].vertices) if (!std::isfinite(v) || std::fabs(v) > 1000000) return 0;
    if (!acquire()) return 0;
    int ready = open_world() && shared->hostPid == GetCurrentProcessId() && live(shared->hostPid, shared->hostTime);
    if (ready) {
        world->magic = 0; // Incomplete writes must never appear ready after an abandoned lock.
        world->frame = *frame;
        world->owner = GetCurrentProcessId();
        world->time = static_cast<uint32_t>(GetTickCount64());
        world->bytes = sizeof(WorldShared);
        world->magic = TA_MAGIC;
    }
    ReleaseMutex(mutex);
    return ready;
}
extern "C" __declspec(dllexport) int ta_transport_read_world(TA_WorldFrame* frame) {
    if (!frame || !acquire()) return 0;
    int ready = open_world() && world->magic == TA_MAGIC && world->bytes == sizeof(WorldShared) &&
        world->owner == shared->hostPid && live(shared->hostPid, shared->hostTime) && live(world->owner, world->time) &&
        world->frame.count <= TA_WORLD_CAPACITY && world->frame.epoch == shared->host.epoch && world->frame.scene == shared->host.scene;
    if (ready) *frame = world->frame;
    ReleaseMutex(mutex);
    return ready;
}
extern "C" __declspec(dllexport) int ta_transport_write_host(const TA_HostFrame* frame) {
    if (!frame || !acquire()) return 0;
    // One host per named mapping; refuse to overwrite a second live instance.
    if (shared->hostPid != GetCurrentProcessId() && live(shared->hostPid, shared->hostTime)) {
        ReleaseMutex(mutex); return 0;
    }
    shared->host = *frame;
    shared->hostPid = GetCurrentProcessId();
    shared->hostTime = static_cast<uint32_t>(GetTickCount64());
    ReleaseMutex(mutex);
    return 1;
}
extern "C" __declspec(dllexport) int ta_transport_read_host(TA_HostFrame* frame) {
    if (!frame || !acquire()) return 0;
    int ready = live(shared->hostPid, shared->hostTime);
    if (ready) *frame = shared->host;
    ReleaseMutex(mutex);
    return ready;
}
extern "C" __declspec(dllexport) int ta_transport_write_guest(const TA_GuestFrame* frame) {
    if (!frame || !acquire()) return 0;
    if (shared->guestPid != GetCurrentProcessId() && live(shared->guestPid, shared->guestTime)) {
        ReleaseMutex(mutex); return 0;
    }
    shared->guest = *frame;
    shared->guestPid = GetCurrentProcessId();
    shared->guestTime = static_cast<uint32_t>(GetTickCount64());
    ReleaseMutex(mutex);
    return 1;
}
extern "C" __declspec(dllexport) int ta_transport_read_guest(TA_GuestFrame* frame) {
    if (!frame || !acquire()) return 0;
    int ready = live(shared->guestPid, shared->guestTime);
    if (ready) *frame = shared->guest;
    ReleaseMutex(mutex);
    return ready;
}
extern "C" __declspec(dllexport) void ta_transport_close(void) {
    if (shared && acquire()) {
        if (shared->hostPid == GetCurrentProcessId()) shared->hostPid = shared->hostTime = 0;
        if (shared->guestPid == GetCurrentProcessId()) shared->guestPid = shared->guestTime = 0;
        ReleaseMutex(mutex);
    }
    if (shared) UnmapViewOfFile(shared);
    if (mapping) CloseHandle(mapping);
    if (mutex) CloseHandle(mutex);
    if (world) UnmapViewOfFile(world);
    if (worldMapping) CloseHandle(worldMapping);
    world = nullptr; worldMapping = nullptr;
    shared = nullptr; mapping = mutex = nullptr;
}
