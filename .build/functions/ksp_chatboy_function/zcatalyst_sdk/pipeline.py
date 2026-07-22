from typing import Optional
from .types import Component
from ._http_client import AuthorizedHttpClient
from ._constants import ( Components, RequestMethod, CredentialUser )
from . import validator
from .exceptions import CatalystPipelineError
from .types.pipeline import PipelineDetails, PipelineRun

class Pipeline(Component):
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        return Components.PIPELINE

    def get_pipeline_details(self, pipeline_id: str) -> PipelineDetails:
        """Get the details of the pipelines.

        Args:
            pipeline_id (str): Id to get the details of the pipeline.

        Returns:
            PipelineDetails: Returns the pipeline details.
        """
        validator.is_non_empty_string_or_number(pipeline_id, 'pipeline_id', CatalystPipelineError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/pipeline/{pipeline_id}',
            user=CredentialUser.ADMIN
        )
        return resp.response_json.get('data')

    def run_pipeline(
        self,
        pipeline_id: str,
        branch: Optional[str] = None,
        env_vars: Optional[dict] = None
        ) -> PipelineRun:
        """Run the Pipeline.

        Args:
            pipeline_id (str): Id of the pipeline.
            branch (Optional[str], optional): Name of the branch. Defaults to None.
            env_vars (Optional[dict], optional): Environment variables updated
                to pipelines. Defaults to None.

        Returns:
            PipelineRun: Returns the status of the pipline.
        """
        validator.is_non_empty_string_or_number(pipeline_id, 'pipeline_id', CatalystPipelineError)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path=f'/pipeline/{pipeline_id}/run' + (f'?branch={branch}' if branch else ''),
            json = env_vars or {},
            user=CredentialUser.ADMIN
        )
        return resp.response_json.get('data')
