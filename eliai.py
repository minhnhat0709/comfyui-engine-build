import base64
import datetime
import io
import os
from typing import List
import boto3

from supabase import Client, create_client
import os

from PIL import Image

url: str = os.environ.get('SUPABASE_ENDPOINT') or "https://rtfoijxfymuizzxzbnld.supabase.co"
key: str = os.environ.get('SUPABASE_KEY') or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0Zm9panhmeW11aXp6eHpibmxkIiwicm9sZSI6ImFub24iLCJpYXQiOjE2OTY1Nzc4MTQsImV4cCI6MjAxMjE1MzgxNH0.ChbqzCyTnUkrZ8VMie8y9fpu0xXB07fdSxVrNF9_psE"
supabase: Client = create_client(url, key)

s3client = boto3.client('s3', endpoint_url= os.environ.get('AWS_ENDPOINT') or 'https://2c4e16b2cfe75a3201f2f7638084e66b.r2.cloudflarestorage.com',
    aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID') or "445b3a76828604585e2f38f49b39188b",
    aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY') or "9d5f008e8be8a9990a6cff7c6a1c78fc6498787a022cb0ea759cbd0af30c1848")
bucket_name = os.environ.get('BUCKET_NAME') or "eliai-server"
server_domain = os.environ.get('STORAGE_DOMAIN') or "https://eliai-server.eliai.vn/"

def png_bytes_to_jpg_bytes(png_bytes):
    # Load the PNG image from bytes
    png_image = Image.open(io.BytesIO(png_bytes))
    
    # Convert the image to RGB mode (JPEG does not support transparency)
    rgb_image = png_image.convert('RGB')
    
    # Save the image to a BytesIO object in JPEG format
    jpg_bytes_io = io.BytesIO()
    rgb_image.save(jpg_bytes_io, format='JPEG')
    
    # Get the JPEG bytes
    jpg_bytes = jpg_bytes_io.getvalue()
    
    return jpg_bytes

def s3Storage_base64_upload(image_bytes: bytes, task_id: str, index: int):
    # image_binary = base64.b64decode(base64_image)
    object_key = f"images/{task_id}/{task_id}_{index}.jpg"

    bytes = png_bytes_to_jpg_bytes(image_bytes)
    s3client.upload_fileobj(
      Fileobj=io.BytesIO(bytes),
      Bucket=bucket_name,
      Key=object_key,
      ExtraArgs={'ACL': 'public-read'}  # Optional: Set ACL to make the image public
    )

    return server_domain + object_key



def image_uploading(images: List[bytes], seed:int, task_id:   str, user_id: str, schema="public"):
    # time.sleep(10)
    result = []
    for index, image in enumerate(images):
        image_url = s3Storage_base64_upload(image, task_id, index)
        print(f"{image_url}")
        result.append(image_url)
        supabase.schema(schema).table("Images").insert({
            "image_url": image_url,
            "is_shared": False,
            "seed": seed,
            "task_id": task_id,
            "user_id": user_id
        }).execute()
    

    if len(result) == 0:
        supabase.schema(schema).table("Tasks").update({
            "status": "failed",
            "finished_at": datetime.datetime.utcnow().isoformat()
        }).eq("task_id", task_id).execute()
    else:
        supabase.schema(schema).table("Tasks").update({
            "status": "done",
            "finished_at": datetime.datetime.utcnow().isoformat()
        }).eq("task_id", task_id).execute()