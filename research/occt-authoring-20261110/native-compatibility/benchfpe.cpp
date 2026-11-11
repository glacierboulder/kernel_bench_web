#include <float.h>
extern "C" __declspec(dllexport) int Benchfpe_Init(void*) { unsigned int old; _controlfp_s(&old, _MCW_EM, _MCW_EM); return 0; }
