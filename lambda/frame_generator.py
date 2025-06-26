import json
import os
from http import HTTPStatus
from io import BytesIO
import boto3
import requests
from botocore.exceptions import ClientError
from PIL import Image

PROMPT_BASE = "I would like to generate frames of a gif based on the provided image. Focus on making changes on the subject declared in the prompt and leaving the background untouched. Please generate frame"

# Set these in Lambda env
STABILITY_API_KEY = os.environ['STABILITY_API_KEY']
NUM_FRAMES = int(os.environ['NUM_FRAMES'])
STRENGTH = os.environ['STRENGTH']
MODEL = os.environ['MODEL']

s3 = boto3.client('s3')
eventbridge = boto3.client('events')

S3_BUCKET = os.environ['S3_BUCKET']

def lambda_handler(event, context):
    print("EVENT:", json.dumps(event))

    job = json.loads(event['Records'][0]['body'])
    job_id = job['job_id']
    prompt = job['prompt']
    image_key = job['image_key']

    # idempotency check
    output_key = f"outputs/{job_id}/frame_1.png"
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=output_key)
        print(f"Job {job_id} has already been processed. Skipping.")
        return {"statusCode": HTTPStatus.OK}
    except ClientError as e:
        if e.response['Error']['Code'] not in ("403", "404"):
            raise

    img_object = s3.get_object(Bucket=S3_BUCKET, Key=image_key)
    input_image = img_object['Body'].read()
    original_pil_image = Image.open(BytesIO(input_image))
    original_size = original_pil_image.size

    current_image = input_image

    for i in range(NUM_FRAMES):
        prompt_text = f"{PROMPT_BASE} {i + 1} of {NUM_FRAMES} according to the following prompt: {prompt}"


        job = json.loads(event['Records'][0]['body'])
        prompt = job['prompt']

        response = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/sd3",
            headers={
                "authorization": f"Bearer {STABILITY_API_KEY}",
                "accept": "image/*"
            },
            files={
                "image": ("input.png", current_image, "image/png")
            },
            data={
                "prompt": prompt_text,
                "strength": STRENGTH,
                "mode": "image-to-image",
                "output_format": "png",
                "model": MODEL
            },
        )

        if response.status_code == HTTPStatus.OK:
            generated_image = Image.open(BytesIO(response.content)).convert("RGB")
            resized_image = generated_image.resize(original_size, Image.Resampling.LANCZOS)
            buffer = BytesIO()
            resized_image.save(buffer, format="PNG")
            buffer.seek(0)
            current_image = buffer.getvalue()
            frame_key = f"outputs/{job_id}/frame_{i + 1}.png"
            s3.put_object(Bucket=S3_BUCKET, Key=frame_key, Body=current_image, ContentType='image/png')
        else:
            print("Image generation failed:")
            print("Status Code:", response.status_code)
            print("Response Body:", response.text)
            raise Exception(f"Stability API error {response.status_code}: {response.text}")

    eventbridge.put_events(
        Entries=[
            {
                'Source': 'gif.frames.complete',
                'DetailType': 'GIFGeneration',
                'Detail': json.dumps({
                    'job_id': job_id
                })
            }
        ]
    )

    return {"statusCode": HTTPStatus.OK}
