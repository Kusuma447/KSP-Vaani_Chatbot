"""Typing for Job Scheduling"""

from enum import Enum
from typing import List, Dict, Any, Union, Optional, Literal, TypedDict
from typing_extensions import TypeAlias
from ..types import ICatalystGResponse


class CapacityAttribute(Enum):
    MEMORY = "memory"
    NUMBER = "number"


class CronExecutionType(Enum):
    PRE_DEFINED = "pre-defined"
    DYNAMIC = "dynamic"


class CronType(Enum):
    CALENDER = "Calender"
    PERIODIC = "Periodic"
    ONETIME = "OneTime"
    CRON_EXPRESSION = "CronExpression"


class TargetType(Enum):
    FUNCTION = "Function"
    CIRCUIT = "Circuit"
    APPSAIL = "AppSail"
    WEBHOOK = "Webhook"


class JobStatus(Enum):
    SUBMITTED = "Submitted"
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCESSFUL = "Successful"
    FAILURE = "Failure"


class RepetitionType(Enum):
    EVERY = "every"
    DAILY = "daily"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ICatalystCapacityAttributes(TypedDict):
    memory: int
    number: int


class ICatalystJobTargetDetails(TypedDict):
    id: str
    target_name: str
    details: Dict[str, Any]


class ICatalystJobpoolDetails(TypedDict):
    id: str
    type: TargetType
    name: str
    capacity: ICatalystCapacityAttributes


class ICatalystJobMetaConfig(TypedDict):
    number_of_retires: int
    retry_interval: int


class ICatalystJobBasic(TypedDict):
    job_name: str
    job_config: Optional[ICatalystJobMetaConfig]
    jobpool_id: str
    jobpool_name: str


class ICatalystFunctionJob(ICatalystJobBasic):
    target_type: Literal[TargetType.FUNCTION]
    target_id: str
    params: Dict[str, str]


class ICatalystWebhookJob(ICatalystJobBasic):
    target_type: Literal[TargetType.WEBHOOK]
    target_id: str
    url: str
    params: Optional[Dict[str, str]]
    headers: Optional[Dict[str, str]]
    request_method: str
    request_body: Optional[str]


class ICatalystAppSailJob(ICatalystJobBasic):
    target_type: Literal[TargetType.APPSAIL]
    target_id: str
    url: Optional[str]
    params: Optional[Dict[str, str]]
    headers: Optional[Dict[str, str]]
    request_method: str
    request_body: Optional[str]


class ICatalystCircuitJob(ICatalystJobBasic):
    target_type: Literal[TargetType.CIRCUIT]
    target_id: str
    test_cases: Dict[str, Any]


TCatalystJobs: TypeAlias = Union[
    ICatalystFunctionJob, ICatalystWebhookJob, ICatalystAppSailJob, ICatalystCircuitJob
]


class ICatalystJobMetaDetails(ICatalystJobBasic):  # for response
    id: str
    target_details: ICatalystJobTargetDetails
    source_type: str
    source_id: str
    source_details: str
    jobpool_details: ICatalystJobpoolDetails
    target_type: TargetType
    target_id: str
    url: Optional[str]
    params: Optional[Dict[str, str]]
    headers: Optional[Dict[str, str]]
    request_method: Optional[str]
    request_body: Optional[str]


class ICatalystJobDetails(ICatalystGResponse):
    job_id: str
    status: bool
    job_status: JobStatus
    capacity: ICatalystCapacityAttributes
    job_meta_details: ICatalystJobMetaDetails
    response_code: Optional[str]
    start_time: str
    end_time: str
    execution_time: str
    parent_job_id: Optional[str]
    retried_count: Optional[int]


class ICatalystCronBasic(TypedDict):
    cron_execution_type: CronExecutionType
    cron_name: str
    cron_status: bool
    job_meta: TCatalystJobs


one_time_cron_detail = TypedDict(
    "one_time_cron_detail", {"time_of_execution": str, "timezone": Optional[str]}
)


class ICatalystOneTimeCron(ICatalystCronBasic):
    cron_type: Literal["OneTime"]
    cron_detail: one_time_cron_detail


every_cron_detail = TypedDict(
    "every_cron_detail",
    {
        "hour": int,
        "minute": int,
        "second": int,
        "timezone": Optional[str],
        "repetition_type": Literal["every"],
    },
)


class ICatalystEveryCron(ICatalystCronBasic):
    cron_type: Literal["Periodic"]
    cron_detail: every_cron_detail
    end_time: Optional[str]


daily_cron_detail = TypedDict(
    "daily_cron_detail",
    {
        "hour": int,
        "minute": int,
        "second": int,
        "timezone": Optional[str],
        "repetition_type": Literal["daily"],
    },
)


class ICatalystDailyCron(ICatalystCronBasic):
    cron_type: Literal["Calendar"]
    cron_detail: daily_cron_detail
    end_time: Optional[str]


monthly_cron_detail = TypedDict(
    "monthly_cron_detail",
    {
        "repetition_type": Literal["monthly"],
        "days": Optional[List[int]],
        "weeks_of_month": Optional[List[int]],
        "week_day": Optional[List[int]],
        "hour": int,
        "minute": int,
        "second": int,
        "timezone": Optional[str],
    },
)


class ICatalystMonthlyCron(ICatalystCronBasic):
    cron_type: Literal["Calendar"]
    cron_detail: monthly_cron_detail
    end_time: Optional[str]


yearly_cron_detail = TypedDict(
    "yearly_cron_detail",
    {
        "repetition_type": Literal["yearly"],
        "months": List[int],
        "days": Optional[List[int]],
        "weeks_of_month": Optional[List[int]],
        "week_day": Optional[List[int]],
        "hour": int,
        "minute": int,
        "second": int,
        "timezone": Optional[str],
    },
)


class ICatalystYearlyCron(ICatalystCronBasic):
    cron_type: Literal["Calendar"]
    cron_detail: yearly_cron_detail
    end_time: Optional[str]


expression_cron_detail = TypedDict(
    "expression_cron_detail", {"timezone": Optional[str]}
)


class ICatalystCronExpression(ICatalystCronBasic):
    cron_type: Literal["CronExpression"]
    cron_expression: str
    cron_detail: expression_cron_detail
    end_time: Optional[str]

TCatalystCron: TypeAlias = Union[
    ICatalystOneTimeCron,
    ICatalystEveryCron,
    ICatalystDailyCron,
    ICatalystMonthlyCron,
    ICatalystYearlyCron,
    ICatalystCronExpression,
]


class ICatalystCronDetails(ICatalystGResponse):
    id: str
    cron_name: str
    description: Optional[str]
    cron_type: CronType
    cron_function_id: Optional[str]
    cron_execution_type: CronExecutionType
    cron_status: bool
    start_time: str
    end_time: str
    cron_expression: Optional[str]
    cron_detail: TCatalystCron
    job_meta: ICatalystJobMetaDetails
    success_count: int
    failure_count: int
