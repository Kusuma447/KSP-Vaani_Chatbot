from typing import List, Literal, Optional, TypedDict, Dict, Union
from enum import Enum

NoSqlAttributeType = Literal['keys_only', 'all', 'include']

NoSqlGroupOperator = Literal['AND', 'OR']

NoSqlUpdateOperation = Literal['PUT', 'DELETE']

NoSqlOperator = Literal[
     'contains', 'begins_with', 'not_contains', 'ends_with', 'in', 'not_in',
       'between', 'not_between', 'equals', 'not_equals', 'greater_than',
       'less_than', 'greater_equal','less_equal'
]

ItemType = Literal[
    'S', 'N', 'B', 'L', 'M', 'SS', 'SB', 'SN', 'BOOL'
]

NoSqlSecondaryKeyCondition = Literal[
      'begins_with', 'between', 'equals', 'greater_than',
       'less_than', 'greater_equal','less_equal'
]

ReturnType = Literal['NEW', 'OLD', 'NULL']

class NoSqlCrudOperation(Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class CatalystSysUser(TypedDict):
    user_id: str
    user_type: str
    email_id: str
    first_name: str
    last_name: str
    zuid: Optional[str]
    is_confirmed: Optional[bool]


class CatalystProjectInfo(TypedDict):
    id: str
    project_name: str
    project_type: str


class CatalystNoSqlKeyInfo(TypedDict):
    column_name: str
    data_type: str


class NoSqlTableResponse(TypedDict):
    id: str
    api_access: bool
    created_by: CatalystSysUser
    created_time: str
    modified_by: CatalystSysUser
    modified_time: str
    name: str
    partition_key: CatalystNoSqlKeyInfo
    project_id: CatalystProjectInfo
    sort_by: CatalystNoSqlKeyInfo
    status: str
    ttl_attribute: str
    ttl_enabled: bool
    type: str

ProjectedAttribute = TypedDict('ProjectedAttribute', {
    'type': str,
})


class NoSqlIndexRes(TypedDict):
    created_by: CatalystSysUser
    created_time: str
    id: str
    modified_by: CatalystSysUser
    modified_time: str
    name: str
    partition_key:CatalystNoSqlKeyInfo
    project_id: CatalystProjectInfo
    projected_attributes: ProjectedAttribute
    sort_key: CatalystNoSqlKeyInfo
    status: str
    type: str


class NoSqlTableResourceRes(TypedDict):
    additional_sort_keys: List[NoSqlIndexRes]
    api_access: bool
    created_by: CatalystSysUser
    created_time: str
    global_index: List[NoSqlIndexRes]
    id: str
    modified_by: CatalystSysUser
    modified_time: str
    name: str
    partition_key: CatalystNoSqlKeyInfo
    project_id:CatalystProjectInfo
    sort_key:CatalystNoSqlKeyInfo
    status:str
    ttl_enabled:bool
    type:str


AttributePath = TypedDict('AttributePath', {
        'attribute_path': List[str]
})

class UpdateCondion(TypedDict):
    function_name: Literal['if_not_exists', 'add', 'subtract', 'append_list']
    args: AttributePath


class NoSqlItemUpdateAttributeOperation(TypedDict, total= False):
    operation_type: NoSqlUpdateOperation
    update_value: Dict[str, str]
    update_function: UpdateCondion
    attribute_path: List[str]


class NoSqlFunctionCondition(TypedDict):
    function_name: Literal['attribute_exits', 'attribute_type']
    args: AttributePath


class NoSqlConditionFuncOperation():
    function: Optional[NoSqlFunctionCondition]


class NoSqlAttributeCondition(TypedDict):
    attribute: Optional[NoSqlAttributeType]
    operator: Optional[NoSqlOperator]
    value: Dict[str, str]


class NoSqlGroupCondition(TypedDict):
    group_operator: Optional[str]
    group: Optional['NoSqlCondition']
    negate: bool


NoSqlCondition = Union[NoSqlAttributeCondition, NoSqlGroupCondition, NoSqlConditionFuncOperation]

class NoSqlItem(TypedDict, total = False):
    status: str
    old_item: str
    item: str


class NoSqlItemRes(TypedDict, total = False):
    size: str
    start_key: str
    operation: Literal['create', 'read', 'update', 'delete']
    update: List[NoSqlItem]
    create: List[NoSqlItem]
    delete: List[NoSqlItem]
    get: List[NoSqlItem]


NoSqlInsertItemReq = TypedDict('NoSqlInsertItemReq', {
    'item': Dict[str, str],
    'condition': Optional[NoSqlCondition],
    'return': ReturnType
}, total = False)

class NoSqlFetchItemReq(TypedDict):
    keys: List[Dict[str, str]]
    required_attributes: List[str]


class NoSqlDeleteItemReq(TypedDict):
    keys: Dict[str, str]
    condition: Optional[NoSqlCondition]


class NoSqlUpdateItemReq(TypedDict):
    keys: Dict[str, str]
    condition: Optional[NoSqlCondition]
    update_attributes: List[NoSqlItemUpdateAttributeOperation]


class NoSqlQueryItemReq(TypedDict):
    consistent_read: bool
    key_condition: NoSqlCondition
    other_condition: Optional[NoSqlCondition]
    limit: int
    forward_scan: bool
    start_key: Dict[str, str]
    additional_sort_keys: str
    required_attributes: List[str]
