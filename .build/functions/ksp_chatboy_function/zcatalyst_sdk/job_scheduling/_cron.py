from typing import List
from .._http_client import AuthorizedHttpClient
from ._types import ICatalystCronDetails, CronExecutionType, ICatalystJobDetails
from .. import validator
from ._exception import CatalystJobSchedulingError

from .._constants import RequestMethod, CredentialUser, Components


class Cron:
    def __init__(self, job_scheduling_instance) -> None:
        self._requester: AuthorizedHttpClient = job_scheduling_instance._requester

    def get_component_name(self):
        return Components.JOB_SCHEDULING

    def get_all(self) -> List[ICatalystCronDetails]:
        """
        Get a list of all static crons

        Returns:
            List[ICatalystCronDetails]: List of static cron details
        """
        resp = self._requester.request(
            method=RequestMethod.GET,
            path="/job_scheduling/cron",
            user=CredentialUser.ADMIN,
        )
        resp_json = resp.response_json
        return resp_json.get("data")

    def get(self, cron_id: str) -> ICatalystCronDetails:
        """
        Get a static or dynamic cron's details

        Args:
            cron_id: Name or Id of the cron to be fetched

        Returns:
            ICatalystCronDetails: Details of the fetched cron

        Raises:
            Exception: If cron_id is invalid
        """
        validator.is_non_empty_string_or_number(
            cron_id, "cron_id", CatalystJobSchedulingError
        )
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f"/job_scheduling/cron/{cron_id}",
            user=CredentialUser.ADMIN,
        )
        resp_json = resp.response_json
        return resp_json.get("data")

    def create(self, cron_details: dict) -> ICatalystCronDetails:
        """
        Create a new dynamic cron

        Args:
            cron_details: Details of the cron to be created

        Returns:
            ICatalystCronDetails: Details of the created cron

        Raises:
            Exception: If cron_details is invalid
        """
        validator.is_non_empty_dict(
            cron_details, "cron_details", CatalystJobSchedulingError
        )
        cron_details["cron_execution_type"] = CronExecutionType.DYNAMIC.value
        job_meta = cron_details.get("job_meta")

        if job_meta is not None and isinstance(job_meta, dict):
            job_meta["source_type"] = "Cron"

        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/job_scheduling/cron",
            user=CredentialUser.ADMIN,
            json=cron_details,
        )
        resp_json = resp.response_json
        return resp_json.get("data")

    def update(self, cron_id: str, cron_details: dict) -> ICatalystCronDetails:
        """
        Update a static or dynamic cron

        Args:
            cron_id: Name or Id of the cron to be updated
            cron_details: Updated details of the cron

        Returns:
            ICatalystCronDetails: Details of the updated cron

        Raises:
            Exception: If cron_id is invalid
            Exception:: If cron_details is invalid
        """
        validator.is_non_empty_string_or_number(
            cron_id, "cron_id", CatalystJobSchedulingError
        )
        validator.is_non_empty_dict(
            cron_details, "cron_details", CatalystJobSchedulingError
        )
        resp = self._requester.request(
            method=RequestMethod.PUT,
            path=f"/job_scheduling/cron/{cron_id}",
            user=CredentialUser.ADMIN,
            json=cron_details,
        )
        resp_json = resp.response_json
        return resp_json.get("data")

    def pause(self, cron_id: str) -> ICatalystCronDetails:
        """
        Stop a cron from submitting jobs to the jobpool

        Args:
            cron_id: Name or Id of the cron to be paused

        Returns:
            ICatalystCronDetails: Details of the paused cron

        Raises:
            Exception: if cron_id is invalid
        """
        validator.is_non_empty_string_or_number(
            cron_id, "cron_id", CatalystJobSchedulingError
        )
        resp = self._requester.request(
            method=RequestMethod.PATCH,
            path=f"/job_scheduling/cron/{cron_id}",
            user=CredentialUser.ADMIN,
            json={"cron_status": False},
        )
        resp_json = resp.response_json
        return resp_json.get("data")

    def resume(self, cron_id: str) -> ICatalystCronDetails:
        """
        Resume a cron to submitting jobs to the jobpool

        Args:
            cron_id: Name or Id of the cron to be resumed

        Returns:
            ICatalystCronDetails: Details of the resumed cron

        Raises:
            Exception: if cron_id is invalid
        """
        validator.is_non_empty_string_or_number(
            cron_id, "cron_id", CatalystJobSchedulingError
        )
        resp = self._requester.request(
            method=RequestMethod.PATCH,
            path=f"/job_scheduling/cron/{cron_id}",
            user=CredentialUser.ADMIN,
            json={"cron_status": True},
        )
        resp_json = resp.response_json
        return resp_json.get("data")

    def run(self, cron_id: str) -> ICatalystJobDetails:
        """
        Run a cron and submit the cron's job immediately to the jobpool

        Args:
            cron_id: Name or Id of the cron which should be run

        Returns:
            ICatalystJobDetails: Details of the job submitted to the jobpool

        Raises:
            Exception: If cron_id is invalid

        """
        validator.is_non_empty_string_or_number(
            cron_id, "cron_id", CatalystJobSchedulingError
        )
        resp = self._requester.request(
            method=RequestMethod.POST,
            path=f"/job_scheduling/cron/{cron_id}/submit_job",
            user=CredentialUser.ADMIN,
        )
        resp_json = resp.response_json
        return resp_json.get("data")

    def delete(self, cron_id: str) -> ICatalystCronDetails:
        """
        Delete a cron

        Args:
            cron_id: Name or Id of the cron which should be deleted

        Returns:
            ICatalystCronDetails: Details of the deleted cron

        Raises:
            Exception: If cron_id is invalid

        """
        validator.is_non_empty_string_or_number(
            cron_id, "cron_id", CatalystJobSchedulingError
        )
        resp = self._requester.request(
            method=RequestMethod.DELETE,
            path=f"/job_scheduling/cron/{cron_id}",
            user=CredentialUser.ADMIN,
        )
        resp_json = resp.response_json
        return resp_json.get("data")
