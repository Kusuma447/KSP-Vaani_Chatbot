from typing import List
from .._http_client import AuthorizedHttpClient
from .._constants import Components, RequestMethod, CredentialUser, CatalystService
from ._types import (
    DataverseEnrichLeadReq,
    DataverseLead,
    DataverseTechStack,
    DataverseSimilarCompanyReq,
)


class Dataverse:
    def __init__(self, smartbrowz_instance) -> None:
        self._requester: AuthorizedHttpClient = smartbrowz_instance._requester

    def get_component_name(self):
        return Components.SMART_BROWZ

    def get_enriched_lead(
        self, lead_critiria: DataverseEnrichLeadReq
    ) -> List[DataverseLead]:
        """
        Get comprehensive details about any organization using its name, \
              email address or website URL.
        """

        request_json = lead_critiria

        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/dataverse/lead-enrichment",
            json=request_json,
            user=CredentialUser.ADMIN,
            catalyst_service=CatalystService.BROWSER360,
        )
        data = resp.response_json.get("data")
        return data

    def find_tech_stack(self, website_url: str) -> List[DataverseTechStack]:
        """
        Get details about the technologies and frameworks used by an organization.
        """

        request_json = {"website_url": website_url}

        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/dataverse/tech-stack-finder",
            json=request_json,
            user=CredentialUser.ADMIN,
            catalyst_service=CatalystService.BROWSER360,
        )
        data = resp.response_json.get("data")
        return data

    def get_similar_companies(
        self, lead_critiria: DataverseSimilarCompanyReq
    ) -> List[str]:
        """
        Find out all the potential competitors of an organization.
        """

        req_json = lead_critiria

        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/dataverse/similar-companies",
            json=req_json,
            user=CredentialUser.ADMIN,
            catalyst_service=CatalystService.BROWSER360,
        )
        data = resp.response_json.get("data")
        return data
