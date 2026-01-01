from datetime import datetime, timedelta, timezone
from typing import Sequence

import jwt
from jwt import InvalidTokenError


def create_access_token(
    *,
    user_id: int,
    secret: str,
    algorithm: str = "HS256",
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    exp = now + (expires_delta or timedelta(minutes=30))
    payload = {"sub": str(user_id), "iat": now, "exp": exp}
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(
    token: str,
    *,
    secret: str,
    algorithms: Sequence[str],
) -> int:
    try:
        payload = jwt.decode(token, secret, algorithms=list(algorithms))
    except InvalidTokenError as exc:  # includes ExpiredSignatureError
        raise ValueError("invalid token") from exc

    sub = payload.get("sub")
    if sub is None:
        raise ValueError("token missing sub")
    try:
        return int(sub)
    except (TypeError, ValueError) as exc:
        raise ValueError("token sub is not an integer") from exc
