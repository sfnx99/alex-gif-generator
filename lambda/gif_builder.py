import os
import json
from io import BytesIO
from http import HTTPStatus
import boto3
from PIL import Image

# Set these in Lambda env
NUM_FRAMES = int(os.environ['NUM_FRAMES'])
DURATION = int(os.environ['DURATION'])

s3 = boto3.client('s3')
S3_BUCKET = os.environ['S3_BUCKET']

def lambda_handler(event, context):
    print("EVENT:", json.dumps(event))
    try:
        job_id = event['detail']['job_id']
        frames = []

        original_key = f"inputs/{job_id}/input.png"
        original_obj = s3.get_object(Bucket=S3_BUCKET, Key=original_key)
        original_image = Image.open(BytesIO(original_obj['Body'].read()))
        frames.append(original_image.convert("RGB"))

        # Load all frames
        for i in range(NUM_FRAMES):
            key = f"outputs/{job_id}/frame_{i+1}.png"
            obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
            frame = Image.open(BytesIO(obj['Body'].read()))
            frames.append(frame.convert("RGB"))

        # Build GIF
        gif_buffer = BytesIO()
        frames[0].save(gif_buffer, format='GIF', append_images=frames[1:], save_all=True, duration=DURATION, loop=0)

        # Upload GIF to S3
        gif_key = f"outputs/{job_id}/final.gif"
        s3.put_object(Bucket=S3_BUCKET, Key=gif_key, Body=gif_buffer.getvalue(), ContentType='image/gif')

        return {
            'statusCode': HTTPStatus.OK,
            'headers': {
                'Access-Control-Allow-Origin': 'http://localhost:8000',
            },
            'body': f"https://{S3_BUCKET}.s3.amazonaws.com/{gif_key}"
        }
    except Exception as e:
        print("ERROR:", str(e))
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "headers": {
                "Access-Control-Allow-Origin": "http://localhost:8000"
            },
            "body": json.dumps({"error": str(e)})
        }
