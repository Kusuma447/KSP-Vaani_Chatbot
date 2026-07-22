from ..types.nosql import NoSqlItem, NoSqlItemRes
from .types import TypeDeserializer, TypeSerializer

class Item:
    """This class used to perform coversion between NoSQL and Python types.

    Returns:
        Item: Instance of the class.
    """
    @staticmethod
    def to_nosql(items):
        """Convert the given type to NoSQl typs.

        Args:
            items (dict): Items to converted in to NoSQL type.

        Returns:
            dict: Returns dict object in the form of NoSQL type.
        """
        res_items  = TypeSerializer().serialize(items)
        if isinstance(items, dict):
            return res_items.get('M')
        return res_items

    @staticmethod
    def to_python(items):
        return TypeDeserializer().deserialize(items)

class NoSqlItemResponse():
    """ NoSQL Table Response."""
    def __init__(self, res_data: NoSqlItem):
        self.status = res_data.get('status')
        self.item = res_data.get('item') and Item.to_python({ 'M': res_data.get('item')})
        self.old_item = res_data.get('old_item') and \
            Item.to_python({ 'M' :res_data.get('old_item')})

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if v is not None and v != self.status}

    def __repr__(self):
        return repr(self.to_dict())


class NoSqlResponse():
    """NoSQL response for all operations performed in the NoSQL table."""
    def __init__(self, res_data: NoSqlItemRes) -> None:
        self._res_data = res_data
        self.size = res_data.get('size')
        self.operation = res_data.get('operation')
        self.start_key = res_data.get('start_key')
        self.get = res_data.get('get') and \
            [NoSqlItemResponse(i).to_dict() for i in res_data.get('get')]
        self.update = res_data.get('update') and \
            [NoSqlItemResponse(i).to_dict() for i in res_data.get('update')]
        self.delete = res_data.get('delete') and \
            [NoSqlItemResponse(i).to_dict() for i in res_data.get('delete')]
        self.create = res_data.get('create') and \
            [NoSqlItemResponse(i).to_dict() for i in res_data.get('create')]

    def get_raw_response(self):
        """Return the raw response of the request.

        Returns:
            json: returns the json response.
        """
        return self._res_data

    def to_dict(self):
        resp_data = {
            k: v for k, v in self.__dict__.items() \
                if v is not None and v != self._res_data and v != self.operation
        }
        return resp_data

    def __repr__(self):
        return repr(self.to_dict())
