# pylint: disable=cyclic-import
import os
import json
import threading
from typing import Dict, Union, Optional
import warnings

from zcatalyst_sdk.connections import Connections

from .nosql import NoSql
from .types import ICatalystConfig
from . import _constants as APIConstants
from .credentials import Credential
from .exceptions import CatalystAppError, CatalystCredentialError
from .cache import Cache
from .cron import Cron
from .datastore import Datastore
from .filestore import Filestore
from .zcql import Zcql
from .email import Email
from .search import Search
from .functions import Functions
from .authentication import Authentication
from .push_notification import PushNotification
from .zia import Zia
from .circuit import Circuit
from .connection import Connection
from .smartbrowz import SmartBrowz
from .quick_ml import QuickML
from .stratus import Stratus
from .job_scheduling import JobScheduling
from .pipeline import Pipeline

CATALYST_OPTIONS_ENV_KEY = 'CATALYST_OPTIONS'
CONFIG_MANDATORIES = {
    APIConstants.PROJECT_ID: (int, str),
    APIConstants.PROJECT_KEY: (int, str),
    APIConstants.PROJECT_DOMAIN: (str,)
}
DEFAULT_ENVIRONMENT = "Development"


class CatalystAppOptions:
    def __init__(self, options: Dict):
        if options is None:
            options = self._load_options_from_env()
        if not isinstance(options, dict):
            raise CatalystAppError(
                'INVALID_APP_OPTIONS',
                f'Illegal app option type - {type(options)}. App options must be a instance of dict'
            )
        config = CatalystAppOptions.validate_options(options)
        self._config = config

    @property
    def config(self):
        return self._config

    @staticmethod
    def _load_options_from_env():
        options_json = os.getenv(CATALYST_OPTIONS_ENV_KEY)
        options = json.loads(options_json)
        if not isinstance(options, dict):
            raise CatalystAppError(
                'INVALID_APP_OPTIONS',
                'App options present in env is invalid.'
                'App options must be stored in env as json string and it must be parsable as dict',
                options
            )
        return options

    @staticmethod
    def validate_options(options: Dict):
        # validation for option keys
        for key, val in CONFIG_MANDATORIES.items():
            if not options.get(key):
                raise CatalystAppError(
                    'INVALID_APP_OPTIONS',
                    (f"Either the key '{key}' is missing or "
                     f"value provided for the {key} is None in app options")
                )
            if not isinstance(options[key], val):
                raise CatalystAppError(
                    'INVALID_APP_OPTIONS',
                    f'{key} must be a instance of {" or ".join([type.__name__ for type in val])}'
                )

        # If environment is empty, set default environment as Development
        if not options.get(APIConstants.ENVIRONMENT):
            options.update({APIConstants.ENVIRONMENT: DEFAULT_ENVIRONMENT})

        if not options.get(APIConstants.PROJECT_SECRET_KEY):
            options.update({APIConstants.PROJECT_SECRET_KEY: None})

        return options


class CatalystApp:
    def __init__(
        self,
        credential: Credential,
        options: Dict,
        name: str
    ):
        if not name or not isinstance(name, str):
            raise CatalystAppError(
                'INVALID_APP_NAME',
                'App name must be a non-empty string',
                name
            )
        self._name = name

        if not isinstance(credential, Credential):
            raise CatalystCredentialError(
                'INVALID CREDENTIAL',
                f'Illegal credential type - {type(credential)}.'
                'credential must be initialized with valid Credential instance.'
            )

        self._credential = credential
        self._options = CatalystAppOptions(options)
        self._lock = threading.RLock()
        self._services: Dict = {}

    @property
    def name(self):
        return self._name

    @property
    def credential(self):
        return self._credential

    @property
    def config(self) -> ICatalystConfig:
        return self._options.config

    @property
    def services(self):
        return self._services

    @property
    def scope(self) -> Optional[str]:
        """
        Returns: Scope of the app if initialized with scope, else None
        """
        if hasattr(self._credential, '_strict_scope'):
            if self._credential._strict_scope:  # pylint: disable=protected-access
                return self._credential.current_user()
        return None

    def cache(self) -> Cache:
        return self._ensure_service('cache', Cache)

    def cron(self) -> Cron:
        return self._ensure_service('cron', Cron)

    def datastore(self) -> Datastore:
        return self._ensure_service('datastore', Datastore)

    def filestore(self) -> Filestore:
        return self._ensure_service('filestore', Filestore)

    def zcql(self) -> Zcql:
        return self._ensure_service('zcql', Zcql)

    def email(self) -> Email:
        return self._ensure_service('mail', Email)

    def search(self) -> Search:
        return self._ensure_service('search', Search)

    def functions(self) -> Functions:
        return self._ensure_service('functions', Functions)

    def authentication(self) -> Authentication:
        warnings.warn("authentication() is deprecated use user_management() instead.",
                      DeprecationWarning)
        return self._ensure_service('user-management', Authentication)

    def user_management(self) -> Authentication:
        return self._ensure_service('user-management', Authentication)

    def push_notification(self) -> PushNotification:
        return self._ensure_service('push-notification', PushNotification)

    def zia(self) -> Zia:
        return self._ensure_service('zia', Zia)

    def circuit(self) -> Circuit:
        return self._ensure_service('circuit', Circuit)

    def connection(self, properties: Union[str, Dict[str, Dict[str, str]]]) -> Connection:
        return self._ensure_service('connection', Connection, override=True, properties=properties)

    def smart_browz(self) -> SmartBrowz:
        return self._ensure_service('SmartBrowz', SmartBrowz)

    def quick_ml(self) -> QuickML:
        return self._ensure_service('QuickML', QuickML)

    def stratus(self) -> Stratus:
        return self._ensure_service('Stratus', Stratus)

    def job_scheduling(self) -> JobScheduling:
        return self._ensure_service('JobScheduling', JobScheduling)

    def pipeline(self) -> Pipeline:
        return self._ensure_service('pipeline', Pipeline)

    def nosql(self) -> NoSql:
        return self._ensure_service('NoSql', NoSql)

    def connections(self) -> Connections:
        return self._ensure_service('connections', Connections)

    def _ensure_service(self, service_name: str, initializer, **kwargs):
        with self._lock:
            if service_name not in self._services or kwargs.get('override'):
                self._services[service_name] = initializer(self, **kwargs)
            return self._services[service_name]
