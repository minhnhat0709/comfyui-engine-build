#!/bin/bash

# Initialize directories and PID files
mkdir -p /root/temp /root/output /var/run
QUEUE_PID_1="/var/run/queue_proc_5001.pid"
QUEUE_PID_2="/var/run/queue_proc_5002.pid"

# Function to check and restart queue process if needed
check_queue_process() {
    local PORT=$1
    local PID_FILE="/var/run/queue_proc_${PORT}.pid"
    local LOG_FILE="/queue_processing_${PORT}.txt"

    # Ensure main server is running on the specified port
    if lsof -i:$PORT -sTCP:LISTEN > /dev/null; then
        if [ -f "$PID_FILE" ]; then
            local STORED_PID
            STORED_PID=$(cat "$PID_FILE" 2>/dev/null)
            if [ -z "$STORED_PID" ]; then
                echo "[$(date)] PID file for port $PORT is empty or invalid"
                rm -f "$PID_FILE"
            else
                # Check if the stored PID is valid and running
                if ps -p "$STORED_PID" -o pid=,comm=,args= 2>/dev/null | grep -q "python.*queue_processing.py $PORT"; then
                    echo "[$(date)] Process $STORED_PID is running correctly for port $PORT"
                    return 0
                else
                    echo "[$(date)] Stored PID $STORED_PID is not valid or the process is not running as expected"
                    rm -f "$PID_FILE"
                fi
            fi
        fi
        
        echo "[$(date)] Starting new queue process for port $PORT"
        
        # Kill any lingering Python processes for this port
        pkill -f "python.*queue_processing.py $PORT" 2>/dev/null || true

        # Start the process
        cd "$(dirname "$(readlink -f "$0")")" || exit 1
        nohup python3 ./queue_processing.py "$PORT" > "$LOG_FILE" 2>&1 &
        local NEW_PID=$!
        
        # Wait briefly and validate the new process
        sleep 2
        if ps -p "$NEW_PID" -o pid=,comm=,args= 2>/dev/null | grep -q "python.*queue_processing.py $PORT"; then
            echo "[$(date)] Successfully started queue process for port $PORT with PID $NEW_PID"
            echo "$NEW_PID" > "$PID_FILE"
            
            # Optional: Adjust process priority
            renice -n -5 "$NEW_PID" 2>/dev/null || true
        else
            echo "[$(date)] Failed to start queue process for port $PORT"
            echo "[$(date)] Last few lines of the log file:"
            tail -n 5 "$LOG_FILE"
        fi
    else
        echo "[$(date)] Main server is not running on port $PORT"
    fi
}


# Cleanup any stale processes and PID files on startup
echo "[$(date)] Cleaning up stale processes..."
pkill -f "python.*queue_processing.py" || true
rm -f "$QUEUE_PID_1" "$QUEUE_PID_2"

# Download initial files
python -c "from comfyapp import download_files; download_files(filter='model', skip_list=['https://huggingface.co/Kijai/flux-fp8/resolve/main/flux1-dev-fp8.safetensors', 'https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors']);"
# git-lfs install && git clone https://huggingface.co/QQGYLab/ELLA /root/ELLA 
# mkdir /root/models/ella_encoder && cp -r /root/ELLA/models--google--flan-t5-xl--text_encoder /root/models/ella_encoder 
# mkdir /root/models/ella && cp /root/ELLA/ella-sd1.5-tsc-t5xl.safetensors /root/models/ella/ella-sd1.5-tsc-t5xl.safetensors 
# rm -rf /root/ELLA

# wget -O /root/workflow_api.json https://raw.githubusercontent.com/minhnhat0709/comfyui-engine-build/main/workflow_api.json
# wget -O /root/workflow_api_inpaint.json https://raw.githubusercontent.com/minhnhat0709/comfyui-engine-build/main/workflow_api_inpaint.json
# wget -O /root/workflow_api_upscale.json https://raw.githubusercontent.com/minhnhat0709/comfyui-engine-build/main/workflow_api_upscale.json
# wget -O /root/workflow_api_controlnet.json https://raw.githubusercontent.com/minhnhat0709/comfyui-engine-build/main/workflow_api_controlnet.json

while true; do
    # Check and start main server for port 5001
    if ! lsof -i:5001 -sTCP:LISTEN > /dev/null; then
        echo "[$(date)] Starting main server on port 5001"
        nohup python3 ./main.py --dont-print-server --listen --port 5001 > /engine_1.txt 2>&1 &
        sleep 15  # Give the server time to start
    fi
    
    # Check queue process for port 5001
    check_queue_process 5001
    
    
    # Check and start main server for port 5002
    if ! lsof -i:5002 -sTCP:LISTEN > /dev/null; then
        echo "[$(date)] Starting main server on port 5002"
        nohup python3 ./main.py --dont-print-server --listen --port 5002 > /engine_2.txt 2>&1 &
        sleep 15  # Give the server time to start
    fi
    
    # Check queue process for port 5002
    check_queue_process 5002
    

    
    if ! lsof -i:5003 -sTCP:LISTEN > /dev/null; then
        echo "[$(date)] Starting utility server on port 5003"
        nohup python controlnet_preprocess_flask.py  &
        sleep 5  # Give the server time to start
    fi
    # Cleanup old files (only if directories exist)
    [ -d /root/output ] && find /root/output -type f -mmin +240 -execdir rm -- '{}' \;
    [ -d /root/temp ] && find /root/temp -type f -mmin +240 -execdir rm -- '{}' \;

    sleep 5s
done

#docker run -it --gpus all -e AWS_ENDPOINT="https://2c4e16b2cfe75a3201f2f7638084e66b.r2.cloudflarestorage.com" -e AWS_ACCESS_KEY_ID=445b3a76828604585e2f38f49b39188b -e AWS_SECRET_ACCESS_KEY=9d5f008e8be8a9990a6cff7c6a1c78fc6498787a022cb0ea759cbd0af30c1848 -e STORAGE_DOMAIN="https://eliai-server.eliai.vn/" -e BUCKET_NAME="eliai-server" -e SUPABASE_URL="https://rtfoijxfymuizzxzbnld.supabase.co" -e SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0Zm9panhmeW11aXp6eHpibmxkIiwicm9sZSI6ImFub24iLCJpYXQiOjE2OTY1Nzc4MTQsImV4cCI6MjAxMjE1MzgxNH0.ChbqzCyTnUkrZ8VMie8y9fpu0xXB07fdSxVrNF9_psE -e REDIS_URI=rediss://default:AVNS_p5SxXC8sjRJE8JkNqB9@task-queue-minhnhatdo0709-a715.a.aivencloud.com:17468 -e TASK_QUEUE=test --name eliai-engine -d --mount source=engine-models,target=/root/models -p 5003:5003 minhnhatdo/eliai-comfy-engine:1.3.9
#docker run --rm -p 5001:1234 verb/socat TCP-LISTEN:1234,fork TCP-CONNECT:172.17.0.2:5005