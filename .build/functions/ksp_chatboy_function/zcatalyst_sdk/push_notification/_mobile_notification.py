import warnings
from typing import List
from enum import Enum
from ..exceptions import CatalystPushNotificationError
from ..types import ICatalystPushDetails, ICatalystMobileNotification
from .._constants import RequestMethod, CredentialUser
from .. import validator
from .._http_client import AuthorizedHttpClient


class MobilePlatform(Enum):
    IOS = "ios"
    ANDROID = "android"


class MobileNotification:
    """
    Class that contains the APIs for mobile push notification
    """

    def __init__(self, requester: AuthorizedHttpClient, app_id):
        self._app_id = app_id
        self._requester = requester

    def send_ios_notification(
        self, notify_obj: ICatalystPushDetails, recipient: str
    ) -> ICatalystMobileNotification:
        """
        Send push notification to IOS mobile devices

        Args:
            notify_obj: details about the notification
            recipient : Catalyst User Id or Email Id of the recipient

        Returns:
            ICatalystMobileNotification: details of the sent notification

        Raises:
            CatalystPushNotificationError: If the `notify_obj` or `recipient` is invalid
        """
        return self.notify(notify_obj, recipient, MobilePlatform.IOS)

    def send_android_notification(
        self, notify_obj: ICatalystPushDetails, recipient: str
    ) -> ICatalystMobileNotification:
        """
        Send push notification to Android mobile devices

        Args:
            notify_obj: details about the notification
            recipient : Catalyst User Id or Email Id of the recipient

        Returns:
            ICatalystMobileNotification: details of the sent notification

        Raises:
            CatalystPushNotificationError: If the `notify_obj` or `recipient` is invalid
        """
        return self.notify(notify_obj, recipient, MobilePlatform.ANDROID)

    def send_notification(
        self, notify_obj: ICatalystPushDetails, recipients: List[str]
    ) -> ICatalystMobileNotification:
        """
        This function is deprecated and will be removed in a future version.
        Use the below functions instead for sending mobile push notification
        - IOS     : `send_ios_notification`
        - Android : `send_android_notification`
        """
        warnings.warn(
            "send_notification() is deprecated use send_ios_notification()"
            + " or send_android_notification() instead.",
            DeprecationWarning,
        )
        return self.notify(
            notify_obj=notify_obj,
            platform=MobilePlatform.IOS,
            recipient=(
                recipients[0]
                if (isinstance(recipients, list) and len(recipients) >= 1)
                else recipients
            ),
        )

    def notify(
        self, notify_obj: ICatalystPushDetails, recipient: str, platform: MobilePlatform
    ) -> ICatalystMobileNotification:
        validator.is_keys_present(
            notify_obj, ["message"], "notify_obj", CatalystPushNotificationError
        )
        validator.is_non_empty_string(recipient, "recipient", CatalystPushNotificationError)
        platform_url = "?isAndroid=true" if (platform == MobilePlatform.ANDROID) else ""
        resp = self._requester.request(
            method=RequestMethod.POST,
            path=f"/push-notification/{self._app_id}/project-user/notify{platform_url}",
            json={"push_details": notify_obj, "recipients": recipient},
            user=CredentialUser.ADMIN,
        )
        return resp.response_json.get("data")
