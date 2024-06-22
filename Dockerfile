FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime as base

RUN apt-get update && apt-get install -y lsof ffmpeg libsm6 libxext6 -y
RUN apt-get install git -y

RUN cd /root && git init . && \
    cd /root && git remote add --fetch origin https://github.com/comfyanonymous/ComfyUI && \
    cd /root && git checkout 1900e5119f70d6db0677fe91194050be3c4476c4 && \
    cd /root && pip install  -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu121

RUN GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/QQGYLab/ELLA /root/ELLA && \
    mkdir /root/models/ella_encoder && cp -r /root/ELLA/models--google--flan-t5-xl--text_encoder /root/models/ella_encoder

RUN pip install modal httpx tqdm websocket-client boto3 supabase flask cupy-cuda12x redis Pillow

# COPY model.json /root/model.json
# COPY helpers.py /root/helpers.py

COPY . /root

WORKDIR /root

RUN python -c "from comfyapp import download_files; download_files(filter='node');"

RUN chmod +x start.sh
ENTRYPOINT ["./start.sh"]



