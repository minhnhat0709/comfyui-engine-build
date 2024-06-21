python -c "from comfyapp import download_files; download_files();"

while true; do
	if ! lsof -i:5001 -sTCP:LISTEN > /dev/null
	then
    		python ./queue_processing.py 5001 > /engine_1.txt 2>&1 &
	fi
  sleep 1m
	if ! lsof -i:5002 -sTCP:LISTEN > /dev/null
	then
    		python ./queue_processing.py 5002 > /engine_2.txt 2>&1 &
	fi
	
	sleep 1m
done