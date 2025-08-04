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

Stack is stored at the end of the RAM and can be as big as programmer allows. Stack pointer can only be incremented or decremented, it can't take values from any other source.

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
8. Shift and roll module
9. Unsigned multiplication module
10. Unsigned division module

All of the modules are 16 bit. They get input from MM and output on decoder signal.

## Instruction decoder

Instruction decoder reads memory at the PC address. When 1-tick signal for the next command comes it launches certain instruction that outputs all of the needed signals in ALU and MM.

There isn't a clock in this CPU - every instruction takes as much ticks as it needs (minimum is 4) and gives a signal for the next instruction on time. So frequency ranges from 0.38 to 10 Hz.

Green button on the joystick starts first instruction, dark red resets all of the registers and turns CPU off.

# Assembler documentation

To use the assembler, write your program in program.txt and launch assembler.py. It automatically sets memory block data to your machine code if assembled correctly. To import it in the game you must press E on the red memory block (RAM) on the corner of the CPU. After that you may press green button on the joystick and the code will execute.

You can also assemble prorgam in any other file (not necessarily .txt) with:

```
python assembler.py path\to\program.txt
```

The assembler isn't sensitive to the register, tabulation and comments are ignored, spaces between operands are ignored. Underscores in immediate values that start with a digit are also ignored.

Link to the table that was used when making SALUT-2: https://docs.google.com/spreadsheets/d/1K6liOvKjDyqksuPSXaJNU8sKMBSrsMw3m8DJNx-0K9s/edit?gid=0#gid=0

It contains instruction set, what flags do they set etc.

## Instruction set

Instructions follow this syntax:

```
(Mnemonic) (Operands separated by commas) ; (Comment after ';')
```

You can also put a comment after an empty line.

### Terms

General purpose registers: R0-R15 (Reg)

Special registers: PC, SP, IM. IA, PS (S.Reg)

Ports: P0-P3 (Port)

Flags: N, Z, C, V (or F0, F1, F2, F3) (Flag)

Immediate value: Imm

Immediate value is a value that is written directly into the memory.
It can be:

1. Decimal number from -65535 to 65535
2. Binary number that starts with "0b" from 0b0 to 0b1111_1111_1111_1111
3. Hexadecimal number that starts with "0x" form 0x0 to 0xFFFF
4. A character in single quotes - it's transformed into integer with python ord() function.
5. A name of a label or a constant.

### NOP

No operation instruction.

Actions: PC = PC + 1, next instruction signal

### STOP

Stops processor.

Actions: PC = PC + 1

For all instructions below actions `PC = PC + 1 (or + 2)` and `next instruction signal` won't be mentioned.

### RET

Returns from a function - pops stack into the PC.

Actions: PC = Memory[SP], SP = SP + 1

### CALL Address

Calls a function by given address.

Possible uses:

```
CALL IA|Reg|Imm
```

Actions: SP = SP - 1, Memory[SP] = PC, PC = Address

### Jump instructions: Mnemonic Address

| Mnemonic  |            Instruction            |    Condition     |
| :-------: | :-------------------------------: | :--------------: |
|    JS     |         Jump if negative          |        N         |
|    JNS    |     Jump if positive or zero      |      not N       |
|  JE (JZ)  |      Jump if equal (if zero)      |        Z         |
| JNE (JNZ) |   Jump if not equal (not zero)    |      not Z       |
| JC (JAE)  | Jump if carry (if above or equal) |        C         |
| JNC (JB)  |   Jump if not carry (if below)    |      not C       |
|    JO     |         Jump if overflow          |        V         |
|    JNO    |       Jump if not overflow        |      not V       |
|    JL     |           Jump if less            |        SL        |
|    JGE    |     Jump if greater or equal      |      not SL      |
|    JA     |           Jump if above           |   C and not Z    |
|    JBE    |      Jump if below or equal       |    not C or Z    |
|    JG     |          Jump if greater          | not SL and not Z |
|    JLE    |       Jump if less or equal       |     SL or Z      |
|    JMP    |               Jump                |       True       |

Above means unsigned greater, below means unsigned less.

JAE and JB can be used instead of JC and JNC

Possible uses:

```
JMP Reg|Imm
```

Actions: PC = Reg|Imm

### MOV Destination, Value

MOV moves a value from one register to another or puts a value into a register from memory.

Possible uses:

```
MOV PC|IM|IA|PS, Reg|Imm
MOV Flag, Reg|Imm
MOV Reg, S.Reg|Reg|Imm|Flag
```

MOV Flag, Value sets the least significant bit of the number to the flag in PS.

MOV IM or PS sets the 4 least significant bits of the number to the special register.

If you move a value into a flag or PS SL flag will be recalculated as N xor V.

MOV PC, Reg|Imm does the same thing as JMP Reg|Imm.

Actions: Destination = Value

### SWAP Reg 1, Reg 2

Swaps two registers.

Actions: Reg 1, Reg 2 = Reg 2, Reg 1

### DROP

Drops a value from the stack - increments SP. In reality the value still stays in the end of the memory but will be rewritten after pushing a new value to the same address.

Actions: SP = SP + 1

### PUSH Value

Pushes a value into the stack.

Possible uses:

```
PUSH S.Reg|Reg|Imm
```

When PS is pushed it includes SL flag as a fifth bit.

Actions: SP = SP - 1, Memory[SP] = Value

### POP Destination

Pops the last value from the stack into the given destination.

Possible uses:

```
POP PC|IM|IA|PS|Reg
```

When PS is popped into it includes SL flag as a fifth bit.

POP PC does the same thing as RET.

Actions: Destination = Memory[SP], SP = SP + 1

### PEEK Destination

Sets destination to the last value from the stack without changing it.

Possible uses:

```
PEEK PC|IM|IA|PS|Reg
```

When PS is peeked into it includes SL flag as a fifth bit.

Actions: Destination = Memory[SP]

### IN Destination, Value

Sets destination to the value from specified in-port.

Possible uses:

```
IN Reg, Port
```

Actions: Destination = Value

### OUT Destination, Value

Outputs value to the specificed out-port.

Possible uses:

```
OUT Port, Reg|Imm
```

Actions: Outputs 1 tick signal

### STR [Address], Value

Stores a value into the RAM at specified address. Address is put in square brackets.

Possible uses:

```
STR [Reg], Reg
STR [Reg+Reg], Reg
STR [Reg], Imm
STR [Imm], Reg
```

Actions: Memory[Address] = Value

### LDR Destination, [Address]

Loads a value from RAM at specifide address into the register.

Possible uses:

```
LDR Reg, [Reg]
LDR Reg, [Reg+Reg]
LDR Reg, [Imm]
```

Actions: Destination = Memory[Address]

### RND Destination

Moves a pseudorandom number into a register.

Possible uses:

```
RND Reg
RND     (Only sets flags)
```

Actions: Destination = Pseudorandom number

### MSB Value

Sets N to the most significant bit of a register.

Possible uses:

```
MSB Reg
```

Actions: N = MSB of Value

### LSB Value

Sets N to the least significant bit of a register.

Possible uses:

```
LSB Reg
```

Actions: N = LSB of Value

### SL

Calcualtes SL flag manually.

Possible uses:

```
SL
```

Actions: SL = N xor V

### Logic instructions: Mnemonic Destination, Value 1, Value 2

Logic operations are: AND, OR, XOR, NAND, NOR, XNOR

Possible uses:

```
Mnemonic Reg, Reg, Reg|Imm
Mnemonic Reg, Reg|Imm, Reg
```

First register is destination, other two are the operands for the logic operation.

Actions: Destination = Operation(Value 1, Value 2)

### NOT Destination, Value

Inverts all bits of the value.

Possible uses:

```
NOT Reg, Reg
```

Actions: Destination = NOT Value

### INC Destination, Value

Increments value.

Possible uses:

```
INC Reg, Reg
```

Actions: Destination = Value + 1

### DEC Destination, Value

Decrements value.

Possible uses:

```
DEC Reg, Reg
```

Actions: Destination = Value - 1

### NEG Destination, Value

Negates a value (two's complement).

Possible uses:

```
NEG Reg, Reg
```

Actions: Destination = -Value

### ABS Destination, Value

Negates a value (two's complement) if value is negative, else leaves value unchanged.

Possible uses:

```
ABS Reg, Reg
```

Actions: Destination = |Value|

### CMP Value 1, Value 2

Compares two values and set flags according to subtraction.

Possible uses:

```
CMP Reg, Reg
CMP Reg, Imm
CMP Imm, Reg
```

Actions: Subtract Value 2 from Value 2

### ADD Destination, Value 1, Value 2

Adds two values.

Possible uses:

```
ADD Reg, Reg, Reg
ADD Reg, Reg, Imm
ADD Reg, Imm, Reg
```

Actions: Destination = Value 1 + Value 2

### ADC Destination, Value 1, Value 2

Adds two values and a carry flag.

Possible uses:

```
ADC Reg, Reg, Reg
ADC Reg, Reg, Imm
ADC Reg, Imm, Reg
```

Actions: Destination = Value 1 + Value 2 + C

### SUB Destination, Value 1, Value 2

Subtracts Value 2 from Value 1.

Possible uses:

```
SUB Reg, Reg, Reg
SUB Reg, Reg, Imm
SUB Reg, Imm, Reg
```

Actions: Destination = Value 1 - Value 2

### SBC Destination, Value 1, Value 2

Subtracts Value 2 and a carry flag from Value 1.

Possible uses:

```
SUB Reg, Reg, Reg
SUB Reg, Reg, Imm
SUB Reg, Imm, Reg
```

Actions: Destination = Value 1 - Value 2 - C

### MUL Destination, Value 1, Value 2

Multiplies two unsigned values.

Possible uses:

```
MUL Reg, Reg, Reg
MUL Reg, Reg, Imm
MUL Reg, Imm, Reg
```

Actions: Destination = Value 1 \* Value 2

### DIV Quotient Destination, Remainder Destination, Value 1, Value 2

Divides two unsigned values.

Possible uses:

```
DIV Reg, Reg, Reg, Reg
DIV Reg, Reg, Reg  (Remainder isn't saved)
DIV Reg, Reg, Imm
```

`DIV Reg, Imm, Reg` isn't implemented.

Actions: Quotient Destination = Value 1 / Value 2, Remainder destination (if specificed) = Value 1 % Value 2

## Flags

N - Negative flag. Most of the time it shows if the result of an instruction was negative in two's complement (most significant bit is on)

Z - Zero flag. It shows if the result of an instruction was zero.

C - Carry flag. Most of the time it shows if adding two numbers produced a carry or subtracting two numbers produced a borrow.

V - Overflow flag. Most of the time it shows that the result after adding/subtracting two positive numbers is negative or the other way around.

By "sets flag" below I mean that if condition is true it sets it as 1, else 0.

### MOV

Whenever you move a value into a flag or PS, SL flag is recalculated (SL = N xor V). All other flags are unchanged.

### POP, PEEK

If you pop or peek into PS it won't recalculate SL flag and set it as fifth bit instead.

### MSB

Sets N flag as the most significant bit of a specificed register.

### LSB

Sets N flag as the least significant bit of a specified register.

### RND

Sets N as the most significant bit of a pseudorandom number.

### SL

Sets SL as N xor V.

### INC, DEC

Sets N as the most significant bit of the result.

Sets Z if the result is zero.

Sets V if input is positive and result is negative or the other way around.

### NEG

Sets N as the most significant bit of the result.

Sets Z if the result is zero.

Sets V if negating a negative number still gave a negative (happens with -32678)

### ABS

Sets N as the most significant bit of the result. (ABS can return negatie value if input is -32678)

Sets Z if the result is zero.

Sets V = N.

### Logic instructions:

Sets N as the most significant bit of the result. (-32678)

Sets Z if the result is zero.

### Shift and roll instructions:

Sets N as the most significant bit of the result. (-32678)

Sets Z if the result is zero.

Sets C if the part that was shifted/rolled out of the register contained at least one turned on bit.

### ADD, ADC, SUB, SBC and CMP

CMP is the same as SUB except it doesn't save the result.

Sets N if the result is negative.

Sets Z if the result is zero

Sets C as carry (no borrow) out bit.

Sets V if adding (subtracting) two positive numbers gave a negative or the other way around.

### MUL

Sets N if the result is negative.

Sets Z if the result is zero

Sets C if the result is bigger than 65535

### DIV, REM

Sets N if the result is negative.

Sets Z if the result is zero

Sets C if the remainder isn't zero.

Sets V if division by zero.

## Labels

If you want your program to jump to some specific place, instead of calculating the number of the needed memory slot in machine code by yourself you can just put a label.

For example:

```
; cycle that goes from 10 to 0
MOV r0, 10
label_1:
    DEC r0, r0
    JNZ label_1
STOP
```

Labels are defined by putting ':' in the end of the line.

Labels are just constants that contain addresses. You can use it just like any other immediate value.

Names of labels can't start with digit. Global labels can't point to the same address ~~because I don't know how my own code works~~ because of they way assembler works.

### Local Labels

If name of a label starts with a dot it becomes a local label. Local labels must follow a global label.

Local labels with the same name can follow two different global labels.

for exammple:

```
global1:
    MOV r0, 10
    .local:
        DEC r0, r0
        JNZ .local

global2:
    MOV r0, 5
    .local:
        DEC r0, r0
        JNZ .local
```

First JNZ will go to .local label that follows global1 and second JNZ will go to .local label that follows global2.

## Special Instructions

Special instructions are marked with a dot in the start. They don't actually have an opcode and are used by assembler only.

### .DATA Value

.DATA just puts the value in this place in the ram.

Possible uses:

```

.DATA Imm

```

### .EQU Name, Value

.EQU defines a constant. After definig a constant you can use the value everywhere.

Possible uses:

```
.EQU Name, IMM

```

Constant name can't start with a digit.

### .INCLUDE Path

.INCLUDE instruction copy and pastes code from another file where you put it.

Recursive includes lead to an error. All of the labels and constants from included files are included as well.

Possible uses:

```
.INCLUDE Path
```

# Thank you for reading

I hope this was useful. I'll probably rewrite the documentation later.
