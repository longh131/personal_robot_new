PREFIX := /opt/personal_robot/tools/arm-none-eabi-root/usr
CC := $(PREFIX)/bin/arm-none-eabi-gcc
OBJCOPY := $(PREFIX)/bin/arm-none-eabi-objcopy
SIZE := $(PREFIX)/bin/arm-none-eabi-size
ROOT := $(abspath ..)
BUILD := $(ROOT)/gcc/build
TARGET := $(ROOT)/OBJ/WHEELTEC

CPU := -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
DEFS := -DSTM32F40_41xxx -DUSE_STDPERIPH_DRIVER -D__FPU_PRESENT=1 \
	-DARM_MATH_CM4 -DUSE_USB_OTG_FS -DPERSONAL_ROBOT_SERVO=1
INCS := -isystem /opt/personal_robot/tools/arm-none-eabi-root/usr/include/newlib -I$(ROOT)/CORE -I$(ROOT)/SYSTEM/delay -I$(ROOT)/SYSTEM/sys -I$(ROOT)/SYSTEM/usart \
	-I$(ROOT)/USER -I$(ROOT)/HARDWARE/LED -I$(ROOT)/FWLIB/inc -I$(ROOT)/FreeRTOS/include \
	-I$(ROOT)/gcc -I$(ROOT)/BALANCE -I$(ROOT)/HARDWARE -I$(ROOT)/HARDWARE/MPU6050 \
	-I$(ROOT)/AutoRecharge -I$(ROOT)/HARDWARE/ICM20948 \
	-I$(ROOT)/HARDWARE/USB/STM32_USB_Host_Library/Class/HID/Inc \
	-I$(ROOT)/HARDWARE/USB/STM32_USB_Host_Library/Core/Inc \
	-I$(ROOT)/HARDWARE/USB/USB_HOST/App -I$(ROOT)/HARDWARE/USB/USB_HOST/Target
CFLAGS := $(CPU) $(DEFS) $(INCS) -O2 -g -ffunction-sections -fdata-sections -fno-common \
	-Wall -Wno-unused -Wno-strict-aliasing -std=gnu99 -include $(ROOT)/gcc/armcc_compat.h
ASFLAGS := $(CPU)
LDSCRIPT := $(ROOT)/gcc/STM32F407VETx_FLASH.ld
LDFLAGS := $(CPU) -T$(LDSCRIPT) -Wl,--gc-sections -nostartfiles \
	-Wl,-Map=$(TARGET).map \
	-L/opt/personal_robot/tools/arm-none-eabi-root/usr/lib/arm-none-eabi/newlib/thumb/v7e-m+fp/hard \
	-L/opt/personal_robot/tools/arm-none-eabi-root/usr/lib/gcc/arm-none-eabi/13.2.1/thumb/v7e-m+fp/hard

C_SRCS := \
	$(ROOT)/USER/main.c $(ROOT)/USER/stm32f4xx_it.c $(ROOT)/USER/system_stm32f4xx.c \
	$(ROOT)/HARDWARE/adc.c $(ROOT)/HARDWARE/can.c $(ROOT)/HARDWARE/encoder.c \
	$(ROOT)/HARDWARE/key.c $(ROOT)/HARDWARE/LED.C $(ROOT)/HARDWARE/motor.c \
	$(ROOT)/HARDWARE/oled.c $(ROOT)/HARDWARE/pstwo.c $(ROOT)/HARDWARE/timer.c \
	$(ROOT)/HARDWARE/usartx.c $(ROOT)/AutoRecharge/AutoRecharge.c \
	$(ROOT)/HARDWARE/ICM20948/ICM20948.c $(ROOT)/HARDWARE/MPU6050/MPU6050.c \
	$(ROOT)/HARDWARE/I2C.c $(ROOT)/HARDWARE/bsp_gamepad.c $(ROOT)/HARDWARE/stmflash.c \
	$(ROOT)/SYSTEM/delay/delay.c $(ROOT)/SYSTEM/sys/sys.c $(ROOT)/SYSTEM/usart/usart.c \
	$(ROOT)/FWLIB/src/misc.c $(ROOT)/FWLIB/src/stm32f4xx_gpio.c $(ROOT)/FWLIB/src/stm32f4xx_rcc.c \
	$(ROOT)/FWLIB/src/stm32f4xx_syscfg.c $(ROOT)/FWLIB/src/stm32f4xx_usart.c \
	$(ROOT)/FWLIB/src/stm32f4xx_adc.c $(ROOT)/FWLIB/src/stm32f4xx_can.c \
	$(ROOT)/FWLIB/src/stm32f4xx_tim.c $(ROOT)/FWLIB/src/stm32f4xx_pwr.c \
	$(ROOT)/FWLIB/src/stm32f4xx_hal_hcd.c $(ROOT)/FWLIB/src/stm32f4xx_ll_usb.c \
	$(ROOT)/FreeRTOS/croutine.c $(ROOT)/FreeRTOS/event_groups.c $(ROOT)/FreeRTOS/list.c \
	$(ROOT)/FreeRTOS/queue.c $(ROOT)/FreeRTOS/tasks.c $(ROOT)/FreeRTOS/timers.c \
	$(ROOT)/gcc/port.c $(ROOT)/gcc/syscalls.c $(ROOT)/FreeRTOS/portable/MemMang/heap_4.c \
	$(ROOT)/BALANCE/system.c $(ROOT)/BALANCE/balance.c \
	$(ROOT)/BALANCE/robot_select_init.c $(ROOT)/BALANCE/show.c $(ROOT)/BALANCE/imu_task.c \
	$(ROOT)/HARDWARE/check.c \
	$(ROOT)/HARDWARE/USB/STM32_USB_Host_Library/Core/Src/usbh_core.c \
	$(ROOT)/HARDWARE/USB/STM32_USB_Host_Library/Core/Src/usbh_ctlreq.c \
	$(ROOT)/HARDWARE/USB/STM32_USB_Host_Library/Core/Src/usbh_ioreq.c \
	$(ROOT)/HARDWARE/USB/STM32_USB_Host_Library/Core/Src/usbh_pipes.c \
	$(ROOT)/HARDWARE/USB/STM32_USB_Host_Library/Class/HID/Src/usbh_hid.c \
	$(ROOT)/HARDWARE/USB/STM32_USB_Host_Library/Class/HID/Src/usbh_hid_keybd.c \
	$(ROOT)/HARDWARE/USB/STM32_USB_Host_Library/Class/HID/Src/usbh_hid_mouse.c \
	$(ROOT)/HARDWARE/USB/STM32_USB_Host_Library/Class/HID/Src/usbh_hid_parser.c \
	$(ROOT)/HARDWARE/USB/USB_HOST/Target/usbh_conf.c \
	$(ROOT)/HARDWARE/USB/USB_HOST/App/usb_host.c \
	$(ROOT)/HARDWARE/USB/USB_HOST/App/usbh_os_middleware.c \
	$(ROOT)/HARDWARE/USB/USB_HOST/App/usbh_hid_GamePad.c \
	$(ROOT)/HARDWARE/USB/USB_HOST/App/xbox360_gamepad.c \
	$(ROOT)/HARDWARE/USB/USB_HOST/App/WiredPS2_gamepad.c

OBJS := $(patsubst $(ROOT)/%.c,$(BUILD)/%.o,$(C_SRCS))
OBJS := $(patsubst $(ROOT)/%.C,$(BUILD)/%.o,$(OBJS))
AS_OBJ := $(BUILD)/startup_stm32f407xx.o

.PHONY: all clean
all: $(TARGET).hex
	$(SIZE) $(TARGET).elf

$(TARGET).hex: $(TARGET).elf
	mkdir -p $(dir $@)
	$(OBJCOPY) -O ihex $< $@

$(TARGET).elf: $(AS_OBJ) $(OBJS)
	mkdir -p $(dir $@)
	$(CC) $(LDFLAGS) $^ -Wl,--start-group -lc -lm -lgcc -Wl,--end-group -o $@

$(AS_OBJ): $(ROOT)/gcc/startup_stm32f407xx.S
	mkdir -p $(dir $@)
	$(CC) $(ASFLAGS) -c $< -o $@

$(BUILD)/%.o: $(ROOT)/%.c
	mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/%.o: $(ROOT)/%.C
	mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -x c -c $< -o $@

clean:
	rm -rf $(BUILD) $(TARGET).elf $(TARGET).hex $(TARGET).map
