from abc import ABC, abstractmethod
import json
import os
from time import time
from typing import Dict, List, Literal, TypedDict, Union
from ._thread_util import ZCThreadUtil
from . import _constants as APIConstants
from ._constants import (
    PROJECT_DOMAIN,
    PROJECT_ID,
    PROJECT_KEY,
    CredentialUser,
    RequestMethod,
    CredentialType
)
from .exceptions import (
    CatalystCredentialError,
    CatalystAppError
)

_CATALYST_AUTH_ENV_KEY = 'CATALYST_AUTH'

_JWT_TOKEN_KEYS = [
    APIConstants.CLIENT_ID,
    APIConstants.JWT_TOKEN,
    APIConstants.SCOPES
]

_REFRESH_OBJ_KEYS = [
    APIConstants.CLIENT_ID,
    APIConstants.CLIENT_SECRET,
    APIConstants.REFRESH_TOKEN
]

_CATALYST_SCOPES = ['admin', 'user']

_PORTAL_ID=os.getenv('CATALYST_PORTAL_DOMAIN')

ICatalystJwtObj = TypedDict('ICatalystJwtObj', {
    'client_id': str,
    'scopes': List[str],
    'jwt_token': str
})

ICatalystRefreshObj = TypedDict('ICatalystRefreshObj', {
    'client_id': str,
    'client_secret': str,
    'refresh_token': str
})

ICatalystTokenObj = TypedDict('ICatalystTokenObj', {
    'access_token': str
})

ICatalystTicketObj = TypedDict('ICatalystTicketObj', {
    'ticket': str
})


# Credential class for all credentials
class Credential(ABC):
    @abstractmethod
    def token(self):
        pass

    def _switch_user(self, user=None):  # pylint: disable=unused-argument
        return None

    def current_user(self):
        return CredentialUser.ADMIN

    def current_user_type(self):
        return CredentialUser.ADMIN


class RefreshTokenCredential(Credential):
    def __init__(self, refresh_obj: ICatalystRefreshObj):
        super().__init__()
        RefreshTokenCredential._validate_refresh_obj(refresh_obj)
        self._client_id = refresh_obj.get(APIConstants.CLIENT_ID)
        self._client_secret = refresh_obj.get(APIConstants.CLIENT_SECRET)
        self._refresh_token = refresh_obj.get(APIConstants.REFRESH_TOKEN)
        self._cached_token: Dict[str, Union[str, int]] = None

    def token(self) -> str:
        if not self._cached_token or self._cached_token.get('expires_in') <= int(round(time())):
            from ._http_client import HttpClient  # pylint: disable=cyclic-import,import-outside-toplevel
            requester = HttpClient(base_url=APIConstants.ACCOUNTS_URL)

            post_data = {
                'grant_type': 'refresh_token',
                'refresh_token': self._refresh_token,
                'client_id': self._client_id,
                'client_secret': self._client_secret
            }

            resp = requester.request(
                method=RequestMethod.POST,
                path='/oauth/v2/token',
                data=post_data
            )
            data: Dict = resp.response_json
            try:
                if data.get('access_token') and data.get('expires_in'):
                    data.update({'expires_in': int(round(time())) + data.get('expires_in') * 1000})
                    self._cached_token = data
                else:
                    raise CatalystCredentialError(
                        'AUTHENTICATION_FAILURE',
                        'Unexpected response while fetching access token',
                        str(data)
                    )
            except:
                raise CatalystCredentialError(
                    'AUTHENTICATION_FAILURE',
                    'Error while fetching access token'
                ) from None

        return self._cached_token.get('access_token')

    @staticmethod
    def _validate_refresh_obj(refresh_obj):
        for key in _REFRESH_OBJ_KEYS:
            if key not in refresh_obj or not refresh_obj[key]:
                raise CatalystCredentialError(
                    'INVALID_CREDENTIAL',
                    f'Unable to get "{key}" in refresh_obj dict'
                )

class JwtTokenCredential:
    def __init__(self, _app):
        self.project_key = _app.config.get(PROJECT_KEY)
        self.project_id = _app.config.get(PROJECT_ID)
        self.project_domain = _app.config.get(PROJECT_DOMAIN)
        self._cached_token = None

    def generate_jwt_token(self, cookie: str, requester) -> ICatalystJwtObj:
        resp = requester.request(
                method=RequestMethod.GET,
                url='https://' + self.project_domain +
                    f'/baas/v1/project/{self.project_id}/authentication/custom-token',
                auth=False,
                headers={
                    'cookie': cookie
                }
        )
        data: Dict = resp.response_json.get('data')
        return data

    def get_token(self, cookie: str) -> str:
        if not self._cached_token or self._cached_token.get('expires_in') <= int(round(time())):
            from ._http_client import HttpClient  # pylint: disable=cyclic-import,import-outside-toplevel
            requester = HttpClient(base_url=APIConstants.ACCOUNTS_URL)
            jwt_res = self.generate_jwt_token(cookie, requester)

            post_data = {
                'response_type': 'remote_token',
                'jwt_token': jwt_res['jwt_token'],
                'client_id': jwt_res['client_id'],
                'scope': ' '.join(jwt_res['scopes'])
            }

            resp = requester.request(
                method=RequestMethod.POST,
                url=_PORTAL_ID + f'/clientoauth/v2/{self.project_key}/remote/auth',
                params=post_data,
                auth=False,
                headers = {
                    'Origin': 'https://' + self.project_domain
                }
            )
            data: Dict = resp.response_json
            try:
                if data.get('access_token') and data.get('expires_in_sec'):
                    data.update(
                        {
                            'expires_in': int(round(time())) + data.get('expires_in_sec') - 300
                        }
                    )
                    self._cached_token = data
                else:
                    raise CatalystCredentialError(
                        'AUTHENTICATION_FAILURE',
                        'Unexpected response while fetching access token',
                        str(data)
                    )
            except:
                raise CatalystCredentialError(
                    'AUTHENTICATION_FAILURE',
                    'Error while fetching access token'
                ) from None

        return self._cached_token.get('access_token')
    @staticmethod
    def _validate_jwt_obj(jwt_obj):
        for key in _JWT_TOKEN_KEYS:
            if key not in jwt_obj or not jwt_obj[key]:
                raise CatalystCredentialError(
                    'INVALID_CREDENTIAL',
                    f'Unable to get "{key}" in jwt_obj dict'
                )

class AccessTokenCredential(Credential):
    def __init__(self, token_obj: ICatalystTokenObj):
        super().__init__()
        self._token: str = _get_attr(token_obj, 'access_token')

    def token(self):
        return self._token


class TicketCredential(Credential):
    def __init__(self, ticket_obj: ICatalystTicketObj):
        super().__init__()
        self._token: str = _get_attr(ticket_obj, 'ticket')

    def token(self):
        return self._token


class CookieCredential(Credential):
    def __init__(self, cookie_obj):
        super().__init__()
        cookie_str = _get_attr(cookie_obj, 'cookie')
        csrf_token: str = ZCThreadUtil().get_value(APIConstants.CSRF_TOKEN_COOKIE)
        if not csrf_token:
            cookies_list: List = cookie_str.split("; ")
            for cookie in cookies_list:
                splitted_cookie: List = cookie.split("=")
                if splitted_cookie[0] == APIConstants.CSRF_TOKEN_COOKIE:
                    csrf_token = splitted_cookie[1]
                    break
            ZCThreadUtil().put_value(APIConstants.CSRF_TOKEN_COOKIE, csrf_token)

        self._cookie = cookie_str
        self._csrf_header = APIConstants.CSRF_PARAM_PREFIX + csrf_token

    def token(self):
        return self._cookie, self._csrf_header


class CatalystCredential(Credential):
    def __init__(self, user: str = None):
        super().__init__()
        thread_obj = ZCThreadUtil()
        self._admin_cred: Union[AccessTokenCredential, TicketCredential] = None
        self._user_cred: Union[AccessTokenCredential, TicketCredential, CookieCredential] = None
        self._admin_token: str = thread_obj.get_value(APIConstants.ADMIN_CRED)
        self._user_token: str = thread_obj.get_value(APIConstants.CLIENT_CRED)
        self._cookie: str = thread_obj.get_value(APIConstants.COOKIE_CRED)
        self._admin_cred_type = thread_obj.get_value(APIConstants.ADMIN_CRED_TYPE)
        self._user_cred_type = thread_obj.get_value(APIConstants.CLIENT_CRED_TYPE)
        self._current_user = CredentialUser.USER
        self._strict_scope = False
        self._user_type: Literal['admin', 'user'] \
            = (CredentialUser.ADMIN
               if thread_obj.get_value(APIConstants.USER_TYPE) == CredentialUser.ADMIN
               else CredentialUser.USER)

        if self._is_valid_user(user):
            self._strict_scope = True
            self._current_user = user.lower()

        # Admin Credentials
        if self._admin_cred_type == CredentialType.ticket:
            self._admin_cred = TicketCredential({
                APIConstants.TICKET: self._admin_token
            })
        elif self._admin_cred_type == CredentialType.token:
            self._admin_cred = AccessTokenCredential({
                APIConstants.ACCESS_TOKEN: self._admin_token
            })
        else:
            raise CatalystCredentialError(
                'INVALID_CREDENTIAL',
                "Admin credential type is unknown"
            )

        # Client Credentials
        if not self._user_token and not self._cookie:
            raise CatalystCredentialError(
                'INVALID_CREDENTIAL',
                "User credentials missing"
            )
        if self._user_cred_type == CredentialType.token:
            self._user_cred = AccessTokenCredential({
                APIConstants.ACCESS_TOKEN: self._user_token
            })
        elif self._user_cred_type == CredentialType.ticket:
            self._user_cred = TicketCredential({
                APIConstants.TICKET: self._user_token
            })
        else:
            self._user_cred = CookieCredential({
                APIConstants.COOKIE: self._cookie
            })

    def token(self):
        if self._current_user == CredentialUser.ADMIN:
            return self._admin_cred.__class__.__name__, self._admin_cred.token()
        if self._current_user == CredentialUser.USER:
            if not self._user_cred:
                raise CatalystCredentialError(
                    'INVALID_CREDENTIAL',
                    'User credentials are not initialized'
                )
            # check if user credentials provided are admin credentials while following strict scope
            if self._strict_scope and self._user_type == CredentialUser.ADMIN:
                raise CatalystCredentialError(
                    'INVALID_CREDENTIAL',
                    'No user credentials present for catalyst app initialized in user scope'
                )
            return self._user_cred.__class__.__name__, self._user_cred.token()
        raise CatalystCredentialError(
            'INVALID_CREDENTIAL',
            'user provided is not recognized',
            self._current_user
        )

    def current_user(self):
        return self._current_user

    def current_user_type(self):
        if self._current_user == CredentialUser.USER:
            return self._user_type
        return self._current_user

    def _switch_user(self, user=None):
        if self._strict_scope:
            return self._current_user
        if not user:
            user = (CredentialUser.USER
                    if self._current_user == CredentialUser.ADMIN
                    else CredentialUser.ADMIN)
        self._current_user = user.lower()
        return self._current_user

    @staticmethod
    def _is_valid_user(user):
        if user is None:
            return False

        if not isinstance(user, str) or user.lower() not in _CATALYST_SCOPES:
            raise CatalystAppError(
                'INVALID SCOPE',
                "Scope must be either 'user' or 'admin'"
            )
        return True


class ApplicationDefaultCredential(Credential):
    def __init__(self):
        super().__init__()
        self._credential_obj = None
        self._credential: Union[
            AccessTokenCredential,
            TicketCredential,
            RefreshTokenCredential
        ] = None

        # load credentials from environment
        self._load_credential_from_env()

        if not self._credential_obj:
            raise CatalystCredentialError(
                'INVALID_CREDENTIAL',
                'There is no default credentials in env. Please provide valid credentials.'
            )

        if not isinstance(self._credential_obj, dict):
            raise CatalystCredentialError(
                'INVALID_CREDENTIAL',
                'Credentials present in env is invalid.'
                'Credentials must be stored in env as json string and it must be parsable as dict',
                self._credential_obj
            )

        if 'refresh_token' in self._credential_obj:
            self._credential = RefreshTokenCredential(self._credential_obj)
        elif 'access_token' in self._credential_obj:
            self._credential = AccessTokenCredential(self._credential_obj)
        elif 'ticket' in self._credential_obj:
            self._credential = TicketCredential(self._credential_obj)
        else:
            raise CatalystCredentialError(
                'INVALID_CREDENTIAL',
                'The given credential object does not contain proper credentials'
            )

    def _load_credential_from_env(self):
        auth_json = os.getenv(_CATALYST_AUTH_ENV_KEY)
        if not isinstance(auth_json, str):
            raise CatalystCredentialError(
                'INVALID_CREDENTIAL',
                'Credentials present in env is invalid.'
                'Credentials must be stored in env as json string.'
            )
        auth_dict = json.loads(auth_json)
        self._credential_obj = auth_dict

    @property
    def credential_obj(self):
        return self._credential_obj

    @property
    def credential(self):
        return self._credential

    def token(self):
        return self._credential.token()


def _get_attr(src: Dict, key: str):
    if not isinstance(src, dict):
        raise CatalystCredentialError(
            'INVALID_CREDENTIAL',
            f'Illegal credential obj type - {type(src)} is provided.'
            'Credential obj must be a instance of dict.'
        )
    if key not in src or not src[key]:
        raise CatalystCredentialError(
            'INVALID_CREDENTIAL',
            f"Unable to get '{key}' in credential dict"
        )
    return src[key]
