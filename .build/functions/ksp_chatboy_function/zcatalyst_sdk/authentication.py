import json
from typing import List, Literal, Optional, Union
from .types import (
    Component,
    ICatalystCustomTokenDetails,
    ICatalystCustomTokenResponse,
    ICatalystSignupConfig,
    ICatalystUserDetails,
    ICatalystUser,
    ICatalystSignupValidationReq
)
from .exceptions import CatalystAuthenticationError
from . import validator
from ._http_client import AuthorizedHttpClient
from ._constants import RequestMethod, CredentialUser, Components

UserStatus = Literal['enable', 'disable']


class ICatalystNewUser(ICatalystSignupConfig):
    user_details: ICatalystUser


class Authentication(Component):
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        return Components.AUTHENTICATION

    def get_current_user(self) -> ICatalystUser:
        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/project-user/current',
            user=CredentialUser.USER
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def get_all_users(self, org_id: str = None) -> List[ICatalystUser]:
        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/project-user',
            user=CredentialUser.ADMIN,
            params={
                'org_id': org_id
            } if org_id else None
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def get_user_details(self, user_id: Union[int, str]) -> ICatalystUser:
        validator.is_non_empty_string_or_number(user_id, 'user_id', CatalystAuthenticationError)
        resp = self._requester.request(
            method=RequestMethod.GET,
            path=f'/project-user/{user_id}',
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def delete_user(self, user_id: Union[int, str]) -> bool:
        validator.is_non_empty_string_or_number(user_id, 'user_id', CatalystAuthenticationError)
        resp = self._requester.request(
            method=RequestMethod.DELETE,
            path=f'/project-user/{user_id}',
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return bool(resp_json.get('data'))

    def register_user(
        self,
        signup_config: ICatalystSignupConfig,
        user_details: ICatalystUserDetails
    ) -> ICatalystNewUser:
        validator.is_deprecated_key_present(signup_config, 'zaid', None, False, True)
        validator.is_keys_present(
            signup_config, ['platform_type'], 'signup_config', CatalystAuthenticationError
        )
        validator.is_keys_present(
            user_details, ['first_name', 'email_id'], 'user_details', CatalystAuthenticationError
        )
        validator.is_deprecated_key_present(user_details, 'zaaid', 'org_id', True, True)
        signup_config['user_details'] = user_details
        resp = self._requester.request(
            method=RequestMethod.POST,
            path='/project-user',
            json=signup_config,
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def add_user_to_org(
        self,
        signup_config: ICatalystSignupConfig,
        user_details: ICatalystUserDetails
    ) -> ICatalystNewUser:
        validator.is_keys_present(
            signup_config, ['platform_type'], 'signup_config', CatalystAuthenticationError
        )
        validator.is_deprecated_key_present(signup_config, 'zaid', None, False, True)
        validator.is_deprecated_key_present(user_details, 'zaaid', 'org_id', True, True)
        validator.is_keys_present(
            user_details,
            ['first_name', 'email_id','org_id'],
            'user_details',
            CatalystAuthenticationError
        )
        signup_config['user_details'] = user_details
        resp = self._requester.request(
            method=RequestMethod.POST,
            path='/project-user',
            json=signup_config,
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def get_all_orgs(self):
        resp = self._requester.request(
            method=RequestMethod.GET,
            path='/project-user/orgs',
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def update_user_status(
        self,
        user_id: Union[str, int],
        status: UserStatus
    ):
        validator.is_non_empty_string_or_number(user_id, 'user_id', CatalystAuthenticationError)
        validator.is_non_empty_string(status, 'status', CatalystAuthenticationError)
        if status not in ['enable', 'disable']:
            raise CatalystAuthenticationError(
                'INVALID_USER_STATUS',
                "Status must be either 'enable' or 'disable'."
            )
        resp = self._requester.request(
            method=RequestMethod.POST,
            path=f'/project-user/{user_id}/{status}',
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def update_user_details(
        self,
        user_id: str,
        user_details: ICatalystUserDetails
    ):
        validator.is_non_empty_string(user_id, 'user_id', CatalystAuthenticationError)
        validator.is_keys_present(
            user_details, ['email_id'], 'user_details', CatalystAuthenticationError
        )
        resp = self._requester.request(
            method=RequestMethod.PUT,
            path=f'/project-user/{user_id}',
            json=user_details,
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    def reset_password(
        self,
        email: str,
        reset_config: ICatalystSignupConfig
    ) -> str:
        validator.is_keys_present(
            reset_config,
            ['platform_type'],
            'reset_config',
            CatalystAuthenticationError
        )
        validator.is_non_empty_string(
           email, 'email_id', CatalystAuthenticationError
        )
        reset_config['user_details'] = { 'email_id': email }
        resp = self._requester.request(
            method=RequestMethod.POST,
            path='/project-user/forgotpassword',
            json=reset_config,
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    @staticmethod
    def get_signup_validation_request(bio_req) -> Optional[ICatalystSignupValidationReq]:
        if bio_req.__class__.__name__ != 'BasicIO':
            raise CatalystAuthenticationError(
                'Invalid-Argument',
                'Please pass the valid basicio param'
            )
        if bio_req.get_argument('request_type') != 'add_user':
            return None

        request_details = bio_req.get_argument('request_details')
        if isinstance(request_details, dict):
            return request_details
        try:
            return json.loads(request_details)
        except TypeError as err:
            raise CatalystAuthenticationError(
                'Invalid request details',
                "Unable to parse 'request_details' from basicio args",
                request_details
            ) from err

    def generate_custom_token(
        self,
        custom_token_details: ICatalystCustomTokenDetails
    ) -> ICatalystCustomTokenResponse:
        validator.is_non_empty_dict(
            custom_token_details, 'custom_token_details', CatalystAuthenticationError
        )
        resp = self._requester.request(
            method=RequestMethod.POST,
            path='/authentication/custom-token',
            json=custom_token_details,
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')
