from typing import Dict, Union

from zcatalyst_sdk import validator
from zcatalyst_sdk.exceptions import CatalystQuickMLError
from .types import Component
from ._http_client import AuthorizedHttpClient
from ._constants import (
    RequestMethod,
    CredentialUser,
    Components,
    CatalystService
)

class QuickML(Component):
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        return Components.QUICK_ML

    def predict(
        self,
        end_point_key: str,
        input_data: Dict[str,Union[str, int]]
    ):
        req_json = { "data" : input_data  }
        validator.is_non_empty_string(end_point_key, 'end point key', CatalystQuickMLError)
        validator.is_non_empty_dict(input_data, 'input data', CatalystQuickMLError)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path='/endpoints/predict',
            json=req_json,
            user=CredentialUser.ADMIN,
            catalyst_service=CatalystService.QUICK_ML,
            headers={
                'X-QUICKML-ENDPOINT-KEY': end_point_key
            }
        )
        return resp.response_json
