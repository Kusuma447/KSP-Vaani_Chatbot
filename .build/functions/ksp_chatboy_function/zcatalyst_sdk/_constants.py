import os
from os import path


def env_override(env_name: str, default_value: str):
    env_value = os.getenv(env_name)
    if not env_value:
        return default_value
    return env_value


meta_file = path.join(path.dirname(path.abspath(__file__)), '__version__.py')
meta = {}
with open(meta_file, encoding="utf-8") as fp:
    exec(fp.read(), meta) # pylint: disable=exec-used

# SDK version
SDK_VERSION = meta['__version__']

# Json variables
JSON_RESPONSE_KEY = "data"
JSON_RESPONSE_STATUS = "status"
JSON_RESPONSE_MESSAGE = "message"
JSON_RESPONSE_CODE = "error_code"
SUCCESS_STATUS = "success"
FAILURE_STATUS = "failure"

# Environment Variable
PROJECT_KEY = "project_key"
PROJECT_ID = "project_id"
PROJECT_DOMAIN = "project_domain"
ENVIRONMENT = "environment"
PROJECT_SECRET_KEY = "project_secret_key"
ADMIN_CRED = "admin_cred"
CLIENT_CRED = "client_cred"
COOKIE_CRED = "cookie_cred"
ACCESS_TOKEN = "access_token"
CLIENT_ACCESS_TOKEN = "client_token"
CLIENT_COOKIE = "client_cookie"
CLIENT_ID = "client_id"
EXPIRES_IN = "expires_in"
REFRESH_IN = "refresh_in"
CLIENT_SECRET = "client_secret"
AUTH_URL = "auth_url"
REFRESH_URL = "refresh_url"
REDIRECT_URL = "redirect_url"
GRANT_TYPE = "grant_type"
CODE = "code"
TICKET = "ticket"
ADMIN_CRED_TYPE = "admin_cred_type"
CLIENT_CRED_TYPE = "client_cred_type"
REFRESH_TOKEN = "refresh_token"
SCOPES="scopes"
JWT_TOKEN = "refresh_token"
USER_TYPE = "user_type"
CONNECTOR_NAME = "connector_name"
ENVIRONMENT_KEY_NAME = "X-Catalyst-Environment"
USER_KEY_NAME = "X-CATALYST-USER"
CATALYST_ORG_ID_KEY="CATALYST-ORG"
X_CATALYST_ORG_ENV_KEY = 'X_ZOHO_CATALYST_ORG_ID'

# URL constants
PROJECT_URL = "project"
PROJECT_KEY_NAME = "PROJECT_ID"
URL_SEPARATOR = "/"
IS_LOCAL = env_override("X_ZOHO_CATALYST_IS_LOCAL", "False")
CSRF_TOKEN_COOKIE = "ZD_CSRF_TOKEN"
APP_DOMAIN = env_override("X_ZOHO_CATALYST_CONSOLE_URL", "https://console.catalyst.localzoho.com")
APP_VERSION_V1 = "/v1"
ACCOUNTS_URL = env_override("X_ZOHO_CATALYST_ACCOUNTS_URL", "https://accounts.localzoho.com")
STRATUS_SUFFIX = env_override("X_ZOHO_STRATUS_RESOURCE_SUFFIX", ".zohostratus.com")

# Header Constants
CONTENT_TYPE = "Content-Type"
CLIENT_HEADER = "PROJECT_ID"
COOKIE_HEADER = "Cookie"
CSRF_HEADER = "X-ZCSRF-TOKEN"
USER_AGENT = "USER-AGENT"

# Auth Constants
AUTHORIZATION = "Authorization"
COOKIE = "cookie"
USER_SCOPE_HEADER = "X-CATALYST-USER"
ADMIN_SCOPE = "admin"
USER_SCOPE = "user"
OAUTH_PREFIX = "Zoho-oauthtoken "
TICKET_PREFIX = "Zoho-ticket "
CSRF_PARAM_PREFIX = "zd_csrparam="
ZAID = 'zaid'


class AcceptHeader:
    KEY = 'Accept'
    VALUE = 'application/vnd.catalyst.v2+json'
    ZCQL = 'application/vnd.catalyst.v2+zcql'


class CredentialUser:
    ADMIN = 'admin'
    USER = 'user'


class RequestMethod:
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    HEAD = "HEAD"
    DELETE = "DELETE"
    PATCH = "PATCH"


class Components:
    CACHE = "Cache"
    FILE_STORE = "FileStore"
    MAIL = "Mail"
    SEARCH = "Search"
    ZCQL = "ZCQL"
    ZIA = "Zia"
    CRON = "Cron"
    DATA_STORE = "DataStore"
    FUNCTION = "Function"
    AUTHENTICATION = "Authentication"
    CIRCUIT = "Circuit"
    PUSH_NOTIFICATION = "PushNotification"
    SMART_BROWZ = "SmartBrowz"
    QUICK_ML = "QuickML"
    STRATUS = "Stratus"
    JOB_SCHEDULING = "JobScheduling"
    PIPELINE = "Pipeline"
    NOSQL = 'NoSql'
    CONNECTIONS = 'Connections'


class CredentialType:
    token = 'token'
    ticket = 'ticket'


class ProjectHeader:
    project_id = 'X-ZC-ProjectId'
    domain = 'X-ZC-Project-Domain'
    key = 'X-ZC-Project-Key'
    environment = 'X-ZC-Environment'
    project_secret_key = 'X-ZC-PROJECT-SECRET-KEY'


class CredentialHeader:
    admin_cred_type = 'X-ZC-Admin-Cred-Type'
    user_cred_type = 'X-ZC-User-Cred-Type'
    admin_token = 'X-ZC-Admin-Cred-Token'
    user_token = 'X-ZC-User-Cred-Token'
    cookie = 'x-zc-cookie'
    zcsrf = 'X-ZCSRF-TOKEN'
    user = 'X-ZC-User-Type'
    signature = "X-ZC-Stratus-Signature"


class CatalystService:
    SERVERLESS = 'baas'
    BROWSER360 = 'browser360'
    QUICK_ML = 'quickml'
    STRATUS = 'stratus'
