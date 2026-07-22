from typing import List
from ..exceptions import CatalystPushNotificationError
from .._http_client import AuthorizedHttpClient
from .. import validator
from .._constants import (
    RequestMethod,
    CredentialUser
)


class WebNotification:
    def __init__(self, notification_instance):
        self._app = notification_instance._app
        self._requester: AuthorizedHttpClient = notification_instance._requester

    def send_notification(
        self,
        message: str,
        recipients: List[str]
    ) -> bool:
        validator.is_non_empty_string(message, 'message', CatalystPushNotificationError)
        validator.is_non_empty_list(recipients, 'recipients', CatalystPushNotificationError)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path='/project-user/notify',
            json={
                'message': message,
                'recipients': recipients
            },
            user=CredentialUser.ADMIN
        )
        return resp.response_json.get('data')
