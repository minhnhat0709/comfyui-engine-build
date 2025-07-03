FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime

RUN apt-get update && apt-get install lsof ffmpeg libsm6 libxext6 wget -y
RUN apt-get install git git-lfs -y

RUN cd /root && git init . && \
    cd /root && git remote add --fetch origin https://github.com/comfyanonymous/ComfyUI && \
    cd /root && git checkout 094306b626e9cf505690c5d8b445032b3b8a36fa && \
    cd /root && pip install --no-cache-dir  -r requirements.txt

# RUN rm -rf /root/models

# RUN git-lfs install && git clone https://huggingface.co/QQGYLab/ELLA /root/ELLA && \
#     mkdir /root/models/ella_encoder && cp -r /root/ELLA/models--google--flan-t5-xl--text_encoder /root/models/ella_encoder && \
#     mkdir /root/models/ella && cp /root/ELLA/ella-sd1.5-tsc-t5xl.safetensors /root/models/ella/ella-sd1.5-tsc-t5xl.safetensors &&\
#     rm -rf /root/ELLA

# ENV PATH="/venv/main/bin:$PATH"
RUN pip install --upgrade --ignore-installed --no-cache-dir uvicorn modal==0.73.100 httpx tqdm websocket-client boto3==1.35.92 supabase flask redis Pillow waitress onnxruntime-gpu 

# COPY model.json /root/model.json
# COPY helpers.py /root/helpers.py



COPY . /root
COPY ./controlnet.jpg /root/input/controlnet.jpg
# COPY ./SD_StandardNoise.png /root/input/SD_StandardNoise.png

# COPY queue_processing.py /root/custom_nodes/eliai/prestartup_script.py


WORKDIR /root
RUN python -c "from comfyapp import download_files; download_files(filter='node');"
# RUN python "/root/custom_nodes/ComfyUI-Impact-Pack/install.py"


COPY start.sh /root/start.sh
RUN chmod +x /root/start.sh
ENTRYPOINT ["/root/start.sh"]



