from datetime import datetime, timedelta, timezone
import json
import os

import boto3
from jose import jwt

from app.config import AWS_REGION, ENVIRONMENT


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def get_secret_key():
    if ENVIRONMENT == "production":
        secrets_client = boto3.client(
            "secretsmanager",
            region_name=AWS_REGION
        )

        response = secrets_client.get_secret_value(
            SecretId="acedra/jwt"
        )

        secret_data = json.loads(response["SecretString"])

        return secret_data["SECRET_KEY"]

    return os.getenv("SECRET_KEY")


SECRET_KEY = get_secret_key()


def create_access_token(data: dict) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )