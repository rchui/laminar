import os

import boto3
import botocore
from smart_open import open as open  # noqa
from smart_open import parse_uri


def exists(uri: str) -> bool:
    parts = parse_uri(uri)

    if parts.scheme == "file":
        return os.path.isfile(parts.uri_path)
    elif parts.scheme == "s3":
        try:  # Check if file exists
            s3 = boto3.resource("s3")
            s3.Object(parts.bucket_id, parts.key_id).load()
            return True
        except botocore.exceptions.ClientError as exception:
            if exception.response["Error"]["Code"] == "404":
                return False
            else:  # Something else went wrong. Fail
                raise
    else:
        raise NotImplementedError(f"Unrecognized scheme '{parts.scheme}' from '{parts}' for '{uri}'.")
