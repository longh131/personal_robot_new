.syntax unified
.cpu cortex-m4
.fpu fpv4-sp-d16
.thumb
.global g_pfnVectors
.global Default_Handler
.word _sidata
.word _sdata
.word _edata
.word _sbss
.word _ebss
.section .text.Reset_Handler
.weak Reset_Handler
.type Reset_Handler, %function
Reset_Handler:
  ldr r0, =_estack
  mov sp, r0
  ldr r0, =_sdata
  ldr r1, =_edata
  ldr r2, =_sidata
  b LoopCopyDataInit
CopyDataInit:
  ldr r3, [r2], #4
  str r3, [r0], #4
LoopCopyDataInit:
  cmp r0, r1
  bcc CopyDataInit
  ldr r2, =_sbss
  ldr r4, =_ebss
  movs r3, #0
  b LoopFillZerobss
FillZerobss:
  str r3, [r2], #4
LoopFillZerobss:
  cmp r2, r4
  bcc FillZerobss
  bl SystemInit
  bl main
  b .
.size Reset_Handler, .-Reset_Handler
.section .text.Default_Handler,"ax",%progbits
Default_Handler:
  b Default_Handler
.section .isr_vector,"a",%progbits
.type g_pfnVectors, %object
g_pfnVectors:
  .word _estack
  .word Reset_Handler
  .word NMI_Handler
  .word HardFault_Handler
  .word MemManage_Handler
  .word BusFault_Handler
  .word UsageFault_Handler
  .word 0
  .word 0
  .word 0
  .word 0
  .word SVC_Handler
  .word DebugMon_Handler
  .word 0
  .word PendSV_Handler
  .word SysTick_Handler
  .word WWDG_IRQHandler
  .word PVD_IRQHandler
  .word TAMP_STAMP_IRQHandler
  .word RTC_WKUP_IRQHandler
  .word FLASH_IRQHandler
  .word RCC_IRQHandler
  .word EXTI0_IRQHandler
  .word EXTI1_IRQHandler
  .word EXTI2_IRQHandler
  .word EXTI3_IRQHandler
  .word EXTI4_IRQHandler
  .word DMA1_Stream0_IRQHandler
  .word DMA1_Stream1_IRQHandler
  .word DMA1_Stream2_IRQHandler
  .word DMA1_Stream3_IRQHandler
  .word DMA1_Stream4_IRQHandler
  .word DMA1_Stream5_IRQHandler
  .word DMA1_Stream6_IRQHandler
  .word ADC_IRQHandler
  .word CAN1_TX_IRQHandler
  .word CAN1_RX0_IRQHandler
  .word CAN1_RX1_IRQHandler
  .word CAN1_SCE_IRQHandler
  .word EXTI9_5_IRQHandler
  .word TIM1_BRK_TIM9_IRQHandler
  .word TIM1_UP_TIM10_IRQHandler
  .word TIM1_TRG_COM_TIM11_IRQHandler
  .word TIM1_CC_IRQHandler
  .word TIM2_IRQHandler
  .word TIM3_IRQHandler
  .word TIM4_IRQHandler
  .word I2C1_EV_IRQHandler
  .word I2C1_ER_IRQHandler
  .word I2C2_EV_IRQHandler
  .word I2C2_ER_IRQHandler
  .word SPI1_IRQHandler
  .word SPI2_IRQHandler
  .word USART1_IRQHandler
  .word USART2_IRQHandler
  .word USART3_IRQHandler
  .word EXTI15_10_IRQHandler
  .word RTC_Alarm_IRQHandler
  .word OTG_FS_WKUP_IRQHandler
  .word TIM8_BRK_TIM12_IRQHandler
  .word TIM8_UP_TIM13_IRQHandler
  .word TIM8_TRG_COM_TIM14_IRQHandler
  .word TIM8_CC_IRQHandler
  .word DMA1_Stream7_IRQHandler
  .word FSMC_IRQHandler
  .word SDIO_IRQHandler
  .word TIM5_IRQHandler
  .word SPI3_IRQHandler
  .word UART4_IRQHandler
  .word UART5_IRQHandler
  .word TIM6_DAC_IRQHandler
  .word TIM7_IRQHandler
  .word DMA2_Stream0_IRQHandler
  .word DMA2_Stream1_IRQHandler
  .word DMA2_Stream2_IRQHandler
  .word DMA2_Stream3_IRQHandler
  .word DMA2_Stream4_IRQHandler
  .word ETH_IRQHandler
  .word ETH_WKUP_IRQHandler
  .word CAN2_TX_IRQHandler
  .word CAN2_RX0_IRQHandler
  .word CAN2_RX1_IRQHandler
  .word CAN2_SCE_IRQHandler
  .word OTG_FS_IRQHandler
  .word DMA2_Stream5_IRQHandler
  .word DMA2_Stream6_IRQHandler
  .word DMA2_Stream7_IRQHandler
  .word USART6_IRQHandler
  .word I2C3_EV_IRQHandler
  .word I2C3_ER_IRQHandler
  .word OTG_HS_EP1_OUT_IRQHandler
  .word OTG_HS_EP1_IN_IRQHandler
  .word OTG_HS_WKUP_IRQHandler
  .word OTG_HS_IRQHandler
  .word DCMI_IRQHandler
  .word CRYP_IRQHandler
  .word HASH_RNG_IRQHandler
  .word FPU_IRQHandler
.macro	def_irq name
  .weak \name
  .thumb_set \name, Default_Handler
.endm
  def_irq NMI_Handler
  def_irq HardFault_Handler
  def_irq MemManage_Handler
  def_irq BusFault_Handler
  def_irq UsageFault_Handler
  def_irq SVC_Handler
  def_irq DebugMon_Handler
  def_irq PendSV_Handler
  def_irq SysTick_Handler
  def_irq WWDG_IRQHandler
  def_irq PVD_IRQHandler
  def_irq TAMP_STAMP_IRQHandler
  def_irq RTC_WKUP_IRQHandler
  def_irq FLASH_IRQHandler
  def_irq RCC_IRQHandler
  def_irq EXTI0_IRQHandler
  def_irq EXTI1_IRQHandler
  def_irq EXTI2_IRQHandler
  def_irq EXTI3_IRQHandler
  def_irq EXTI4_IRQHandler
  def_irq DMA1_Stream0_IRQHandler
  def_irq DMA1_Stream1_IRQHandler
  def_irq DMA1_Stream2_IRQHandler
  def_irq DMA1_Stream3_IRQHandler
  def_irq DMA1_Stream4_IRQHandler
  def_irq DMA1_Stream5_IRQHandler
  def_irq DMA1_Stream6_IRQHandler
  def_irq ADC_IRQHandler
  def_irq CAN1_TX_IRQHandler
  def_irq CAN1_RX0_IRQHandler
  def_irq CAN1_RX1_IRQHandler
  def_irq CAN1_SCE_IRQHandler
  def_irq EXTI9_5_IRQHandler
  def_irq TIM1_BRK_TIM9_IRQHandler
  def_irq TIM1_UP_TIM10_IRQHandler
  def_irq TIM1_TRG_COM_TIM11_IRQHandler
  def_irq TIM1_CC_IRQHandler
  def_irq TIM2_IRQHandler
  def_irq TIM3_IRQHandler
  def_irq TIM4_IRQHandler
  def_irq I2C1_EV_IRQHandler
  def_irq I2C1_ER_IRQHandler
  def_irq I2C2_EV_IRQHandler
  def_irq I2C2_ER_IRQHandler
  def_irq SPI1_IRQHandler
  def_irq SPI2_IRQHandler
  def_irq USART1_IRQHandler
  def_irq USART2_IRQHandler
  def_irq USART3_IRQHandler
  def_irq EXTI15_10_IRQHandler
  def_irq RTC_Alarm_IRQHandler
  def_irq OTG_FS_WKUP_IRQHandler
  def_irq TIM8_BRK_TIM12_IRQHandler
  def_irq TIM8_UP_TIM13_IRQHandler
  def_irq TIM8_TRG_COM_TIM14_IRQHandler
  def_irq TIM8_CC_IRQHandler
  def_irq DMA1_Stream7_IRQHandler
  def_irq FSMC_IRQHandler
  def_irq SDIO_IRQHandler
  def_irq TIM5_IRQHandler
  def_irq SPI3_IRQHandler
  def_irq UART4_IRQHandler
  def_irq UART5_IRQHandler
  def_irq TIM6_DAC_IRQHandler
  def_irq TIM7_IRQHandler
  def_irq DMA2_Stream0_IRQHandler
  def_irq DMA2_Stream1_IRQHandler
  def_irq DMA2_Stream2_IRQHandler
  def_irq DMA2_Stream3_IRQHandler
  def_irq DMA2_Stream4_IRQHandler
  def_irq ETH_IRQHandler
  def_irq ETH_WKUP_IRQHandler
  def_irq CAN2_TX_IRQHandler
  def_irq CAN2_RX0_IRQHandler
  def_irq CAN2_RX1_IRQHandler
  def_irq CAN2_SCE_IRQHandler
  def_irq OTG_FS_IRQHandler
  def_irq DMA2_Stream5_IRQHandler
  def_irq DMA2_Stream6_IRQHandler
  def_irq DMA2_Stream7_IRQHandler
  def_irq USART6_IRQHandler
  def_irq I2C3_EV_IRQHandler
  def_irq I2C3_ER_IRQHandler
  def_irq OTG_HS_EP1_OUT_IRQHandler
  def_irq OTG_HS_EP1_IN_IRQHandler
  def_irq OTG_HS_WKUP_IRQHandler
  def_irq OTG_HS_IRQHandler
  def_irq DCMI_IRQHandler
  def_irq CRYP_IRQHandler
  def_irq HASH_RNG_IRQHandler
  def_irq FPU_IRQHandler
