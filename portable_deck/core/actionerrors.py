"""Typed model validation failures, compatible with ValueError callers."""
class ActionValidationError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
