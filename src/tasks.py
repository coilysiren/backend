import json

import dotenv
import invoke
import requests

from . import bsky as _bsky


dotenv.load_dotenv()
bsky_client = _bsky.init()


@invoke.task
def bsky(ctx: invoke.Context, path: str, **kwargs):
    token = bsky_client._session.access_jwt
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    response = requests.get(f"https://bsky.social/xrpc/{path}", headers=headers, timeout=30, params=kwargs)
    print(f"status code: {response.status_code}")
    print(response.headers)
    print(json.dumps(response.json(), indent=2))
