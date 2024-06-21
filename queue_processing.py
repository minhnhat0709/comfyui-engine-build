import json
from comfyapp import ComfyUI
import redis
import time

def main():
  comfyUI = ComfyUI()
  comfyUI.prepare_comfyui()
  time.sleep(15)

  redis_uri = 'rediss://default:AVNS_p5SxXC8sjRJE8JkNqB9@task-queue-minhnhatdo0709-a715.a.aivencloud.com:17468'
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