from typing import Dict
from .._http_client import AuthorizedHttpClient
from .. import validator
from ._types import ICatalystJobDetails
from .._constants import RequestMethod, CredentialUser

from ._exception import CatalystJobSchedulingError


class Job:
    def __init__(self, job_scheduling_instance):
        self._requester: AuthorizedHttpClient = job_scheduling_instance._requester

    def get_job(self, job_id: str) -> ICatalystJobDetails:
        """
        Get a job's details

        Args:
            job_id: Id of the job to be fetched

        Returns:
            ICatalystJobDetails: Details of job fetched with the job_id

        Raises:
            Exception: If the given job_id is invalid.

        """
        validator.is_non_empty_string_or_number(
            job_id, "job_id", CatalystJobSchedulingError
        )
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f"/job_scheduling/job/{job_id}",
            user=CredentialUser.ADMIN,
        )
        resp_json = resp.response_json
        return resp_json.get("data")

    def submit_job(self, job_meta: Dict) -> ICatalystJobDetails:
        """
        Submit a job to the jobpool

        Args:
            job_meta: Meta details of the job

        Returns:
            ICatalystJobDetails: Details of the submitted job

        Raises:
            Exception: if the job_meta object is invalid
        """
        validator.is_non_empty_dict(job_meta, "job_meta", CatalystJobSchedulingError)

        job_meta["source_type"] = "API"
        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/job_scheduling/job",
            user=CredentialUser.ADMIN,
            json=job_meta,
        )
        resp_json = resp.response_json
        return resp_json.get("data")

    def delete_job(self, job_id: str) -> ICatalystJobDetails:
        """
        Delete a job from jobpool

        Args:
            job_id: Id of the job to be deleted

        Returns:
            ICatalystJobDetails: Details of the deleted job

        Raises:
            Exception: if the job_id is invalid
        """
        validator.is_non_empty_string_or_number(
            job_id, "job_id", CatalystJobSchedulingError
        )
        resp = self._requester.request(
            method=RequestMethod.DELETE,
            path=f"/job_scheduling/job/{job_id}",
            user=CredentialUser.ADMIN,
        )
        resp_json = resp.response_json
        return resp_json.get("data")
