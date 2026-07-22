from ..exceptions import (
    CatalystError
)

class CatalystJobSchedulingError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)
