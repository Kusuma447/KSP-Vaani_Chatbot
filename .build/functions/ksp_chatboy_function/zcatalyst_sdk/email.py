from io import BufferedReader
from typing import Optional
from .types import Component, ICatalystMail, ICatalystProject
from .exceptions import CatalystMailError
from . import validator
from ._http_client import AuthorizedHttpClient
from ._constants import RequestMethod, CredentialUser, Components

_MAIL_OBJ_DICT = {
    'from_email': str,
    'to_email': list,
    'subject': str,
    'content': str,
    'cc': list,
    'bcc': list,
    'reply_to': list,
    'html_mode': bool,
    'display_name': str,
    'attachments': list
}


class ICatalystMailResp(ICatalystMail):
    project_details: Optional[ICatalystProject]


class Email(Component):
    def __init__(self, app) -> None:
        self._app = app
        self._requester = AuthorizedHttpClient(self._app)

    def get_component_name(self):
        return Components.MAIL

    def send_mail(self, mail_obj: ICatalystMail) -> ICatalystMailResp:
        validator.is_non_empty_dict(mail_obj, 'mail_obj', CatalystMailError)
        mail_data = self._generate_data(mail_obj)
        resp = self._requester.request(
            method=RequestMethod.POST,
            path='/email/send',
            files=mail_data,
            user=CredentialUser.ADMIN
        )
        resp_json = resp.response_json
        return resp_json.get('data')

    @staticmethod
    def _generate_data(mail_obj):
        data = []
        for key, data_type in _MAIL_OBJ_DICT.items():
            if key in mail_obj:
                if not isinstance(mail_obj[key], data_type):
                    raise CatalystMailError(
                        'INVALID_MAIL_OBJECT',
                        f'{key} must be an instance of {data_type}'
                    )
                if data_type is list:
                    if key == 'attachments':
                        for attachment in mail_obj[key]:
                            Email._is_valid_attachment(attachment)
                            data.append((key, attachment))
                    else:
                        listed_keys: list = mail_obj[key]
                        data.append((key, (None, ','.join(listed_keys))))
                elif data_type is bool:
                    data.append((key, (None, str(mail_obj[key]).lower())))
                else:
                    data.append((key, (None, mail_obj[key])))
        return data

    @staticmethod
    def _is_valid_attachment(attachment):
        if not isinstance(attachment, BufferedReader):
            raise CatalystMailError(
                'INVALID_MAIL_OBJECT',
                'Attachments must be a instance of BufferReader'
            )
