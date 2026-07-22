# Copyright (c) 2023, ZOHO CORPORATION PRIVATE LIMITED
# All rights reserved.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


""" SDK for Catalyst by Zoho """
import threading
from typing import Dict, Literal
from .types import ICatalystOptions
from . import credentials
from .catalyst_app import CatalystApp
from ._thread_util import ZCThreadUtil, get_attr
from .exceptions import CatalystAppError
from . import _constants as APIConstants
from ._constants import ProjectHeader, CredentialHeader
from ._util import parse_headers_from_request

_app_collection = {}
_app_lock = threading.RLock()

_DEFAULT_APP_NAME = '[DEFAULT]'
CatalystScopes = Literal['admin', 'user']


def initialize(
    name=_DEFAULT_APP_NAME,
    scope: CatalystScopes = None,
    req = None
):
    """
    Initializes a new CatalystApp from request

    Args:
        name: Name of the catalyst app (optional).
            If app name is None, default name will be used.
        scope: The scope in which the app gets initialized (optional).
            If no scope provided, catalyst will switch scopes automatically.
        req: Request object to initialize the SDK

    Returns:
        CatalystApp: A newly initialized catalyst app instance.

    Raises:
        CatalystAppError: If the given scope or other app properties are invalid.
        CatalystCredentialError: If the credentials are missing.
    """

    if req:
        parse_headers_from_request(req)

    thread_obj = ZCThreadUtil()
    catalyst_headers: Dict = thread_obj.get_value("catalyst_headers")

    if not catalyst_headers:
        raise CatalystAppError(
            'FATAL ERROR',
            'Catalyst headers are empty'
        )

    # creating options from catalyst config
    options = {
        APIConstants.PROJECT_KEY: get_attr(catalyst_headers, ProjectHeader.key),
        APIConstants.PROJECT_ID: get_attr(catalyst_headers, ProjectHeader.project_id),
        APIConstants.PROJECT_DOMAIN: get_attr(catalyst_headers, ProjectHeader.domain),
        APIConstants.ENVIRONMENT: get_attr(catalyst_headers, ProjectHeader.environment),
        APIConstants.PROJECT_SECRET_KEY: get_attr(
            catalyst_headers,
            ProjectHeader.project_secret_key
        )
    }

    admin_token = get_attr(catalyst_headers, CredentialHeader.admin_token)
    if admin_token:
        thread_obj.put_value(APIConstants.ADMIN_CRED, admin_token)
        thread_obj.put_value(
            APIConstants.ADMIN_CRED_TYPE,
            get_attr(catalyst_headers, CredentialHeader.admin_cred_type)
        )

    user_token = get_attr(catalyst_headers, CredentialHeader.user_token)
    if user_token:
        thread_obj.put_value(APIConstants.CLIENT_CRED, user_token)
        thread_obj.put_value(
            APIConstants.CLIENT_CRED_TYPE,
            get_attr(catalyst_headers, CredentialHeader.user_cred_type)
        )

    cookie_str = get_attr(catalyst_headers, CredentialHeader.cookie)
    if cookie_str:
        thread_obj.put_value(APIConstants.COOKIE_CRED, cookie_str)

    user_type = get_attr(catalyst_headers, CredentialHeader.user)
    if user_type:
        thread_obj.put_value(APIConstants.USER_TYPE, user_type)

    credential = credentials.CatalystCredential(scope)
    app = CatalystApp(credential, options, name)

    with _app_lock:
        _app_collection[f'{app.name}_{threading.get_ident()}'] = app
        return app


def initialize_app(
    credential: credentials.Credential = None,
    options: ICatalystOptions = None,
    name=_DEFAULT_APP_NAME
):
    """
    Initializes a new CatalystApp

    Args:
        credential: A credential object of valid Credential type which is initialized from
            catalyst credential module (optional). If credential is None,
            first will check for valid credentials in credential path file and next in env.
        options: A dictionary of key-value pairs (optional). If passed, it must contains the
            mandatory keys - 'project_id', 'project_key' and 'project_domain'.
            If no options provided will check it in env.
        name: Name of the catalyst app (optional).
            If app name is None, default name will be used.

    Returns:
        CatalystApp: A newly initialized catalyst app instance.

    Raises:
        CatalystAppError: If duplicate app name provided  or app options are invalid.
        CatalystCredentialError: If the given credentials are invalid.
    """
    if not isinstance(name, str) or not name:
        raise CatalystAppError(
            'INVALID_APP_NAME',
            'App name must be a non-empty string',
            name
        )

    with _app_lock:
        if f'{name}_{threading.get_ident()}' in _app_collection:
            raise CatalystAppError(
                'DUPLICATE_APP',
                f'There is already an app named "{name}".'
            )

    if credential is None:
        credential = credentials.ApplicationDefaultCredential().credential

    app = CatalystApp(credential, options, name)

    with _app_lock:
        _app_collection[f'{app.name}_{threading.get_ident()}'] = app
        return app


def get_app(name=_DEFAULT_APP_NAME) -> CatalystApp:
    if not isinstance(name, str):
        raise CatalystAppError(
            'INVALID_APP_NAME',
            'app name must be a string.'
        )
    if f'{name}_{threading.get_ident()}' not in _app_collection:
        err_msg = (
            'Default app does not exist. Make sure to initialize the default app.'
            if name == _DEFAULT_APP_NAME
            else f'There is no app named "{name}". Make sure to initialize the app.'
        )

        raise CatalystAppError(
            'INVALID_APP_NAME',
            err_msg
        )

    with _app_lock:
        return _app_collection[f'{name}_{threading.get_ident()}']
