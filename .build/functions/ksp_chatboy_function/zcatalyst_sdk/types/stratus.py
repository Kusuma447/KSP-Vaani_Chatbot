from typing import List, Dict, Literal, Optional, TypedDict, Union
from . import (
    ICatalystGResponse
)

Cache = TypedDict('caching', {
    'status': Union[str, bool]
})

StratusUploadOptions = TypedDict('StratusUploadOptions', {
    'overwrite': Union[str, bool],
    'ttl': str,
    'compress': str,
    'meta_data': Dict[str, str],
    'content_type': str,
    'extract_upload': Literal['true', 'false']
}, total= False)

StratusDownloadOptions = TypedDict('StratusDownloadOptions', {
    'version_id': str,
    'range': str
}, total= False)


class BucketMeta(TypedDict):
    versioning: bool
    caching: Cache
    encryption: bool
    audit_consent: bool


class StratusObjectDetails(TypedDict):
    key_type: str
    key: str
    size: int
    version_id: str
    etag: str
    content_type: str
    last_modified: str
    object_url: Optional[str]


class StratusObjectsRes(TypedDict):
    key_count: int
    max_keys: Optional[int]
    truncated: str
    next_continuation_token: Optional[str]
    contents: List[StratusObjectDetails]


class DeleteObjectOptions(TypedDict):
    key: str
    version_id: str


class StratusBucket(ICatalystGResponse):
    bucket_name: str
    bucket_url: str
    objects_count: str
    size_in_bytes: str
    bucket_meta: BucketMeta


class StratusObjectVersion(TypedDict, total = False):
    version_id: str
    is_latest: Optional[bool]
    last_modified: str
    size: str
    etag: str


class ObjectVersionsRes(TypedDict):
    key: str
    versions_count: str
    next_continuation_token: str
    max_versions: str
    is_truncated: Optional[bool]
    version: List[StratusObjectVersion]


class BucketCorsResponse(TypedDict):
    domain: str
    allowed_methods: List[str]


class CopyObjectResponse(TypedDict):
    key: str
    copy_to: str
    message: str


class RenameObjectResponse(TypedDict):
    current_key: str
    rename_to: str
    message: str


class UnzipObjectResponse(TypedDict):
    key: str
    destination: str
    message: str
    task_id: str


class DeleteObjectPathResponse(TypedDict):
    prefix: str
    message: str


class InitiateMultipartUploadResponse(TypedDict):
    bucket: str
    key: str
    upload_id: int
    status: str


class UploadedObjectPartRes(TypedDict):
    part_number: str
    size: str
    upload_at: str


class MultipartUploadSummaryRes(TypedDict):
    bucket: str
    key: str
    upload_id: str
    parts: List[UploadedObjectPartRes]


class StratusSignature(TypedDict):
    stsPolicy: str
    stsSignature: str

class StratusPutObjectRes(TypedDict):
    task_id: str

class PutObjectAsPartsOptions(TypedDict, total=False):
    overwrite: Optional[Union[str, bool]]

class StratusInitiateUploadOptions(TypedDict, total=False):
    overwrite: Union[str, bool]
    compress: str
