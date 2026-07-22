from datetime import datetime
from typing import Dict, Optional
from urllib.parse import parse_qs

from .._http_client import AuthorizedHttpClient
from ..types.stratus import StratusSignature
from .._constants import CredentialUser, RequestMethod


class SignatureCache:
    """
    Handles signature caching and retrieval for bucket authentication.
    """
    bucket_signatures: Dict[str, Dict] = {}

    @classmethod
    def get_signature(cls, bucket_name: str) -> Optional[Dict]:
        """
        Retrieve the cached signature for the specified bucket if valid.
        """
        sign = cls.bucket_signatures.get(bucket_name)
        if sign and int(sign.get('expiry_time', 0)) > int(datetime.now().timestamp() * 1000):
            return sign.get('signature')
        return None

    @classmethod
    def update_signature(cls, bucket_name: str, signature: Dict) -> None:
        """
        Update the cached signature for the specified bucket.
        """
        cls.bucket_signatures[bucket_name] = signature


class AuthUtil:
    """
    Handles user authentication and signature retrieval for buckets.
    """
    def __init__(self, bucket_name: str, requester: AuthorizedHttpClient) -> None:
        self.bucket_name = bucket_name
        self._requester = requester
        self.user_type = requester._app.credential.current_user_type()
        self.user_scope = requester._app.credential.current_user()

    def get_user_type(self) -> str:
        """
        Retrieve the user type.
        """
        return self.user_type

    def get_user_scope(self) -> str:
        """
        Retrieve the user scope.
        """
        return self.user_scope

    def get_bucket_signature(self) -> Optional[StratusSignature]:
        """
        Retrieve or refresh the bucket signature.

        Returns:
            Optional[StratusSignature]: The valid bucket signature.
        """
        if self.user_type == 'admin' or self.user_scope == 'admin':
            signature = SignatureCache.get_signature(self.bucket_name)
            if signature:
                return signature
            return self._refresh_signature()
        return None

    def _refresh_signature(self) -> Optional[StratusSignature]:
        """
        Fetch a new signature from the server and update the cache.

        Returns:
            Optional[StratusSignature]: The refreshed bucket signature.
        """
        req_params = {'bucket_name': self.bucket_name}
        response = self._requester.request(
            method=RequestMethod.POST,
            path='/bucket/signature',
            params=req_params,
            user=CredentialUser.ADMIN
        )
        sign = response.response_json.get('data')
        if sign:
            sign['expiry_time'] = int(sign.get('expiry_time', 0)) - 300000
            sign['signature'] = parse_qs(sign.get('signature'))
            SignatureCache.update_signature(self.bucket_name, sign)
            return sign.get('signature')
        return None
