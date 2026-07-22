from typing import Union
from ..types import Component
from ..exceptions import CatalystPushNotificationError
from .._http_client import AuthorizedHttpClient
from .. import validator
from .._constants import Components
from ._web_notificaton import WebNotification
from ._mobile_notification import MobileNotification


class PushNotification(Component):
    def __init__(self, app):
        self._app = app
        self._requester = AuthorizedHttpClient(app)

    def get_component_name(self):
        return Components.PUSH_NOTIFICATION

    def mobile(self, app_id: Union[int, str]):
        """
        Create a Mobile notification instance

        Args:
            app_id: AppId for identifying the registered mobile application

        Returns:
            MobileNotification: Returns an instance of MobileNotification class
        """
        validator.is_non_empty_string_or_number(app_id, 'app_id', CatalystPushNotificationError)
        return MobileNotification(self._requester, str(app_id))

    def web(self):
        """
        Create a Web notification instance

        Returns:
            WebNotification: Returns an instance of WebNotification class
        """
        return WebNotification(self)
