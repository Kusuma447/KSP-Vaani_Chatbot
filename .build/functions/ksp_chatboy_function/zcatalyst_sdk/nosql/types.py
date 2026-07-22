import base64
from decimal import (
    Clamped,
    Context,
    Decimal,
    Inexact,
    Overflow,
    Rounded,
    Underflow,
)

import collections.abc as collections_abc

STRING = 'S'
NUMBER = 'N'
BINARY = 'B'
STRING_SET = 'SS'
NUMBER_SET = 'SN'
BINARY_SET = 'SB'
NULL = 'NULL'
BOOLEAN = 'BOOL'
MAP = 'M'
LIST = 'L'


NOSQL_CONTEXT = Context(
    Emin=-128,
    Emax=126,
    prec=38,
    traps=[Clamped, Overflow, Inexact, Rounded, Underflow],
)


BINARY_TYPES = (bytearray, bytes)


class Binary:
    """A class for representing Binary in nosql

    Especially for Python 2, use this class to explicitly specify
    binary data for item in NoSQL. It is essentially a wrapper around
    binary. Unicode and Python 3 string types are not allowed.
    """

    def __init__(self, value):
        if not isinstance(value, BINARY_TYPES):
            types = ', '.join([str(t) for t in BINARY_TYPES])
            raise TypeError(f'Value must be of the following types: {types}')
        self.value = value

    def __eq__(self, other):
        if isinstance(other, Binary):
            return self.value == other.value
        return self.value == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return f'Binary({self.value!r})'

    def __str__(self):
        return self.value

    def __bytes__(self):
        return self.value

    def __hash__(self):
        return hash(self.value)


class TypeSerializer:
    """This class serializes Python data types to NoSQL types."""

    def serialize(self, value):
        """The method to serialize the Python data types.

        :param value: A python value to be serialized to NoSQL. Here are
            the various conversions:

            Python                                  NoSQL
            ------                                  --------
            None                                    {'NULL': True}
            True/False                              {'BOOL': True/False}
            int/Decimal                             {'N': str(value)}
            string                                  {'S': string}
            Binary/bytearray/bytes (py3 only)       {'B': bytes}
            set([int/Decimal])                      {'SN': [str(value)]}
            set([string])                           {'SS': [string])
            set([Binary/bytearray/bytes])           {'SB': [bytes]}
            list                                    {'L': list}
            dict                                    {'M': dict}

            For types that involve numbers, it is recommended that ``Decimal``
            objects are used to be able to round-trip the Python type.
            For types that involve binary, it is recommended that ``Binary``
            objects are used to be able to round-trip the Python type.

        :rtype: dict
        :returns: A dictionary that represents a nosql data type.
        """
        nosql_type = self._get_nosql_type(value)
        serializer = getattr(self, f'serialize_{nosql_type}'.lower())
        return {nosql_type: serializer(value)}

    def _get_nosql_type(self, value):
        nosql_type = None

        if self._is_null(value):
            nosql_type = NULL

        elif self._is_boolean(value):
            nosql_type = BOOLEAN

        elif self._is_number(value):
            nosql_type = NUMBER

        elif self._is_string(value):
            nosql_type = STRING

        elif self._is_binary(value):
            nosql_type = BINARY

        elif self._is_type_set(value, self._is_number):
            nosql_type = NUMBER_SET

        elif self._is_type_set(value, self._is_string):
            nosql_type = STRING_SET

        elif self._is_type_set(value, self._is_binary):
            nosql_type = BINARY_SET

        elif self._is_map(value):
            nosql_type = MAP

        elif self._is_listlike(value):
            nosql_type = LIST

        else:
            msg = f'Unsupported type "{type(value)}" for value "{value}"'
            raise TypeError(msg)

        return nosql_type

    def _is_null(self, value):
        if value is None:
            return True
        return False

    def _is_boolean(self, value):
        if isinstance(value, bool):
            return True
        return False

    def _is_number(self, value):
        if isinstance(value, (int, Decimal)):
            return True
        if isinstance(value, float):
            raise TypeError(
                'Float types are not supported. Use Decimal types instead.'
            )
        return False

    def _is_string(self, value):
        if isinstance(value, str):
            return True
        return False

    def _is_binary(self, value):
        if isinstance(value, (Binary, bytearray, bytes)):
            return True
        return False

    def _is_set(self, value):
        if isinstance(value, collections_abc.Set):
            return True
        return False

    def _is_type_set(self, value, type_validator):
        if self._is_set(value):
            if False not in map(type_validator, value):
                return True
        return False

    def _is_map(self, value):
        if isinstance(value, collections_abc.Mapping):
            return True
        return False

    def _is_listlike(self, value):
        if isinstance(value, (list, tuple)):
            return True
        return False

    def serialize_null(self, value):
        return value

    def serialize_bool(self, value):
        return value

    def serialize_n(self, value):
        number = str(NOSQL_CONTEXT.create_decimal(value))
        if number in ['Infinity', 'NaN']:
            raise TypeError('Infinity and NaN not supported')
        return number

    def serialize_s(self, value):
        return value

    def serialize_b(self, value):
        if isinstance(value, Binary):
            value = value.value
        return base64.b64encode(value).decode('utf-8')

    def serialize_ss(self, value):
        return [self.serialize_s(s) for s in value]

    def serialize_sn(self, value):
        return [self.serialize_n(n) for n in value]

    def serialize_sb(self, value):
        return [self.serialize_b(b) for b in value]

    def serialize_l(self, value):
        return [self.serialize(v) for v in value]

    def serialize_m(self, value):
        return {k: self.serialize(v) for k, v in value.items()}


class TypeDeserializer:
    """This class deserializes NoSQL types to Python types."""

    def deserialize(self, value):
        """The method to deserialize the NoSQL data types.

        :param value: A NoSQL value to be deserialized to a pythonic value.
            Here are the various conversions:

            NoSQL                                Python
            --------                                ------
            {'NULL': True}                          None
            {'BOOL': True/False}                    True/False
            {'N': str(value)}                       Decimal(str(value))
            {'S': string}                           string
            {'B': bytes}                            Binary(bytes)
            {'SN': [str(value)]}                    set([Decimal(str(value))])
            {'SS': [string]}                        set([string])
            {'SB': [bytes]}                         set([bytes])
            {'L': list}                             list
            {'M': dict}                             dict

        :returns: The pythonic value of the NoSQL type.
        """

        if not value:
            raise TypeError(
                'Value must be a nonempty dictionary whose key '
                'is a valid nosql type.'
            )
        nosql_type = list(value.keys())[0]
        try:
            deserializer = getattr(
                self, f'deserialize_{nosql_type}'.lower()
            )
        except AttributeError as exc:
            raise TypeError(f'nosql type {nosql_type} is not supported') from exc
        return deserializer(value[nosql_type])

    def deserialize_null(self, value):
        value = None
        return value

    def deserialize_bool(self, value):
        return value

    def deserialize_n(self, value):
        return NOSQL_CONTEXT.create_decimal(value)

    def deserialize_s(self, value):
        return value

    def deserialize_b(self, value):
        return Binary(base64.b64decode(value))

    def deserialize_sn(self, value):
        return set(map(self.deserialize_n, value))

    def deserialize_ss(self, value):
        return set(map(self.deserialize_s, value))

    def deserialize_sb(self, value):
        return set(map(self.deserialize_b, value))

    def deserialize_l(self, value):
        return [self.deserialize(v) for v in value]

    def deserialize_m(self, value):
        return {k: self.deserialize(v) for k, v in value.items()}
