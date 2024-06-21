import json
import os
from comfyapp import run_comfyui_server, run_task
import redis
import time
import sys

def main():

  # get the port from the first command line
  port = sys.argv[1]
  run_comfyui_server(port)
  time.sleep(15)

  redis_uri = os.environ.get('REDIS_URI')
  taskQueue = os.environ.get('TASK_QUEUE')
  while True:
    time.sleep(15)
    try:
      redis_client = redis.from_url(redis_uri, decode_responses=True)
      task = redis_client.rpop(taskQueue)
      redis_client.close()

      if task:
        task = json.loads(task)
        run_task(task, port)
    except Exception as e:
      print(e)

if __name__ == "__main__":
  main()