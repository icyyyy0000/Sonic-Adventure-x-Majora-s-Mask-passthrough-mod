#ifndef TA_TRANSPORT_H
#define TA_TRANSPORT_H
#include "bridge_protocol.h"
#include "world_protocol.h"
#ifdef __cplusplus
extern "C" {
#endif
__declspec(dllexport) int ta_transport_write_host(const TA_HostFrame*);
__declspec(dllexport) int ta_transport_read_host(TA_HostFrame*);
__declspec(dllexport) int ta_transport_write_guest(const TA_GuestFrame*);
__declspec(dllexport) int ta_transport_read_guest(TA_GuestFrame*);
__declspec(dllexport) void ta_transport_close(void);
__declspec(dllexport) int ta_transport_write_world(const TA_WorldFrame*);
__declspec(dllexport) int ta_transport_read_world(TA_WorldFrame*);
#ifdef __cplusplus
}
#endif
#endif
