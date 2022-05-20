import json

from .common import CardanoNetwork, ScriptMethod


class ScriptError(Exception):
    code = 500001
    message = "Script Error"

    def __init__(self, message, error=None, traceback=None, additional_context={}):
        self.message = message
        self.error = error
        self.traceback = traceback
        self.additional_context = additional_context

    def __str__(self):
        error_str = f"Error {self.code}: {self.message}\n"
        if self.error:
            error_str += f" Error: {self.error}"
        if self.traceback:
            error_str += f" Traceback: {self.traceback}"
        if self.additional_context:
            error_str += f" Context: {self.additional_context}"
        return error_str

    def json_str(self):
        return json.dumps(
            {
                "code": self.code,
                "message": self.message,
                "context": self.additional_context,
            },
        )


class InsufficientBalance(ScriptError):
    code = 400001
    message = "Insufficient Balance"

    def __init__(self, required_amount, current_amount):
        super().__init__(
            message=self.message,
            additional_context={
                "required_amount": required_amount,
                "current_amount": current_amount,
            },
        )


class InvalidMethod(ScriptError):
    code = 400002
    message = "Invalid Method"
    allowed_methods = [method.value for method in ScriptMethod]

    def __init__(self, method):
        super().__init__(
            message=self.message,
            additional_context={
                "allowed_methods": self.allowed_methods,
                "method": method,
            },
        )


class InvalidNetwork(ScriptError):
    code = 400003
    message = "Invalid Method"
    allowed_methods = [network.value for network in CardanoNetwork]

    def __init__(self, network):
        super().__init__(
            message=self.message,
            additional_context={
                "allowed_methods": self.allowed_methods,
                "network": network,
            },
        )


class InvalidFileError(ScriptError):
    code = 400004
    message = "Invalid File Input"

    def __init__(self, file, message, error=None, traceback=None):
        super().__init__(
            message=message or self.message,
            error=error,
            traceback=traceback,
            additional_context={
                "file": file,
            },
        )


class InvalidType(ScriptError):
    code = 400005
    message = "Invalid Value Type"

    def __init__(self, type, message):
        super().__init__(
            message=message or self.message,
            additional_context={"type": type},
        )


class EmptyList(ScriptError):
    code = 400006
    message = "List is empty"

    def __init__(self, field):
        super().__init__(
            message=self.message,
            additional_context={"field": field},
        )
