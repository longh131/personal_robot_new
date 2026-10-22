ENTRY(Reset_Handler)
MEMORY
{
  FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 512K
  RAM (xrw)  : ORIGIN = 0x20000000, LENGTH = 128K
}
_estack = ORIGIN(RAM) + LENGTH(RAM);
_Min_Heap_Size = 0x400;
_Min_Stack_Size = 0x800;
SECTIONS
{
  .isr_vector : { KEEP(*(.isr_vector)) } >FLASH
  .text : { *(.text*) *(.rodata*) KEEP(*(.init)) KEEP(*(.fini)) } >FLASH
  .ARM.extab : { *(.ARM.extab* .gnu.linkonce.armextab.*) } >FLASH
  .ARM : { *(.ARM.exidx*) } >FLASH
  _sidata = LOADADDR(.data);
  .data : {
    _sdata = .;
    *(.data*)
    *(.RamFunc*)
    _edata = .;
  } >RAM AT> FLASH
  .bss : {
    _sbss = .;
    *(.bss*)
    *(COMMON)
    _ebss = .;
  } >RAM
  ._user_heap_stack : {
    . = ALIGN(8);
    . = . + _Min_Heap_Size;
    . = . + _Min_Stack_Size;
    . = ALIGN(8);
  } >RAM
}
