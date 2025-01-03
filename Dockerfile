FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime as base

RUN apt-get update && apt-get install lsof ffmpeg libsm6 libxext6 wget -y
RUN apt-get install git git-lfs -y

RUN cd /root && git init . && \
    cd /root && git remote add --fetch origin https://github.com/comfyanonymous/ComfyUI && \
    cd /root && git checkout 0d4e29f13fafb8fc003a213bb38d4ef4e4e6aa8a && \
    cd /root && pip install  -r requirements.txt

RUN git-lfs install && git clone https://huggingface.co/QQGYLab/ELLA /root/ELLA && \
    mkdir /root/models/ella_encoder && cp -r /root/ELLA/models--google--flan-t5-xl--text_encoder /root/models/ella_encoder && \
    mkdir /root/models/ella && cp /root/ELLA/ella-sd1.5-tsc-t5xl.safetensors /root/models/ella/ella-sd1.5-tsc-t5xl.safetensors

RUN pip install modal httpx tqdm websocket-client boto3 supabase flask cupy-cuda12x redis Pillow waitress

# COPY model.json /root/model.json
# COPY helpers.py /root/helpers.py



COPY . /root
COPY ./controlnet.jpg /root/input/controlnet.jpg
COPY ./SD_StandardNoise.png /root/input/SD_StandardNoise.png

# COPY queue_processing.py /root/custom_nodes/eliai/prestartup_script.py


WORKDIR /root
# RUN python -c "from comfyapp import download_files; download_files(filter='node');"
# RUN python "/root/custom_nodes/ComfyUI-Impact-Pack/install.py"

COPY start.sh /root/start.sh
RUN chmod +x /root/start.sh
ENTRYPOINT ["/root/start.sh"]



