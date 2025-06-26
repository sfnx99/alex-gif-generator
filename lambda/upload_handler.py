import uuid
import base64
import json
import os
from http import HTTPStatus
from io import BytesIO
import boto3
from PIL import Image

s3 = boto3.client('s3')
sqs = boto3.client('sqs')

S3_BUCKET = os.environ['S3_BUCKET']
QUEUE_URL = os.environ['GENERATION_QUEUE_URL']
ACCESS_TOKEN = os.environ['ACCESS_TOKEN']

def resize_image(image, max_size=1024):
    """
    Resize an image while keeping aspect ratio, with the largest dimension set to max_size.
    """
    width, height = image.size
    if max(width, height) <= max_size:
        return image
    if width > height:
        new_width = max_size
        new_height = int(height * max_size / width)
    else:
        new_height = max_size
        new_width = int(width * max_size / height)
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

def lambda_handler(event, context):
    print("EVENT:", json.dumps(event))
    try:
        if event.get('httpMethod', '') == 'OPTIONS':
            return {
                "statusCode": HTTPStatus.OK,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                },
                "body": "",
            }

        body = json.loads(event.get('body', '{}'))
        prompt = body.get('prompt')
        image_base64 = body.get('image_base64')
        token = body.get('access_token')

        if token != ACCESS_TOKEN:
            return {
                "statusCode": HTTPStatus.FORBIDDEN,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Invalid access token"}),
            }

        if not prompt or not image_base64:
            return {
                "statusCode": HTTPStatus.BAD_REQUEST,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Missing prompt or image_base64 in request body"}),
            }

        image_data = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_data))
        resized_image = resize_image(image)

        buffer = BytesIO()
        resized_image.save(buffer, format='PNG')
        buffer.seek(0)

        job_id = str(uuid.uuid4())
        image_key = f"inputs/{job_id}/input.png"

        s3.put_object(Bucket=S3_BUCKET, Key=image_key, Body=buffer.getvalue(), ContentType='image/png')

        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps({
                'job_id': job_id,
                'prompt': prompt,
                'image_key': image_key
            })
        )

        return {
            'statusCode': HTTPStatus.OK,
            'headers': {
                "Access-Control-Allow-Origin": "*",
            },
            'body': json.dumps({'job_id': job_id}),
        }

    except Exception as e:
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "headers": {
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": str(e)}),
        }
