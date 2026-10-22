#ifndef ARMCC_COMPAT_H
#define ARMCC_COMPAT_H
#ifndef __CC_ARM
#ifndef __weak
#define __weak __attribute__((weak))
#endif
#ifndef __packed
#define __packed __attribute__((packed))
#endif
#ifndef __inline
#define __inline inline
#endif
#ifndef __forceinline
#define __forceinline inline __attribute__((always_inline))
#endif
#ifndef __nop
#define __nop() __asm volatile("nop")
#endif
#endif
#endif
