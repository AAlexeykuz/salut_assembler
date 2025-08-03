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

MM just outputs every single register or memory slots that could be read and has input for every register that could be written in.

It has these modules:

1. RAM - Random access memory

RAM has 16-bit addresses and contains 16-bit memory slots, so the CPU has 128 KiB of RAM in total.

2. Registers

There are 16 general purpose registers (16-bit) from R0 to R15.

3. Ports

There are 4 in-ports and 4 out-ports from P0 TO P3.

Out-ports can't be read, they can only output values from register or memory. When they output a value they turn 17th signal bit on, no matter what the output is. Output lasts only 1 tick.

In-ports can be read in a register. After one tick input in-ports memorise the value (input should also turn signal bits on so that the CPU would know input happened).

Signal bits are marked white on the build.

4. Special Registers

1. PC - Program counter. It's where CPU reads instructions from.

1. SP - Stack pointer. It shows the top of the stack.

1. IM - Input mask. It contains 4 bits that control from which ports input handling can be triggered.

1. IA - Input address. It tells where input handling function is in the memory.

When input signal bits turn on, if the port in which they're turned on is set in IM it clears signal bits from every port and executes CALL IA instruction, interrupting others.

5. Flags

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

All of the modules are 16 bit. They get input from MM and outputs on decoder signal.
