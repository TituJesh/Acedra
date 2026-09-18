import boto3

from app.config import AWS_REGION, S3_BUCKET_NAME


s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION
)


def upload_file_to_s3(
    file_object,
    s3_key: str,
    content_type: str | None = None
):
    extra_args = {}

    if content_type:
        extra_args["ContentType"] = content_type

    s3_client.upload_fileobj(
        file_object,
        S3_BUCKET_NAME,
        s3_key,
        ExtraArgs=extra_args
    )


def delete_file_from_s3(s3_key: str):
    s3_client.delete_object(
        Bucket=S3_BUCKET_NAME,
        Key=s3_key
    )

def generate_download_url(
    s3_key: str,
    expiration: int = 300
):
    return s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": S3_BUCKET_NAME,
            "Key": s3_key
        },
        ExpiresIn=expiration
    )