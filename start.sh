#!/bin/bash
python -c "from comfyapp import download_files; download_files(filter='model');"

wget -O workflow_api.json https://raw.githubusercontent.com/minhnhat0709/comfyui-engine-build/main/workflow_api.json
wget -O workflow_api_upscale.json https://raw.githubusercontent.com/minhnhat0709/comfyui-engine-build/main/workflow_api_upscale.json
wget -O workflow_api_inpaint.json https://raw.githubusercontent.com/minhnhat0709/comfyui-engine-build/main/workflow_api_inpaint.json
wget -O comfyapp.py https://raw.githubusercontent.com/minhnhat0709/comfyui-engine-build/main/comfyapp.py

while true; do
	if ! lsof -i:5001 -sTCP:LISTEN > /dev/null
	then
    		python ./main.py --dont-print-server --listen --port 5001 > /engine_1.txt 2>&1 &
	fi
  sleep 1m
	if ! lsof -i:5002 -sTCP:LISTEN > /dev/null
	then
    		python ./main.py --dont-print-server --listen --port 5002 > /engine_2.txt 2>&1 &
	fi
	
	sleep 1m
done

#docker run -it --gpus all -e AWS_ENDPOINT="https://2c4e16b2cfe75a3201f2f7638084e66b.r2.cloudflarestorage.com" -e AWS_ACCESS_KEY_ID=445b3a76828604585e2f38f49b39188b -e AWS_SECRET_ACCESS_KEY=9d5f008e8be8a9990a6cff7c6a1c78fc6498787a022cb0ea759cbd0af30c1848 -e STORAGE_DOMAIN="https://eliai-server.eliai.vn/" -e BUCKET_NAME="eliai-server" -e SUPABASE_URL="https://rtfoijxfymuizzxzbnld.supabase.co" -e SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0Zm9panhmeW11aXp6eHpibmxkIiwicm9sZSI6ImFub24iLCJpYXQiOjE2OTY1Nzc4MTQsImV4cCI6MjAxMjE1MzgxNH0.ChbqzCyTnUkrZ8VMie8y9fpu0xXB07fdSxVrNF9_psE -e REDIS_URI=rediss://default:AVNS_p5SxXC8sjRJE8JkNqB9@task-queue-minhnhatdo0709-a715.a.aivencloud.com:17468 -e TASK_QUEUE=test --name eliai-engine -d --mount source=engine-models,target=/root/models minhnhatdo/eliai-comfy-engine:1.1.6