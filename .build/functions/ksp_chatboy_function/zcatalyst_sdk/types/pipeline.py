from typing import  List, TypedDict, Dict
from ..types import ICatalystProject, ICatalystSysUser

class PipelineDetails(TypedDict):
    pipeline_id: str
    name: str
    description: str
    project_details: ICatalystProject
    created_time: str
    created_by: ICatalystSysUser
    modified_time: str
    modified_by: ICatalystSysUser
    git_account_id: str
    mask_regex: List[str]
    pipeline_status: str
    config_id: int
    integ_id: int
    repo_id: str
    branch: str
    git_service: str
    env_vars: Dict[str, str]
    extra_details: Dict[str, str]
    trigger_build: bool

class PipelineRun(TypedDict):
    history_id: str
    pipeline_id: str
    event_time: str
    event_details: Dict[str, str]
    history_status: str
