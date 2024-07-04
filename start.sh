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