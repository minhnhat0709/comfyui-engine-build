import json
import os
import threading
from task_runner import run_task
import redis
import time
import sys

# from comfy.cli_args import args

def main():

  #get the port from the first command line
  port = sys.argv[1]
  # run_comfyui_server(port)
  time.sleep(15)

  # port = args.port

  redis_uri = os.environ.get('REDIS_URI')
  taskQueue = os.environ.get('TASK_QUEUE')
  redis_client = redis.from_url(redis_uri, decode_responses=True)

  try:
      while True:
          time.sleep(1)
          try:
              task = redis_client.rpop(taskQueue)

              if task:
                  task = json.loads(task)
                  run_task(task, port)
          except Exception as e:
              print(f"Error processing task: {e}")
  except KeyboardInterrupt:
      print("Shutting down gracefully...")
  finally:
      redis_client.close()

def runQueue():
    #Create a background thread
    t1 = threading.Thread(target=main)
    #Background thread will finish with the main program
    t1.daemon = True
    #Start YourLedRoutine() in a separate thread
    t1.start()

if __name__ == "__main__":
    main()