Weclome to SALUT-2 - fast 16-bit CPU in Scrap Mechanic (there will be a link to steam page)
This documentation isn't written by a native English speaker and in hurry so, please forgive me for unclear explanations and mistakes

# CPU Architecture

CPU consists of three main parts:

1. ALU - Artihmetic Logic Unit
2. MM - Memory manager
3. Instruction decoder

MM is basically the same thing as ALU except it does nothing with the data and just writes it in another place.
In both MM and ALU all outputs from all modules are always on (except for multiplication and divison).
Instruction decoder reads memory from PC register and turns on needed inputs in MM and ALU.

## MM Architecture

MM just outputs every single register or memory slot that could be read and has input for every register that could be written in.

It has these modules:

### 1. RAM - Random access memory

RAM has 16-bit addresses and contains 16-bit memory slots, so the CPU has 128 KiB of RAM in total.

### 2. Registers

There are 16 general purpose registers (16-bit) from R0 to R15.

### 3. Ports

There are 4 in-ports and 4 out-ports from P0 TO P3.

Out-ports can't be read, they can only output values from register or memory. When they output a value they turn 17th signal bit on, no matter what the output is. Output lasts only 1 tick.

In-ports can be read in a register. After one tick input in-ports memorise the value (input should also turn signal bits on so that the CPU would know input happened).

Signal bits are marked white on the build.

By default P0 OUT is connected to 32x32 screen, P0 IN is connected to the joystick.

### 4. Special Registers

1.  PC - Program counter. It's where CPU reads instructions from.

2.  SP - Stack pointer. It shows address of the last value put in stack (0 if it's empty yet).

Stack is stored at the end of the RAM and can be as big as programmer allows.

3.  IM - Input mask. It contains 4 bits that control from which ports input handling can be triggered.

4.  IA - Input address. It tells where input handling function is in the memory.

If the in-port with the signal bit on is marked in IM it triggers input handling. It clears signal bits from every port and executes CALL IA instruction, interrupting others.

### 5. Flags

Flags are stored in a PS (Processor state) register.

1.  N (F0) - Negative flag.

2.  Z (F1) - Zero flag.

3.  C (F2) - Carry flag.

4.  V (F3) - Overflow flag

5.  SL - Signed less flag.

SL flag is special as it can't be set manually and is derived from first 4 flags (SL = N xor V).
SL flag only changes whenever PS is changed manually from instruction or while subtracting (comparing). In every other situation it is ignored.
SL flag is also pushed to stack as a fifth bit of PS and fifth bit from stack can be set as SL as well when popping.

## ALU Architecture

ALU contains these modules:

1. Increment module
2. Decrement module
3. Negative module
4. Absolute module
5. Pseudorandom number generator (16-bit Fibonacci LFSR)
6. Adder (and subtractor)
7. Logical module (AND, OR, XOR, NAND, NOR, XNOR, NOT)
8. Multiplication module
9. Division module

All of the modules are 16 bit. They get input from MM and output on decoder signal.

## Instruction decoder

Instruction decoder reads memory by PC address. When 1-tick signal for the next command comes it launches certain instruction that outputs all of the needed signals in ALU and MM.

There isn't a clock in this CPU - every instruction takes as much ticks as it needs (minimum is 4) and gives a signal for the next command on time. So frequency ranges from 0.38 to 10 Hz.

Green button on the joystick starts first instruction, dark red resets all of the registers and turns CPU off.

# Assembler documentation

To use the assembler, write your program in program.txt and launch assembler.py. It automatically sets memory block data to your machine code if assembled correctly. To import it in the game you must press E on the red memory block (RAM) on the corner of the CPU. After that you may press green button on the joystick and the code will execute.

You can also assemble prorgam in any other file (not necessarily .txt) with:

```
python assembler.py path\to\program.txt
```

## Instruction set

Instructions follow this syntax:

```
(Mnemonic) (Operands separated by commas) ; (Comment after ';')
```

You can also put a comment after an empty line.

### Terms

General purpose registers: R0-R15 (Reg)
Special registers: PC, SP, IM. IA, PS
Ports: P0-P3 (Port)
Flags: N, Z, C, V or F0, F1, F2, F3 (Flag)
Immediate value: Imm

Immediate value means a value that is written directly into the memory.
It can be:

1. Decimal number from -65535 to 65535
2. Binary number that starts with "0b" from 0b0 to 0b1111_1111_1111_1111
3. Hexadecimal number that starts with "0x" form 0x0 to 0xFFFF
4. a letter in single quotes - it's transformed into integer with python ord() function.
5. A defined name of a label or a constant.

### 0x0000 NOP

No operation instruction.

Actions: PC = PC + 1, Next command signal

### 0x0001 STOP

Stops processor.

Actions: PC = PC + 1

### 0x0002 RET

Returns from a function - pops stack into the PC.

Actions: PC = Memory[SP], SP = SP + 1, Next command signal

### 0x0003 CALL Reg|Imm

Calls a function - pushes PC into stack and

### 0x0004-0x0012 Jumps

| Opcode | Mnemonic |            Instruction            | Condition |
| :----: | :------: | :-------------------------------: | :-------: |
| 0x0004 |    JS    |         Jump if negative          |     N     |
| 0x0005 |   JNS    |     Jump if positive or zero      |   not N   |
| 0x0006 |    JE    |      Jump if equal (if zero)      |     Z     |
| 0x0007 |   JNE    |   Jump if not equal (not zero)    |   not Z   |
| 0x0008 | JC (JAE) | Jump if carry (if above or equal) |     C     |
| 0x0009 | JNC (JB) |   Jump if not carry (if below)    |   not C   |
| 0x000A |          |                                   |           |
| 0x000B |          |                                   |           |
| 0x000C |          |                                   |           |
| 0x000D |          |                                   |           |
| 0x000E |          |                                   |           |
| 0x000F |          |                                   |           |
| 0x0010 |          |                                   |           |
| 0x0011 |          |                                   |           |
| 0x0012 |          |                                   |           |
