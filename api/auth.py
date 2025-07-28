# api/auth.py

import jwt
import uuid
import hashlib
from urllib.parse import urlencode

from datetime import datetime, timedelta

import time
from core import config

def _generate_payload(query: dict = None) -> dict:
    payload = {
        'access_key': config.ACCESS_KEY,
        'nonce': str(uuid.uuid4()),
    }

    if query is not None:
        query_string = urlencode(query).encode()
        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()
        payload.update({
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        })

    return payload

def generate_jwt_token(query: dict = None) -> str:
    payload = _generate_payload(query)
    jwt_token = jwt.encode(payload, config.SECRET_KEY)
    authorization_token = f'Bearer {jwt_token}'
    return authorization_token
