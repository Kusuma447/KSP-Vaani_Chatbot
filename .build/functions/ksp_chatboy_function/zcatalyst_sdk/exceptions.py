import warnings


class CatalystError(Exception):
    def __init__(self, code, message, value=None, status_code = None):
        self._code = code
        self._message = message
        self._http_status_code = status_code
        self._value = value
        Exception.__init__(self, self.to_string())

    @property
    def code(self):
        return self._code

    @property
    def message(self):
        return self._message

    @property
    def value(self):
        return self._value

    @property
    def status_code(self):
        return self._http_status_code

    def to_json(self):
        json_dict = {"code": self._code, "message": self._message}
        if self._value:
            json_dict['value'] = self._value
        if self._http_status_code:
            json_dict['status_code'] = self._http_status_code
        return json_dict

    def to_string(self):
        return str(self.to_json())


class CatalystCredentialError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystAppError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystAPIError(CatalystError):
    def __init__(self, code, message, value=None, http_status_code=None):
        self.http_status_code = http_status_code
        CatalystError.__init__(self, code, message, value, self.http_status_code)

    @property
    def status_code(self):
        return self.http_status_code


class CatalystCacheError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystDatastoreError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystFunctionError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystMailError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystFilestoreError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystAuthenticationError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystZCQLError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystCronError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystCircuitError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystConnectorError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystPushNotificationError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystSearchError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystZiaError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class BrowserLogicError(CatalystError):
    """
    SmartBrowz Exceptions
    This Error Class is deprecated and may be removed in future version
    """

    def __init__(self, code, message, value=None):
        warnings.warn(
            "The BrowserLogicError class is deprecated and"
            " will be removed in a future version."
            " Use CatalystSmartBrowzError instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        CatalystError.__init__(self, code, message, value)


class CatalystSmartBrowzError(CatalystError):
    """
    Error class for Catalyst SmartBrowz exceptions
    """

    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class QuickMLError(CatalystError):
    """
    QuickML Exceptions
    This Error Class is deprecated and may be removed in future version
    """

    def __init__(self, code, message, value=None):
        warnings.warn(
            "The QuickMLError class is deprecated and"
            + " will be removed in a future version."
            " Use CatalystQuickMLError instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        CatalystError.__init__(self, code, message, value)


class CatalystQuickMLError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystStratusError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)

class CatalystPipelineError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)


class CatalystNoSqlError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)

class CatalystConnectionError(CatalystError):
    def __init__(self, code, message, value=None):
        CatalystError.__init__(self, code, message, value)

class CatalystDeprecationWarning(Warning):
    pass
