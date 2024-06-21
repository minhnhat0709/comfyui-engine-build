import json
import os
from comfyapp import ComfyUI
import redis
import time

def main():
  comfyUI = ComfyUI()
  comfyUI.prepare_comfyui()
  time.sleep(15)

  redis_uri = os.environ.get('REDIS_URI')
  while True:
    time.sleep(15)
    try:
      redis_client = redis.from_url(redis_uri, decode_responses=True)
      task = redis_client.rpop('taskQueue')
      redis_client.close()

      if task:
        task = json.loads(task)
        comfyUI.run_task(task)
    except Exception as e:
      print(e)

if __name__ == "__main__":
  main()