# pylint: disable=invalid-name
from abc import ABC, abstractmethod
from io import BufferedReader
from typing import Any, List, Literal, Optional, TypedDict, Dict, Union


class Component(ABC):
    @abstractmethod
    def get_component_name(self) -> str:
        pass


class ParsableComponent(Component):
    @abstractmethod
    def to_string(self):
        pass

    @abstractmethod
    def to_dict(self):
        pass


class ICatalystOptions(TypedDict):
    project_id: Union[int, str]
    project_key: Union[int, str]
    project_domain: str
    environment: Optional[str]


class ICatalystConfig(ICatalystOptions):
    project_secret_key: Optional[str]


class ICatalystSysUser(TypedDict):
    userId: str
    email_id: str
    first_name: str
    last_name: str
    zuid: Optional[str]
    is_confirmed: Optional[bool]


class ICatalystProject(TypedDict):
    id: str
    project_name: str


class ICatalystGResponse(TypedDict):
    created_time: Optional[str]
    created_by: Optional[ICatalystSysUser]
    modified_time: Optional[str]
    modified_by: Optional[ICatalystSysUser]
    project_details: Optional[ICatalystProject]


class ICatalystSegment(TypedDict):
    id: str
    segment_name: str


class ICatalystCache(TypedDict):
    cache_name: str
    cache_value: str
    expires_in: str
    expiry_in_hours: str
    ttl_in_milliseconds: str
    segment_details: ICatalystSegment


class ICatalystFolder(TypedDict):
    id: str
    folder_name: Optional[str]


class ICatalystFile(TypedDict):
    id: str
    file_location: Optional[str]
    file_name: str
    file_size: int
    folder_details: ICatalystFolder


class ICatalystColumn(TypedDict):
    table_id: str
    column_sequence: str
    column_id: str
    column_name: str
    category: int
    data_type: int
    max_length: str
    is_mandatory: bool
    default_value: Optional[Any]
    decimal_digits: Optional[str]
    is_unique: bool
    search_index_enabled: bool


class ICatalystRow(TypedDict):
    CREATORID: str
    CREATEDTIME: str
    MODIFIEDTIME: str
    ROWID: str


class ICatalystRows(TypedDict):
    status: str
    data: List[ICatalystRow]
    more_records: Optional[bool]
    next_token: Optional[str]


class ICatalystTable(TypedDict):
    table_id: Optional[str]
    table_name: Optional[str]
    table_scope: Optional[str]
    project_id: Optional[ICatalystProject]
    modified_time: Optional[str]
    modified_by: Optional[ICatalystSysUser]


class ICatalystMail(TypedDict, total=False):
    from_email: str
    to_email: List[str]
    subject: str
    content: Optional[str]
    cc: Optional[List[str]]  # pylint: disable=invalid-name
    bcc: Optional[List[str]]
    reply_to: Optional[List[str]]
    html_mode: Optional[bool]
    display_name: Optional[str]
    attachments: Optional[List[BufferedReader]]


class ICatalystUserRoleDetails(TypedDict):
    role_id: str
    role_name: str


MailTemplateDetails = TypedDict(
    "MailTemplateDetails",
    {"senders_mail": Optional[str], "subject": Optional[str], "message": Optional[str]},
    total=False,
)


class ICatalystSignupConfig(TypedDict, total=False):
    platform_type: str
    redirect_url: Optional[str]
    template_details: Optional[MailTemplateDetails]


class ICatalystUser(TypedDict):
    zuid: str
    zaaid: str
    status: str
    user_id: str
    is_confirmed: bool
    email_id: str
    first_name: str
    last_name: str
    created_time: str
    modified_time: str
    invited_time: str
    role_details: ICatalystUserRoleDetails


class ICatalystUserDetails(TypedDict, total=False):
    first_name: str
    last_name: Optional[str]
    email_id: str
    org_id: str


class ICatalystUserParticulars(TypedDict):
    email_id: str
    first_name: str
    last_name: str
    org_id: Optional[str]


class ICatalystCronUrl(TypedDict):
    url: str
    headers: Optional[Dict[str, str]]
    params: Optional[Dict[str, str]]
    request_method: str
    request_body: Optional[str]


class ICatalystCronJob(TypedDict):
    time_of_execution: Union[str, int, None]
    repetition_type: Optional[str]
    hour: Optional[int]
    minute: Optional[int]
    second: Optional[int]
    days: Optional[List[int]]
    weeks_of_month: Optional[List[int]]
    week_day: Optional[List[int]]
    months: Optional[List[int]]
    timezone: Optional[str]


class ICatalystCron(TypedDict, total=False):
    cron_name: str
    description: Optional[str]
    cron_type: str
    status: bool
    cron_url_details: ICatalystCronUrl
    job_detail: ICatalystCronJob


class ICatalystPushDetails(TypedDict, total=False):
    message: str
    additional_info: Optional[Dict[str, Any]]
    badge_count: Optional[int]
    reference_id: Optional[str]
    expiry_time: Optional[int]


class ICatalystMobileNotification(TypedDict):
    recipients: List[str]
    push_details: ICatalystPushDetails


class ICatalystSearchQuery(TypedDict, total=False):
    search: str
    search_table_columns: Dict[str, List[str]]
    select_table_columns: Optional[Dict[str, List[str]]]
    order_by: Optional[Dict[str, Any]]
    start: Optional[int]
    end: Optional[int]


class ICatalystSignupUserDetails(ICatalystUserParticulars):
    role_details: Optional[ICatalystUserRoleDetails]


class ICatalystSignupValidationReq(TypedDict):
    user_details: ICatalystSignupUserDetails
    auth_type: Literal["web", "mobile"]


class ICatalystSignupUserResponse(TypedDict):
    """
    User details to add in Catalyst after successful signup validation

    Attributes:
    ----------
        first_name: Optional[str]
            first name of the user

        last_name: Optional[str]
            last name of the user

        org_id: Optional[Union[int, str]]
            client portal org to which the user should be added to

        role_identifier: Optional[Union[int, str]]
            to determine the role of the user
    """

    first_name: Optional[str]
    last_name: Optional[str]
    org_id: Optional[Union[int, str]]
    role_identified: Optional[Union[int, str]]


class ICatalystSignupErrorResponse(TypedDict):
    """
    Error Response for SignUp validation

    Attributes:
    -----------
        status_code: int
            status code of the response

        body: Any
            response to be sent
    """

    status_code: int
    body: Any


class ICatalystSignupValidationResponse(TypedDict):
    """
    Validation response to be sent to User SignUp validation request in BasicIO

    Attributes:
    -----------
        status: Literal['success' | 'failure']
            denotes the status of the validation request as success or failure

        user_details: Optional[ICatalystSignupUserResponse]
            details of the user to be added in Catalyst on successful validation

        error_response: Optional[ICatalystSignupErrorResponse]
            details of the error response to be sent incase of validation failure
    """

    status: Literal["success", "failure"]
    user_details: Optional[ICatalystSignupUserResponse]
    error_response: Optional[ICatalystSignupErrorResponse]


CustomTokenUserDetails = TypedDict(
    "CustomTokenUserDetails",
    {
        "role_name": Optional[str],
        "phone_number": Optional[str],
        "country_code": Optional[str],
    },
    total=False,
)


class ICatalystCustomTokenDetails(TypedDict):
    type: Literal["web", "mobile"]
    user_details: CustomTokenUserDetails


class ICatalystCustomTokenResponse(TypedDict):
    jwt_token: str
    client_id: str
    scopes: List[str]


Group = TypedDict("Group", {"column_name": str, "comparator": str, "value": str})

BulkReadCriteria = TypedDict(
    "BulkReadCriteria", {"group_operator": str, "group": List[Group]}
)


class ICatalystBulkReadQuery(TypedDict, total=False):
    page: Optional[int]
    select_columns: Optional[List[str]]
    criteria: Optional[BulkReadCriteria]


FkMapping = TypedDict("FkMapping", {"local_column": str, "reference_column": str})


class ICatalystBulkWriteInput(TypedDict, total=False):
    operation: Optional[Literal["insert", "update", "upsert"]]
    find_by: Optional[str]
    fk_mapping: Optional[List[FkMapping]]


class ICatalystBulkCallback(TypedDict, total=False):
    url: str
    headers: Optional[Dict[str, str]]
    params: Optional[Dict[str, str]]


QueryResultDetails = TypedDict(
    "QueryResultDetails", {"page": Optional[int], "file_id": Optional[str]}
)

BulkJobQueryResult = TypedDict(
    "BulkJobQueryResult", {"table_id": str, "details": QueryResultDetails}
)

BulkJobResultDetails = TypedDict(
    "BulkJobResultDetails",
    {"table_id": str, "records_processed": int, "more_records": Optional[bool]},
)

BulkJobResults = TypedDict(
    "BulkJobResults",
    {
        "download_url": Optional[str],
        "description": str,
        "details": Optional[BulkJobResultDetails],
    },
)


class ICatalystBulkJob(TypedDict):
    job_id: str
    status: Literal["In-Progress", "Completed", "Failed"]
    operation: str
    project_details: ICatalystProject
    created_by: ICatalystSysUser
    created_time: str
    query: Optional[List[BulkJobQueryResult]]
    callback: Optional[ICatalystBulkCallback]
    results: Optional[BulkJobResults]


class CatalystBucketObject(TypedDict):
    bucket_name: str
    object_key: str
    version_id: str

class ICatalystConnectionDetails(TypedDict):
    headers: Dict[str, str]
    parameters: Dict[str, str]

class ICatalystConnectionsResponse(TypedDict):
    connections: ICatalystConnectionDetails
