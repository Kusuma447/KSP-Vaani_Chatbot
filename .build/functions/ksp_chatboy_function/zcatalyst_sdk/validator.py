""" A module of several validators """

from io import BufferedReader
import re
from typing import List, Optional, Type
import warnings

def is_valid_email(email):
    """
    validates the given value is a email

    Args:
        email: The value to validate.

    Returns:
        bool: Whether the value is a valid email or not.
    """
    regex = r'^[^@]+@[^@]+$'
    if re.fullmatch(regex, email):
        return True
    return False


def is_bool(value):
    """
    validates the given value is a boolean

    Args:
        value: The value to validate.

    Returns:
        bool: Whether the value is a boolean or not.
    """
    return isinstance(value, bool)


def _is_number(value):
    """
    validates the given value is a number

    Args:
        value: The value to validate.

    Returns:
        bool: Whether the value is a number or not.
    """
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def _is_integer(value):
    """
    validates the given value is a integer

    Args:
        value: The value to validate.

    Returns:
        bool: Whether the value is a integer or not.
    """
    try:
        int(str(value))
        return True
    except (ValueError, TypeError):
        return False


def is_string(value):
    """
    validates the given value is a string

    Args:
        value: The value to validate.

    Returns:
        bool: Whether the value is a string or not.
    """
    return isinstance(value, str)


def is_list(value):
    """
    validates the given value is a list

    Args:
        value: The value to validate.

    Returns:
        bool: Whether the value is a list or not.
    """
    return isinstance(value, list)


def is_dict(value):
    """
    validates the given value is a dict

    Args:
        value: The value to validate.

    Returns:
        bool: Whether the value is a dict or not.
    """
    return isinstance(value, dict)


def is_set(value):
    """
    validates the given value is a set

    Args:
        value: The value to validate.

    Returns:
        bool: Whether the value is a set or not.
    """
    return isinstance(value, set)


def is_tuple(value):
    """
    validates the given value is a tuple

    Args:
        value: The value to validate.

    Returns:
        bool: Whether the value is a tuple or not.
    """
    return isinstance(value, tuple)


def is_buffered_reader(value):
    """
    validates the given value is a buffered reader or not

    Args:
        value: The value to validate.

    Returns:
        bool: Whether the value is a buffered reader or not.
    """
    return isinstance(value, BufferedReader)


def is_non_empty_string(
    value,
    attr_name: Optional[str] = None,
    exception: Optional[Type[Exception]] = None
):
    """
    validates the given value is a non-empty string

    Args:
        value: The value to validate.
        attr_name: The name of the value to use in error.
        exception: The Exception class to raise error if needed.

    Returns:
        bool: Whether the value is a non-empty string or not.

    Raises:
        Exception: If the value is not a non-empty string and exception class is given.
    """
    if not is_string(value) or not value:
        if exception:
            raise exception(
                'Invalid-Argument',
                f'Value provided for {attr_name} is expected to be a non-empty string.',
                value
            )
        return False
    return True


def is_non_empty_string_or_number(
    value,
    attr_name: Optional[str] = None,
    exception: Optional[Type[Exception]] = None
):
    """
    validates the given value is a non-empty string or number

    Args:
        value: The value to validate.
        attr_name: The name of the value to use in error.
        exception: The Exception class to raise error if needed.

    Returns:
        bool: Whether the value is a valid non-empty string or number.

    Raises:
        Exception: If the value is not a non-empty string or number and
            exception class is given.
    """
    if is_non_empty_string(value) or _is_number(value):
        return True
    if exception:
        raise exception(
            'Invalid-Argument',
            f'Value provided for {attr_name} is expected to be a non-empty string or number.',
            value
        )
    return False


def is_parsable_number(
    value,
    attr_name: Optional[str] = None,
    exception: Optional[Type[Exception]] = None
):
    """
    validates the given value is a parsable number

    Args:
        value: The value to validate.
        attr_name: The name of the value to use in error.
        exception: The Exception class to raise error if needed.

    Returns:
        bool: Whether the value is a parsable number.

    Raises:
        Exception: If the value is non parsable number and exception
            class is given.
    """

    if _is_number(value):
        return True

    if exception:
        raise exception(
            'Invalid-Argument',
            f'Value provided for {attr_name} is expected to be a parsable number.',
            value
        )
    return False


def is_parsable_integer(
    value,
    attr_name: Optional[str] = None,
    exception: Optional[Type[Exception]] = None
):
    """
    validates the given value is a parsable integer

    Args:
        value: The value to validate.
        attr_name: The name of the value to use in error.
        exception: The Exception class to raise error if needed.

    Returns:
        bool: Whether the value is a parsable integer.

    Raises:
        Exception: If the value is non parsable integer and
            exception class is given.
    """

    if _is_integer(value):
        return True

    if exception:
        raise exception(
            'Invalid-Argument',
            f'Value provided for {attr_name} is expected to be a parsable integer.',
            value
        )
    return False


def is_non_empty_list(
    value,
    attr_name: Optional[str] = None,
    exception: Optional[Type[Exception]] = None
):
    """
    validates the given value is a non-empty list

    Args:
        value: The value to validate.
        attr_name: The name of the value to use in error.
        exception: The Exception class to raise error if needed.

    Returns:
        bool: Whether the value is a valid non-empty list or not.

    Raises:
        Exception: If the value is not a non-empty list and exception class is given.
    """
    if not is_list(value) or not value:
        if exception:
            raise exception(
                'Invalid-Argument',
                f'Value provided for {attr_name} is expected to be a non-empty list.',
                value
            )
        return False
    return True

def is_non_empty_tuple(
    value,
    attr_name: Optional[str] = None,
    exception: Optional[Type[Exception]] = None
):
    """
    validates the given value is a non-empty tuple

    Args:
        value: The value to validate.
        attr_name: The name of the value to use in error.
        exception: The Exception class to raise error if needed.

    Returns:
        bool: Whether the value is a valid non-empty tuple or not.

    Raises:
        Exception: If the value is not a non-empty tuple and exception class is given.
    """
    if not is_tuple(value) or not value:
        if exception:
            raise exception(
                'Invalid-Argument',
                f'Value provided for {attr_name} is expected to be a non-empty tuple.',
                value
            )
        return False
    return True


def is_non_empty_dict(
    value,
    attr_name: Optional[str] = None,
    exception: Optional[Type[Exception]] = None
):
    """
    validates the given value is a non-empty dict

    Args:
        value: The value to validate.
        attr_name: The name of the value to use in error.
        exception: The Exception class to raise error if needed.

    Returns:
        bool: Whether the value is a valid non-empty dict or not.

    Raises:
        Exception: If the value is not a non-empty dict and exception class is given.
    """
    if not is_dict(value) or not value:
        if exception:
            raise exception(
                'Invalid-Argument',
                f'Value provided for {attr_name} is expected to be a non-empty dict.',
                value
            )
        return False
    return True


def is_keys_present(
    obj: dict,
    keys: List[str],
    attr_name: Optional[str] = None,
    exception: Optional[Type[Exception]] = None
):
    """
    validates a dict has given keys. Note: single level

    Args:
        obj: The obj to validate.
        keys: Keys to be check for presence.
        attr_name: The name of the value to use in error.
        exception: The Exception class to raise error if needed.

    Returns:
        bool: validity of the object

    Raises:
        Exception: If the given key is not present and if exception class is given.
    """
    if not is_non_empty_dict(obj, attr_name, exception):
        return False
    for key in keys:
        if key not in obj or obj[key] is None:
            if exception:
                raise exception(
                    'Invalid-Argument',
                    f"Value for the key '{key}' cannot be None or undefined in {attr_name} dict",
                    obj
                )
            return False
    return True


def is_deprecated_key_present(
    obj: dict,
    depkey: str,
    actkey: Optional[str] = None,
    delet : bool = False,
    warn: bool = False
):
    """
    validates a dict has deprecated key. Note: single level

    Args:
        obj: The obj to validate.
        depkey: Key to be check for deprecation.
        actkey: Actual key used istead of deprecated key
        delet : Delete a deprecated property if needed
        warn: The warnings class to raise warning if needed

    Returns:
        bool: validity of the object

    Raises:
        Warning: If the given key is deprecated and if Warning class is given.
    """
    if not is_non_empty_dict(obj):
        return False
    if depkey in obj:
        if warn:
            warnings.warn(f"{depkey} is deprecated. It will be removed soon.",DeprecationWarning)
        if actkey is not None:
            warnings.warn(f"Use {actkey} instead. ")
            obj[actkey] = obj[depkey]
        if delet:
            del obj[depkey]
        return True
    return False


def is_valid_url(url):
    """
    validates the given value is a valid url

    Args:
        email: The value to validate.

    Returns:
        bool: Whether the value is a valid url or not.
    """
    regex = """^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}
            \\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"""
    if re.match(regex, url):
        return True
    return False
