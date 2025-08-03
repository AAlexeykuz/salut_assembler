class AssemblerError(Exception):
    pass


class AssemblerNameError(AssemblerError):
    pass


class RecursiveIncludeError(AssemblerError):
    pass


class InstructionError(AssemblerError):
    pass


class UndefinedValueError(AssemblerError):
    pass


class OperandError(AssemblerError):
    pass


class LabelError(AssemblerError):
    pass
