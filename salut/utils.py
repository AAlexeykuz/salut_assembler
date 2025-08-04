from typing import Literal, Optional

from salut.errors import AssemblerError

# регистры
REGISTER_NAMES = R = [f"R{i}" for i in range(16)]
SQUARED_R = [f"[{r}]" for r in REGISTER_NAMES]
SQUARED_SUM_R = [f"[{r1}+{r2}]" for r1 in REGISTER_NAMES for r2 in REGISTER_NAMES]
# порты
PORT_NAMES = P = [f"P{i}" for i in range(4)]
# специальные регистры
PC, SP, IM, IA, PS = ["PC"], ["SP"], ["IM"], ["IA"], ["PS"]
SPECIAL_REGISTER_NAMES = PC + SP + IM + IA + PS
# флаги
N, Z, C, V = ["N"], ["Z"], ["C"], ["V"]
FLAG_NAMES = N + Z + C + V
FLAG_NUMBER_NAMES = ["F0", "F1", "F2", "F3"]
F = FLAG_NAMES + FLAG_NUMBER_NAMES
# немедленные значения
IMM = ["0_IMMEDIATE"]
SQUARED_IMM = ["0_SQUARED_IMMEDIATE"]
NAME = ["0_NAME"]
PATH = ["0_PATH"]

RESERVED_NAMES = (
    REGISTER_NAMES + SPECIAL_REGISTER_NAMES + PORT_NAMES + F + SQUARED_R + SQUARED_SUM_R
)


def immediate_to_int(imm: str) -> int:
    imm = imm.replace("_", "")
    if imm.startswith("0X"):
        value = int(imm[2:], 16)
    elif imm.startswith("0B"):
        value = int(imm[2:], 2)
    elif imm.startswith("'") and imm.endswith("'") and len(imm) >= 3:
        value = ord(imm[1:-1])
    else:
        value = int(imm)
    if -65536 < value < 65536:
        return value
    raise ValueError("Immediate values must be in range [-65535; 65535]")


class Instruction:
    _register_bits = 4
    _flag_bits = _port_bits = 2

    def __init__(
        self,
        names: str | list[str],
        opcode: Optional[int] = None,
        operands: Optional[list[list[str]]] = None,
    ) -> None:
        if isinstance(names, str):
            names = [names]
        self.names: list[str] = names
        self._opcode: Optional[int] = opcode
        if operands is None:
            operands = []
        self.operands: list[list[str]] = operands

    @staticmethod
    def _is_immediate(value: str) -> bool:
        return value not in (
            REGISTER_NAMES
            + SPECIAL_REGISTER_NAMES
            + FLAG_NAMES
            + FLAG_NUMBER_NAMES
            + PORT_NAMES
            + SQUARED_R
            + SQUARED_SUM_R
        )

    @staticmethod
    def _is_squared(value: str) -> bool:
        if len(value) < 3:
            return False
        return value.startswith("[") and value.endswith("]")

    @staticmethod
    def _is_immediate_squared(value: str) -> bool:
        return Instruction._is_squared(value) and Instruction._is_immediate(
            value.strip("[]")
        )

    def do_operands_match(self, operands: list[str]) -> bool:
        if len(operands) != len(self.operands):
            return False
        for i, operand in enumerate(operands):
            if operand in self.operands[i]:
                continue
            if self._is_immediate(operand) and any(
                j in self.operands[i] for j in ["0_IMMEDIATE", "0_NAME", "0_PATH"]
            ):
                continue
            if (
                self._is_immediate_squared(operand)
                and "0_SQUARED_IMMEDIATE" in self.operands[i]
            ):
                continue
            return False
        return True

    def _get_word_usage(self) -> Literal[1, 2]:
        """Возвращает, сколько слов использует инструкция"""
        if (
            any("IMMEDIATE" in possible_values for possible_values in self.operands)
            or len(self.operands) == 4
            or "REM" in self.names  # REM и DIV c 4 операндами используют IMMEDIATE неявно
        ):
            return 2
        return 1

    @staticmethod
    def _place_immediate_last(operands: list[str]) -> None:
        for i, operand in enumerate(operands):
            if Instruction._is_immediate(operand) or Instruction._is_immediate_squared(
                operand
            ):
                operands[i], operands[-1] = operands[-1], operands[i]  # noqa: PLR1736

    def _normalize_operands(self, operands: list[str]) -> list[str]:
        """
        1) Убирает специальные регистры, превращает флаги: N=F0, Z=F1, C=F2, V=F3
        2) Превращает [Reg+Reg] в [Reg], [Reg]
        3) Ставит порты, флаги и значения в квадратных скобках первее регистров.
        Убирает квадратные скобки.
        4) Ставит немедленное значение в конце.
        """
        operands = [
            f"F{FLAG_NAMES.index(operand)}" if operand in FLAG_NAMES else operand
            for operand in operands
            if operand not in SPECIAL_REGISTER_NAMES
        ]

        for operand in operands[:]:
            if "+" in operand:
                operands.remove(operand)
                operand_1, operand_2 = operand.split("+")
                operands.append(operand_1 + "]")
                operands.append("[" + operand_2)

        squared_operands = [
            operand.strip("[]") for operand in operands if self._is_squared(operand)
        ]
        operands = squared_operands + [
            operand for operand in operands if operand not in squared_operands
        ]
        flag_and_port_oprands = [
            operand for operand in operands if operand in (FLAG_NUMBER_NAMES + PORT_NAMES)
        ]
        operands = flag_and_port_oprands + [
            operand for operand in operands if operand not in flag_and_port_oprands
        ]

        self._place_immediate_last(operands)

        return operands

    @staticmethod
    def _get_bits(operand: str) -> int:
        if operand in PORT_NAMES:
            return Instruction._port_bits
        if operand in FLAG_NUMBER_NAMES:
            return Instruction._flag_bits
        if operand in REGISTER_NAMES:
            return Instruction._register_bits
        raise AssemblerError("Unexpected assembler error: operands were normalized wrong")

    @staticmethod
    def _get_operand_sum(operands: list[str]) -> int:
        ports = [operand for operand in operands if operand in PORT_NAMES]
        flags = [operand for operand in operands if operand in FLAG_NUMBER_NAMES]
        registers = [operand for operand in operands if operand in REGISTER_NAMES]
        operands = ports + flags + registers[::-1]
        sum_ = 0
        for i in operands:
            sum_ <<= Instruction._get_bits(i)
            sum_ += int(i[1:])
        # print(operands, format(sum_, "016b"))
        return sum_

    def get_machine_code(self, operands: list[str]) -> list[int | str]:
        if self._opcode is None:
            raise AssemblerError("Unexpected assembler exception.")
        operands = self._normalize_operands(operands)
        if not operands:
            return [self._opcode]
        has_immediate = self._is_immediate(operands[-1])
        if has_immediate and (len(operands) == 4 or "REM" in self.names):
            return [self._opcode, self._get_operand_sum(operands)]
        if has_immediate:
            return [self._opcode + self._get_operand_sum(operands[:-1]), operands[-1]]
        return [self._opcode + self._get_operand_sum(operands)]


INSTRUCTIONS: list[Instruction] = [
    Instruction("NOP", 0),
    Instruction("STOP", 1),
    Instruction("RET", 2),
    Instruction("CALL", 3, [IMM]),
    Instruction("JS", 4, [IMM]),
    Instruction("JNS", 5, [IMM]),
    Instruction(["JE", "JZ"], 6, [IMM]),
    Instruction(["JNE", "JNZ"], 7, [IMM]),
    Instruction(["JC", "JAE"], 8, [IMM]),
    Instruction(["JNC", "JB"], 9, [IMM]),
    Instruction("JO", 10, [IMM]),
    Instruction("JNO", 11, [IMM]),
    Instruction("JL", 12, [IMM]),
    Instruction("JGE", 13, [IMM]),
    Instruction("JA", 14, [IMM]),
    Instruction("JBE", 15, [IMM]),
    Instruction("JG", 16, [IMM]),
    Instruction("JLE", 17, [IMM]),
    Instruction("JMP", 18, [IMM]),
    Instruction("MOV", 18, [PC, IMM]),
    Instruction("MOV", 19, [IM, IMM]),
    Instruction("MOV", 20, [IA, IMM]),
    Instruction("MOV", 21, [PS, IMM]),
    Instruction("DROP", 22),
    Instruction("PUSH", 23, [PC]),
    Instruction("PUSH", 24, [SP]),
    Instruction("PUSH", 25, [IM]),
    Instruction("PUSH", 26, [IA]),
    Instruction("PUSH", 27, [PS]),
    Instruction("POP", 2, [PC]),
    Instruction("POP", 28, [IM]),
    Instruction("POP", 29, [IA]),
    Instruction("POP", 30, [PS]),
    Instruction("PEEK", 31, [PC]),
    Instruction("PEEK", 32, [IM]),
    Instruction("PEEK", 33, [IA]),
    Instruction("PEEK", 34, [PS]),
    Instruction("RND", 35),
    Instruction("DIV", 37, [R, R, R, R]),
    Instruction("REM", 38, [R, R, R]),
    Instruction("SL", 39),
    Instruction("MOV", 40, [F, IMM]),
    Instruction("OUT", 44, [P, IMM]),
    Instruction("CALL", 48, [IMM]),
    Instruction("JS", 64, [R]),
    Instruction("JNS", 80, [R]),
    Instruction(["JE", "JZ"], 96, [R]),
    Instruction(["JNE", "JNZ"], 112, [R]),
    Instruction(["JC", "JAE"], 128, [R]),
    Instruction(["JNC", "JB"], 144, [R]),
    Instruction("JO", 160, [R]),
    Instruction("JNO", 176, [R]),
    Instruction("JL", 192, [R]),
    Instruction("JGE", 208, [R]),
    Instruction("JA", 224, [R]),
    Instruction("JBE", 240, [R]),
    Instruction("JG", 256, [R]),
    Instruction("JLE", 272, [R]),
    Instruction("JMP", 288, [R]),
    Instruction("MOV", 304, [R, PC]),
    Instruction("MOV", 320, [R, SP]),
    Instruction("MOV", 336, [R, IM]),
    Instruction("MOV", 352, [R, IA]),
    Instruction("MOV", 368, [R, PS]),
    Instruction("MOV", 384, [IM, R]),
    Instruction("MOV", 400, [IA, R]),
    Instruction("MOV", 416, [PS, R]),
    Instruction("MOV", 432, [R, IMM]),
    Instruction("PUSH", 448, [R]),
    Instruction("POP", 464, [R]),
    Instruction("PEEK", 480, [R]),
    Instruction("STR", 496, [SQUARED_R, IMM]),
    Instruction("MSB", 512, [R]),
    Instruction("LSB", 528, [R]),
    Instruction("RND", 544, [R]),
    Instruction("CMP", 560, [R, IMM]),
    Instruction("CMP", 576, [IMM, R]),
    Instruction("STR", 592, [SQUARED_IMM, R]),
    Instruction("LDR", 608, [R, SQUARED_IMM]),
    Instruction("CALL", 624, [IA]),
    Instruction("MOV", 640, [R, F]),
    Instruction("MOV", 704, [F, R]),
    Instruction("IN", 768, [R, P]),
    Instruction("OUT", 832, [P, R]),
    Instruction("MOV", 1024, [R, R]),
    Instruction("SWAP", 1280, [R, R]),
    Instruction("LDR", 1536, [R, SQUARED_R]),
    Instruction("STR", 1792, [SQUARED_R, R]),
    Instruction("DEC", 2048, [R, R]),
    Instruction("INC", 2304, [R, R]),
    Instruction("CMP", 2560, [R, R]),
    Instruction("NOT", 2816, [R, R]),
    Instruction("NEG", 3072, [R, R]),
    Instruction("ABS", 3328, [R, R]),
    Instruction("ABS", 3328, [R, R]),
    Instruction("ADD", 3584, [R, R, IMM]),
    Instruction("ADD", 3584, [R, IMM, R]),
    Instruction("ADC", 3840, [R, R, IMM]),
    Instruction("ADC", 3840, [R, IMM, R]),
    Instruction("SUB", 4096, [R, R, IMM]),
    Instruction("SBC", 4352, [R, R, IMM]),
    Instruction("SUB", 4608, [R, R, IMM]),
    Instruction("SBC", 4864, [R, R, IMM]),
    Instruction("AND", 5120, [R, R, IMM]),
    Instruction("AND", 5120, [R, IMM, R]),
    Instruction("OR", 5376, [R, R, IMM]),
    Instruction("OR", 5376, [R, IMM, R]),
    Instruction("XOR", 5632, [R, R, IMM]),
    Instruction("XOR", 5632, [R, IMM, R]),
    Instruction("NAND", 5888, [R, R, IMM]),
    Instruction("NAND", 5888, [R, IMM, R]),
    Instruction("NOR", 6144, [R, R, IMM]),
    Instruction("NOR", 6144, [R, IMM, R]),
    Instruction("XNOR", 6400, [R, R, IMM]),
    Instruction("XNOR", 6400, [R, IMM, R]),
    Instruction("SHL", 6656, [R, R, IMM]),
    Instruction("SHR", 6912, [R, R, IMM]),
    Instruction("ROL", 7168, [R, R, IMM]),
    Instruction("ROR", 7424, [R, R, IMM]),
    Instruction("MUL", 7680, [R, R, IMM]),
    Instruction("MUL", 7680, [R, IMM, R]),
    Instruction("DIV", 7936, [R, R, IMM]),
    Instruction("LDR", 8192, [R, SQUARED_SUM_R]),
    Instruction("STR", 12288, [SQUARED_SUM_R, R]),
    Instruction("ADD", 16384, [R, R, R]),
    Instruction("ADC", 20480, [R, R, R]),
    Instruction("SUB", 24576, [R, R, R]),
    Instruction("SBC", 28672, [R, R, R]),
    Instruction("AND", 32768, [R, R, R]),
    Instruction("OR", 36864, [R, R, R]),
    Instruction("XOR", 40960, [R, R, R]),
    Instruction("NAND", 45056, [R, R, R]),
    Instruction("NOR", 49152, [R, R, R]),
    Instruction("XNOR", 53248, [R, R, R]),
    Instruction("MUL", 57344, [R, R, R]),
    Instruction("DIV", 61440, [R, R, R]),
    Instruction(".DATA", operands=[IMM]),
    Instruction(".EQU", operands=[NAME, IMM]),
    Instruction(".INCLUDE", operands=[PATH]),
]
