import contextlib
import json
import sys
from pathlib import Path
from typing import Optional, cast

from memory_block_data_path import MEMORY_BLOCK_DATA_PATH
from salut.errors import (
    AssemblerError,
    AssemblerNameError,
    InstructionError,
    LabelError,
    OperandError,
    RecursiveIncludeError,
    UndefinedValueError,
)
from salut.utils import (
    FLAG_NAMES,
    FLAG_NUMBER_NAMES,
    IMM,
    INSTRUCTIONS,
    NAME,
    PATH,
    PORT_NAMES,
    REGISTER_NAMES,
    RESERVED_NAMES,
    SQUARED_IMM,
    SQUARED_R,
    SQUARED_SUM_R,
    Instruction,
    immediate_to_int,
)


class Assembler:
    _illegal_characters: str = " :,-+[]'"

    def __init__(self, address_shift: int, included_files: Optional[list[str]]) -> None:
        self._address_shift: int = address_shift
        self._line_count: int = 0
        self._word_count: int = 0  # одно слово - 16 бит
        self._constants: dict[str, int] = {}  # константы, объявленные через .equ
        self._global_labels: dict[str, int] = {}  # глобальная: адрес
        self._local_labels: dict[
            str, dict[str, int]  # глобальная: {локальная: адрес}
        ] = {}
        self._included_names: list[str | tuple[str, str]] = []
        if included_files is None:
            included_files = []
        self._included_files = included_files
        self._was_error = False
        self._word_to_line: dict[
            int, int
        ] = {}  # номер слова: номер строки (для принта ошибок)

    @staticmethod
    def _format_line(line: str) -> str:
        """Убирает комментарии, табуляцию и превращает всё в верхний регистр"""
        return line.split(";")[0].upper().strip()

    @staticmethod
    def _parse_line(line: str) -> tuple[str, list[str]]:
        """Возвращает имя инструкции и её операнды из форматированной (непустой) строчки кода"""
        splitted_line = line.split(maxsplit=1)
        if len(splitted_line) == 1:
            return line, []
        instruction_name = splitted_line[0]
        operands = splitted_line[1].replace(" ", "").split(",")
        return instruction_name, operands

    @staticmethod
    def _find_operand_patterns(instruction_name: str) -> list[str]:
        instructions = [
            instruction
            for instruction in INSTRUCTIONS
            if instruction_name in instruction.names
        ]
        patterns: list[list[set]] = [
            [set(possible_values) for possible_values in instruction.operands]
            for instruction in instructions
        ]
        for pattern in patterns:
            for possible_values in pattern:
                for iterable, name in [
                    (IMM, "Imm"),
                    (SQUARED_IMM, "[Imm]"),
                    (REGISTER_NAMES, "Reg"),
                    (SQUARED_R, "[Reg]"),
                    (SQUARED_SUM_R, "[Reg + Reg]"),
                    (FLAG_NAMES, "Flag"),
                    (FLAG_NUMBER_NAMES, "Flag"),
                    (PORT_NAMES, "Port"),
                    (NAME, "Name"),
                    (PATH, "Path\\to\\file.txt"),
                ]:
                    if set(iterable).issubset(possible_values):
                        possible_values.add(name)
                        possible_values.difference_update(iterable)
        return [
            f"{instruction_name} "
            + ", ".join(
                ["|".join(sorted(possible_values)) for possible_values in pattern]
            )
            for pattern in patterns
        ]

    @staticmethod
    def _find_instruction(instruction_name: str, operands: list[str]) -> Instruction:
        instructions = [
            instruction
            for instruction in INSTRUCTIONS
            if instruction_name in instruction.names
        ]
        if not instructions:
            raise InstructionError(f"Unknown instruction '{instruction_name}'.")

        if not all(operands):
            raise OperandError(
                "Missing operand: found two commas with nothing in between."
            )

        possible_operand_lengths = [
            len(instruction.operands) for instruction in instructions
        ]
        if possible_operand_lengths and len(operands) not in possible_operand_lengths:
            if len(set(possible_operand_lengths)) == 1:
                operand_number = possible_operand_lengths[0]
            else:
                operand_number = f"from {min(possible_operand_lengths)} to {max(possible_operand_lengths)}"
            operand_number: int | str
            raise OperandError(
                f"Instruction {instruction_name} expected {operand_number} operand{'s' if operand_number != 1 else ''}."
            )

        for instruction in instructions:
            if instruction.do_operands_match(operands):
                return instruction

        raise OperandError(
            f"Operands for instruction {instruction_name} don't match any valid pattern.\n"
            f"Expected patterns:\n{'\n'.join(Assembler._find_operand_patterns(instruction_name))}"
        )

    def _parse_instruction(
        self, instruction_name: str, operands: list[str]
    ) -> list[int | str] | list[int]:
        instruction = self._find_instruction(instruction_name, operands)
        if ".DATA" in instruction.names:
            return [operands[0]]
        if ".EQU" in instruction.names:
            self._check_constant_name(operands[0])
            self._constants[operands[0]] = immediate_to_int(operands[1])
            return []
        if ".INCLUDE" in instruction.names:
            path = operands[0].lower()
            if not Path(path).is_file():
                raise OperandError(f"Invalid path for file to include: {path}")
            if path in self._included_files:
                raise RecursiveIncludeError(
                    f"Recursion path:\n{'\n↓\n'.join(self._included_files)}"
                )
            with open(path) as program_file:
                machine_code = Assembler.assemble(
                    program_file.readlines(),
                    path=path,
                    address_shift=self._word_count,
                    included_files=self._included_files + [path],
                    previous_assembler=self,
                )
                if machine_code is None:
                    self._was_error = True
                    return []
                return machine_code
        return instruction.get_machine_code(operands)

    def _get_current_global_label(self, address: Optional[int] = None) -> str | None:
        if address is None:
            address = self._word_count
        address += self._address_shift
        global_labels = [(k, v) for k, v in self._global_labels.items() if v <= address]
        if not global_labels:
            return None
        return max(
            global_labels,
            key=lambda x: x[1],
        )[0]

    def _check_name(self, name: str) -> None:
        if not name:
            raise AssemblerNameError(
                "Name for a label or constant should have at least one character."
            )

        for char in Assembler._illegal_characters:
            if char in name:
                raise AssemblerNameError(
                    f"Name '{name}' contains illegal character '{char}'."
                )

        if name in RESERVED_NAMES:
            raise AssemblerNameError(
                f"Name '{name}' is reserved and can't be used as a label or constant name."
            )

        if name[0].isdigit():
            raise AssemblerNameError(
                "Names of labels or constants can't start with a digit."
            )

        if name in self._included_names:
            raise AssemblerNameError(
                f"Label or constant '{name}' is already defined in included files."
            )

    def _check_constant_name(self, const: str) -> None:
        self._check_name(const)
        if const in self._constants:
            raise AssemblerNameError(f"Constant {const} is already defined.")
        if const in self._global_labels or any(
            const in values for values in self._local_labels.values()
        ):
            raise AssemblerNameError(f"Name {const} is already defined as a label.")

    def _check_label_name(self, label: str) -> None:
        """Вызывает ошибку, если имя метки неправильное"""
        self._check_name(label)

        if label in self._constants:
            raise AssemblerNameError(f"Name '{label}' is already defined as a constant.")

        if label.startswith("."):
            global_label = self._get_current_global_label()
            if not global_label:
                raise AssemblerNameError(
                    "Local labels (starting with '.') must follow a global label."
                )
            if label in self._local_labels[global_label]:
                raise AssemblerNameError(
                    f"Local label '{label}' is already defined in this scope."
                )

        elif label in self._global_labels:
            raise AssemblerNameError(f"Global label '{label}' is already defined.")

    def _add_label(self, line: str) -> None:
        """Добавляет метку, если имя метки правильное, иначе вызывает ошибку

        Args:
            line (str): строка, оканчивающаяся на :
        """
        label = line[:-1].strip()
        address = self._word_count + self._address_shift

        self._check_label_name(label)

        # локальные метки
        current_global_label = cast(str, self._get_current_global_label())

        if label[0] == ".":
            self._local_labels[current_global_label][label] = address
            return

        # глобальные метки
        if (
            current_global_label in self._global_labels
            and self._global_labels[current_global_label] == address
        ):
            raise LabelError(
                f"Global labels '{current_global_label}' and '{label}' conflict as they point to the same address."
            )
        self._global_labels[label] = address
        self._local_labels[label] = {}

    def _assemble_line(self, line: str) -> list[int | str] | list[int]:
        self._line_count += 1

        formatted_line = self._format_line(line)
        if not formatted_line:
            return []

        if formatted_line.endswith(":"):
            self._add_label(formatted_line)
            return []

        output = self._parse_instruction(*self._parse_line(formatted_line))
        for i in range(len(output)):
            self._word_to_line[self._word_count + i] = self._line_count
        self._word_count += len(output)
        return output

    def replace_names(self, machine_code: list[int | str], path: Optional[str]) -> None:
        self._line_count = 0
        for i, value in enumerate(machine_code):
            self._line_count += 1
            if isinstance(value, int):
                continue
            with contextlib.suppress(ValueError):
                machine_code[i] = immediate_to_int(value)
                continue
            if value in self._global_labels:
                machine_code[i] = self._global_labels[value]
                continue
            if value in self._constants:
                machine_code[i] = self._constants[value]
                continue
            current_global_label = self._get_current_global_label(i)
            if current_global_label and value in self._local_labels[current_global_label]:
                machine_code[i] = self._local_labels[current_global_label][value]
                continue
            self._was_error = True
            self._line_count = self._word_to_line[i]
            self.print_error(UndefinedValueError(f"Undefined value: '{value}'"), path)

    def add_labels(
        self, global_labels: dict[str, int], local_labels: dict[str, dict[str, int]]
    ) -> None:
        for k, v in global_labels.items():
            if k in self._global_labels:
                raise NameError(
                    f"Global label '{k}' is already defined and cannot be included from another file."
                )
            self._global_labels[k] = v
            self._included_names.append(k)
        for k1, v1 in local_labels.items():
            for k2, v2 in v1.items():
                if k1 in self._local_labels and k2 in self._local_labels[k1]:
                    raise NameError(
                        f"Local label '{k2}' of global label '{k1}' is already defined and cannot be included from another file."
                    )
                if k1 not in self._local_labels:
                    self._local_labels[k1] = {}
                self._local_labels[k1][k2] = v2
                self._included_names.append((k1, k2))

    def add_constants(self, constants: dict[str, int]) -> None:
        for k, v in constants.items():
            if k in self._constants:
                raise NameError(
                    f"Constant '{k}' is already defined and cannot be included from another file."
                )
            self._constants[k] = v
            self._included_names.append(k)

    def print_error(self, error: Exception, path: Optional[str]) -> None:
        print(
            f"{error.__class__.__name__} on line {self._line_count}{f' in {path}' if path else ''}:\n{error}\n"
        )

    @staticmethod
    def print_machine_code(machine_code: list[int]) -> None:
        line_width = 8
        for i in range(0, len(machine_code), line_width):
            print(
                format(i, "04x")
                + "\t"
                + "  ".join(format(j, "04X") for j in machine_code[i : i + line_width])
            )

    @classmethod
    def assemble(
        cls,
        lines: list[str],
        path: Optional[str] = None,
        address_shift: int = 0,
        included_files: Optional[list[str]] = None,
        previous_assembler: Optional["Assembler"] = None,
    ) -> Optional[list[int] | list[int | str]]:
        assembler = cls(address_shift, included_files)
        machine_code = []
        for line in lines:
            try:
                machine_code.extend(assembler._assemble_line(line))
            except AssemblerError as error:
                assembler.print_error(error, path)
                assembler._was_error = True
        if not included_files:
            assembler.replace_names(machine_code, path)
        if previous_assembler:
            try:
                previous_assembler.add_labels(
                    assembler._global_labels, assembler._local_labels
                )
                previous_assembler.add_constants(assembler._constants)
            except NameError as error:
                assembler.print_error(error, path)
                assembler._was_error = True
        memory_use_percentage = len(machine_code) * 100 / 65536
        if len(machine_code) > 65536 and not included_files:
            print(
                "MemoryOverflowError:\n"
                f"Program is too large: used {memory_use_percentage:.2f}% of available RAM (128 KiB)."
            )
            assembler._was_error = True
        if assembler._was_error:
            return None
        if not included_files:
            # Assembler.print_machine_code(machine_code)
            print(machine_code[:100])
            print("Program assembled succesfully!")
            print(
                f"{assembler._word_count * 2} bytes ({memory_use_percentage:.2f}%) of RAM used."
            )
        return machine_code


def main() -> None:
    program_path = "program.txt" if len(sys.argv) <= 1 else sys.argv[1]
    with open(MEMORY_BLOCK_DATA_PATH) as memory_block_data_file:
        memory_block_data = json.load(memory_block_data_file)
    with open(program_path, encoding="utf-8") as program_file:
        machine_code = Assembler.assemble(program_file.readlines())
        if machine_code is None:
            return
        memory_block_data["data"] = machine_code
    with open(MEMORY_BLOCK_DATA_PATH, "w") as memory_block_data_file:
        json.dump(memory_block_data, memory_block_data_file, indent=4)


if __name__ == "__main__":
    main()
