# AI GIF Generator using AWS Lambda and Serverless Architecture

## Overview

This is a serverless web application that allows users to generate animated GIFs from an uploaded image and prompt using generative AI. The system processes images in multiple stages using AWS Lambda functions, orchestrated via SQS and EventBridge, and serves the resulting GIF back to the user via a static S3-hosted frontend.

---

## Features

- Upload an image and prompt to generate a GIF
- Uses AI (Stability API) to create image-to-image transformations
- Animates results into a downloadable GIF
- Fully serverless using AWS Lambda, S3, API Gateway, SQS, and EventBridge
- Static frontend hosted on Amazon S3
- Token-based access control

---

## How AWS Lambda is Used

The application relies on **AWS Lambda** for compute and logic. Three Lambda functions handle the entire GIF generation lifecycle:

### 1. `UploadHandler` Lambda
- **Trigger:** Invoked by API Gateway when the user submits a form.
- **Responsibilities:**
  - Accepts image and prompt data from the frontend.
  - Resizes and stores the input image in S3.
  - Enqueues a new job in an SQS queue for frame generation.
  - Validates access using a static token.
- **Environment Variables:**
  - `GENERATION_QUEUE_URL` – SQS URL
  - `S3_BUCKET` – Bucket name to store image

---

### 2. `FrameGenerator` Lambda
- **Trigger:** Automatically triggered by messages from the SQS queue.
- **Responsibilities:**
  - Downloads the uploaded image from S3.
  - For each frame:
    - Calls the Stability AI API with an updated prompt
    - Uploads the frame back to S3
  - Once all frames are generated, publishes a custom event to EventBridge to notify the next step.
- **Environment Variables:**
  - `STABILITY_API_KEY`, `S3_BUCKET`, etc.

---

### 3. `GifBuilder` Lambda
- **Trigger:** EventBridge rule matching `gif.frames.complete` events.
- **Responsibilities:**
  - Loads all generated frames from S3
  - Uses Python’s `PIL` (Pillow) library to stitch them into an animated GIF
  - Uploads the final `.gif` file to the output S3 folder

---

## Why Lambda?

- **Serverless Scalability:** No need to manage infrastructure.
- **Cost Efficient:** Pay only for what you use.
- **Event-Driven:** Natural fit for async image generation pipeline.
- **Granular Permissions:** Each function has a minimal IAM role tailored to its tasks.

---

## Deployment

The application is deployed using **AWS SAM (Serverless Application Model)**. Key resources include:

- Lambda functions (`UploadHandler`, `FrameGenerator`, `GifBuilder`)
- SQS queue
- S3 buckets (for image storage and static frontend hosting)
- API Gateway
- EventBridge Rule

---

## Frontend

- Hosted as a static website on S3
- Users upload an image, enter a prompt, and submit the form
- Uses JavaScript to interact with API Gateway
- Polls S3 to check when the final GIF is available

---

## Security

- A static access token is required and validated by the Lambda backend.
- IAM policies restrict access for each function.
- S3 bucket access is tightly controlled (CORS + static site hosting + token validation).

---

## License

MIT License
