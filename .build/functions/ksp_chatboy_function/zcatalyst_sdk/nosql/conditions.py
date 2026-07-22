from .types import TypeSerializer
from ..exceptions import CatalystNoSqlError


class AttrBase:
    """This class used to construct the attribute condition dict."""
    operator = ''

    def __init__(self, name, values):
        self.name = name
        self.value = values

    def get_condition(self):
        return {
            'attribute': self.name,
            'operator': self.operator,
            'value': TypeSerializer().serialize(self.value)
        }


class FuncBase:
    """This class used to construct the function condition dict."""
    operator = ''

    def __init__(self, name, value = None):
        self.args = []
        self.args.append({
            'attribute_path': name
        })
        self.values = value

    def get_condition(self):
        if self.values is not None:
            self.args.append(TypeSerializer().serialize(self.values))
        return {
            'function': {
                'function_name': self.operator,
                'args': self.args
            }
        }

class GroupBase:
    """This class used to construct the group condition dict."""

    operator = ''
    group= []

    def __init__(self, value):
        self.value = value

    def get_grouped_values(self):
        self.group.extend(self.value)

    def get_condition(self):
        self.get_grouped_values()
        return {
            'group_operator': self.operator,
            'group': self.group
        }


class Attr:
    """Represents an NoSql attribute condition."""

    def __init__(self, name):
        self.name = name

    def __and__(self, value):
        raise CatalystNoSqlError('AND', self)

    def __or__(self, value):
        raise CatalystNoSqlError('OR', self)

    def __invert__(self):
        raise CatalystNoSqlError('NOT', self)

    def equal(self, value):
        """Creates a condition where the attribute is equal to the value.

        :param value: The value that the attribute is equal to.
        """
        return Equals(self.name, value).get_condition()

    def not_equal(self, value):
        """Creates a condition where the attribute is not equal to the value.

        :param value: The value that the attribute is not equal to.
        """
        return NotEquals(self.name, value).get_condition()

    def less_than(self, value):
        """Creates a condition where the attribute is less than the value.

        :param value: The value that the attribute is less than.
        """
        return LessThan(self.name, value).get_condition()

    def less_than_equal(self, value):
        """Creates a condition where the attribute is less than or equal to the
           value.

        :param value: The value that the attribute is less than or equal to.
        """
        return LessThanEquals(self.name, value).get_condition()

    def greater_than(self, value):
        """Creates a condition where the attribute is greater than the value.

        :param value: The value that the attribute is greater than.
        """
        return GreaterThan(self.name, value).get_condition()

    def greater_than_equal(self, value):
        """Creates a condition where the attribute is greater than or equal to
           the value.

        :param value: The value that the attribute is greater than or equal to.
        """
        return GreaterThanEquals(self.name, value).get_condition()

    def begins_with(self, value):
        """Creates a condition where the attribute begins with the value.

        :param value: The value that the attribute begins with.
        """
        return BeginsWith(self.name, value).get_condition()

    def attr_in(self, value):
        """Creates a condition where the attribute is in the value.

        :param value: The value that the attribute is in.
        """
        return In(self.name, value).get_condition()

    def between(self, low_value, high_value):
        """Creates a condition where the attribute is greater than or equal
        to the low value and less than or equal to the high value.

        :param low_value: The value that the attribute is greater than or equal to.
        :param high_value: The value that the attribute is less than or equal to.
        """
        return Between(self.name, [low_value, high_value]).get_condition()

    def contains(self, values):
        """Creates a condition where the attribute is contains the value.

        :param value: The value that the attribute contains.
        """
        return Contains(self.name, values).get_condition()

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)


class Func:
    """Represents an NoSql function condition."""

    def __init__(self, name):
        self.name = name

    def exists(self):
        """Creates a condition where the attribute exists."""
        return AttributeExists(self.name).get_condition()

    def not_exists(self):
        """Creates a condition where the attribute does not exist."""
        return AttributeNotExists(self.name).get_condition()

    def attribute_type(self, value):
        """Creates a condition for the attribute type.

        :param value: The type of the attribute.
        """
        return AttributeType(self.name, value).get_condition()


class Group:
    """Represents an NoSql Group condition."""
    def __init__(self, value):
        self.value = value

    def with_and(self):
        """Creates a group condition where the condition and to the other condition

        :param value: The condition that the other condition is group with AND operator.
        """
        return And(self.value).get_condition()

    def with_or(self):
        """Creates a group condition where the condition or to the other condition

        :param value: The condition that the other condition is group with OR operator.
        """
        return Or(self.value).get_condition()

class Key(Attr):
    pass

class Equals(AttrBase):
    operator = 'equals'

class NotEquals(AttrBase):
    operator = 'not_equals'

class LessThan(AttrBase):
    operator = 'less_than'

class LessThanEquals(AttrBase):
    operator = 'less_equal'

class GreaterThan(AttrBase):
    operator = 'greater_than'

class GreaterThanEquals(AttrBase):
    operator = 'greater_equal'

class Between(AttrBase):
    operator = 'between'

class BeginsWith(AttrBase):
    operator = 'begins_with'

class Contains(AttrBase):
    operator = 'contains'

class In(AttrBase):
    operator = 'in'

class AttributeExists(FuncBase):
    operator = 'attribute_exists'

class AttributeNotExists(FuncBase):
    operator = 'attribute_not_exists'

class AttributeType(FuncBase):
    operator = 'attribute_type'

class And(GroupBase):
    operator = 'AND'

class Or(GroupBase):
    operator = 'OR'
