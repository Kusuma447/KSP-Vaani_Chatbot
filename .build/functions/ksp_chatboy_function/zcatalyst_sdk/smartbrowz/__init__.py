from typing import Union, List
import warnings
from ..types import Component
from ..exceptions import CatalystSmartBrowzError
from .._http_client import AuthorizedHttpClient
from .. import validator
from .._constants import RequestMethod, CredentialUser, Components, CatalystService
from ._types import (
    OutputOptions,
    PdfOptions,
    PdfPageOptions,
    ScreenShotOptions,
    ScreenShotPageOptions,
    NavigationOptions,
    DataverseEnrichLeadReq,
    DataverseLead,
    DataverseTechStack,
    DataverseSimilarCompanyReq,
)
from ._dataverse import Dataverse
from ._browser_grid import BrowserGrid


class SmartBrowz(Component):
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)
        self._dataverse = Dataverse(self)
        self._browser_grid = BrowserGrid(self)

    def dataverse(self) -> Dataverse:
        """
        Get an object instance to access SmartBrowz Dataverse functionalities
        """
        return self._dataverse

    def browser_grid(self) -> BrowserGrid:
        """
        Get an object instance to access Browser Grid functionalities
        """
        return self._browser_grid

    def get_component_name(self):
        return Components.SMART_BROWZ

    def convert_to_pdf(
        self,
        source: str,
        pdf_options: PdfOptions = None,
        page_options: PdfPageOptions = None,
        navigation_options: NavigationOptions = None,
        **kwargs
    ):
        """
        convert the given source into pdf
        """

        req_json = {"output_options": {"output_type": "pdf"}}
        validator.is_non_empty_string(source, "source", CatalystSmartBrowzError)
        if validator.is_valid_url(source):
            req_json["url"] = source
        else:
            req_json["html"] = source

        req_json.update(
            {
                "pdf_options": pdf_options,
                "page_options": page_options,
                "navigation_options": navigation_options,
            }
        )
        req_json.update(kwargs)

        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/convert",
            json=req_json,
            user=CredentialUser.ADMIN,
            catalyst_service=CatalystService.BROWSER360,
        )
        return resp.response

    def take_screenshot(
        self,
        source: str,
        screenshot_options: ScreenShotOptions = None,
        page_options: ScreenShotPageOptions = None,
        navigation_options: NavigationOptions = None,
        **kwargs
    ):
        """
        Take screenshot of the given source
        """

        req_json = {"output_options": {"output_type": "screenshot"}}
        validator.is_non_empty_string(source, "source", CatalystSmartBrowzError)
        if validator.is_valid_url(source):
            req_json["url"] = source
        else:
            req_json["html"] = source

        req_json.update(
            {
                "screenshot_options": screenshot_options,
                "page_options": page_options,
                "navigation_options": navigation_options,
            }
        )
        req_json.update(kwargs)

        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/convert",
            json=req_json,
            user=CredentialUser.ADMIN,
            catalyst_service=CatalystService.BROWSER360,
        )
        return resp.response

    def generate_from_template(
        self,
        template_id: Union[str, int],
        template_data: dict = None,
        output_options: OutputOptions = None,
        pdf_options: PdfOptions = None,
        screenshot_options: ScreenShotOptions = None,
        page_options: Union[PdfPageOptions, ScreenShotPageOptions] = None,
        navigation_options: NavigationOptions = None,
        **kwargs
    ):
        """
        Generate outputs using existing templates with dynamic template datas
        """

        validator.is_non_empty_string_or_number(
            template_id, "template_id", CatalystSmartBrowzError
        )

        req_json = {
            "template_id": template_id,
            "template_data": template_data,
            "output_options": output_options,
            "pdf_options": pdf_options,
            "screenshot_options": screenshot_options,
            "page_options": page_options,
            "navigation_options": navigation_options,
        }
        req_json.update(kwargs)

        resp = self._requester.request(
            method=RequestMethod.POST,
            path="/convert",
            json=req_json,
            user=CredentialUser.ADMIN,
            catalyst_service=CatalystService.BROWSER360,
        )
        return resp.response

    def get_enriched_lead(
        self, lead_critiria: DataverseEnrichLeadReq
    ) -> List[DataverseLead]:
        """
        Get comprehensive details about any organization using its name, \
        email address or website URL.

        This method is deprecate and maybe removed in future versions.
        """

        warnings.warn(
            "The 'get_enriched_lead' method is deprecated and will be removed in a future version."
            " Use 'dataverse().get_enriched_lead' method instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        return self._dataverse.get_enriched_lead(lead_critiria=lead_critiria)

    def find_tech_stack(self, website_url: str) -> List[DataverseTechStack]:
        """
        Get details about the technologies and frameworks used by an organization.

        This method is deprecate and maybe removed in future versions.
        """

        warnings.warn(
            "The 'find_tech_stack' method is deprecated and will be removed in a future version."
            " Use 'dataverse().find_tech_stack' method instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        return self._dataverse.find_tech_stack(website_url=website_url)

    def get_similar_companies(
        self, lead_critiria: DataverseSimilarCompanyReq
    ) -> List[str]:
        """
        Find out all the potential competitors of an organization.

        This method is deprecate and maybe removed in future versions.
        """

        warnings.warn(
            "The 'get_similar_companies' method is"
            " deprecated and will be removed in a future version."
            " Use 'dataverse().get_similar_companies' method instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        return self._dataverse.get_similar_companies(lead_critiria=lead_critiria)
