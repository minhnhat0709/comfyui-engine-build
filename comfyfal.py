import fal
import fal.toolkit
from fal.container import ContainerImage
from fal.toolkit import Image
 
from pydantic import BaseModel, Field


import datetime
import glob
import json
import os
import pathlib
import random
import shutil
import subprocess
import threading
from typing import Dict

import eliai
from eliai import supabase
from lora_manager import load_loras
from helpers import connect_to_local_server, download_to_comfyui, get_images

# comfyui_commit_sha = "1900e5119f70d6db0677fe91194050be3c4476c4"
comfyui_commit_sha = "c6812947e98eb384250575d94108d9eb747765d9"


    

def remove_all_files_and_dirs_in_folder(folder_path):
    # Get a list of all files and directories in the folder
    items = glob.glob(os.path.join(folder_path, '*'))
    
    for item in items:
        try:
            if os.path.isfile(item) and item != "/root/input/controlnet.jpg":
                os.remove(item)
                print(f"Removed file {item}")
            elif os.path.isdir(item):
                shutil.rmtree(item)
                print(f"Removed directory {item}")
        except Exception as e:
            print(f"Error removing {item}: {e}")
def remove_temp_file(list_file_name):
    for item in list_file_name:
        try:
            os.remove("/root/input/" + item)
            print(f"Removed file {item}")
        except Exception as e:
            print(f"File {item} not found. Skipping.")

def run_comfyui_server( port=8188):
        cmd = f"python main.py --dont-print-server --listen --port {port}"
        subprocess.Popen(cmd, shell=True)

def workflow_run(workflow_data, task_id, user_id, seed, port=8189):
        # send requests to local headless ComfyUI server (on port 8189)
        try:
            
            server_address = f"127.0.0.1:{port}"
            ws = connect_to_local_server(server_address)
            images = get_images(ws, workflow_data, server_address)
            # eliai.image_uploading(images=images, seed=seed, task_id=task_id, user_id=user_id)
            ws.close()  # close the websocket
            
            # background_thread = threading.Thread(target=eliai.image_uploading, args=(images, seed, task_id, user_id))
            # background_thread.start()

            eliai.image_uploading(images, seed, task_id, user_id)
        except Exception as e:
            raise e
        
        # remove_all_files_and_dirs_in_folder("/root/input")
        
        return

def create_sketch2img_workflow(item, is_edit = False):
    preprocessor_map = {
      "control_v11p_sd15_canny_fp16.safetensors": "CannyEdgePreprocessor",
      "control_v11p_sd15_depth_fp16.safetensors": "DepthAnythingPreprocessor",
      "control_v11p_sd15_lineart_fp16.safetensors": "LineArtPreprocessor",
      "control_v11p_sd15_mlsd_fp16.safetensors": "M-LSDPreprocessor",
      "control_v11p_sd15_openpose_fp16.safetensors": "OpenposePreprocessor",
      "control_v11p_sd15_scribble_fp16.safetensors": "Scribble_XDoG_Preprocessor",
      "control_v11p_sd15_seg_fp16.safetensors": "SAMPreprocessor",
      "control_v11u_sd15_tile_fp16.safetensors": "TilePreprocessor",
    }
    workflow_data = json.loads(
        (pathlib.Path(__file__).parent / ("workflow_api_inpaint.json" if is_edit else "workflow_api.json")).read_text()
    )

    if item.get("input_image_url") is not None:
        download_to_comfyui(item["input_image_url"], "input")
        workflow_data["219"]["inputs"]["strength"] = item["control_strength"]
        workflow_data["143"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
        workflow_data["216"]["inputs"]["control_net_name"] = item["control_net_name"]
        workflow_data["183"]["inputs"]["preprocessor"] = preprocessor_map[item["control_net_name"]]
    else:
        workflow_data["219"]["inputs"]["strength"] = 0

    

    # insert the prompt
    workflow_data["137"]["inputs"]["text"] = item["prompt"]
    workflow_data["140"]["inputs"]["text"] = item["negative_prompt"]
    
    if item.get("loras") is not None and len(item["loras"]) > 0:
        load_loras(item["loras"])
        print("lora_loaded")
        for index, lora in enumerate(item["loras"]):
            # download_to_comfyui(lora["download_url"], "models/loras", lora["name"])
            workflow_data["159"]["inputs"][f"lora_0{index+1}"] = lora["name"]
            workflow_data["159"]["inputs"][f"strength_0{index+1}"] = lora["weight"]
        workflow_data["137"]["inputs"]["text_clip"] = item["lora_triggers"]

    if is_edit == False:
        workflow_data["134"]["inputs"]["height"] = item["height"]
        workflow_data["134"]["inputs"]["width"] = item["width"]
        workflow_data["275"]["inputs"]["seed"] = item["seed"]
        workflow_data["134"]["inputs"]["batch_size"] = item["batch_size"]
    else:
        workflow_data["232"]["inputs"]["image_gen_height"] = item["height"] * 1.5
        workflow_data["232"]["inputs"]["image_gen_width"] = item["width"] * 1.5

        workflow_data["230"]["inputs"]["denoise"] = item["denoise"]
        workflow_data["230"]["inputs"]["seed"] = item["seed"]
        workflow_data["243"]["inputs"]["amount"] = item["batch_size"]


        download_to_comfyui(item["mask"], "input")
        workflow_data["231"]["inputs"]["image"] = item["mask"].split("/")[-1]
        download_to_comfyui(item["image"], "input")
        workflow_data["234"]["inputs"]["image"] = item["image"].split("/")[-1]
        

    
    

    

    

    return workflow_data

def create_upscale_workflow(item, isFlux = False):
    download_to_comfyui(item["input_image_url"], "input")
    
    workflow_data = json.loads(
        (pathlib.Path(__file__).parent / ("workflow_api_flux_upscale.json" if isFlux else "workflow_api_upscale.json")).read_text()
    )

    # insert the prompt
    # workflow_data["99"]["inputs"]["text"] = item["prompt"]
    if isFlux:
        workflow_data["59"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
        workflow_data["72"]["inputs"]["denoise"] = item["denoising_strength"]
    else:
        workflow_data["97"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
        workflow_data["96"]["inputs"]["denoise"] = item["denoising_strength"]
    

    return workflow_data
def run_task( task, port=8189):
    try:
        item = task

        supabase.table("Tasks").update({
            "status": "processing",
        }).eq("task_id", item['task_id']).execute()

        if item["seed"] == 0:
            item["seed"] = random.randint(1,4294967294)
        
        # download input images to the container
        if "upscale" in item["type"]:
            workflow_data = create_upscale_workflow(item=item, isFlux=item["type"] == "flux_upscale")
        else:
            workflow_data = create_sketch2img_workflow(item=item, is_edit=item["type"] == "edit")
        
        
        
        print("ready to run")
        workflow_run(workflow_data, item["task_id"], item["user_id"], item["seed"], port)
        remove_temp_file([item.get("input_image_url", "").split("/")[-1], item.get("mask", "").split("/")[-1], item.get("image", "").split("/")[-1]])
    except Exception as e:
        print(e)
        if item:
            supabase.table("Tasks").update({
                "status": "failed",
                "finished_at": datetime.datetime.utcnow().isoformat()
            }).eq("task_id", item['task_id']).execute()
def download_files(filter="node, model"):
    models = json.loads(
        (pathlib.Path(__file__).parent / "model.json").read_text()
    )
    for m in models:
        if m["url"].endswith(".git") and "node" not in filter:
            continue
        if not m["url"].endswith(".git") and "model" not in filter:
            continue
        download_to_comfyui(m["url"], m["path"],git_sha=m.get("git_sha", None))
 
dockerfile_str = """
FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime as base

RUN apt-get update && apt-get install lsof ffmpeg libsm6 libxext6 wget -y
RUN apt-get install git git-lfs -y

RUN cd /root && git init . && \
    cd /root && git remote add --fetch origin https://github.com/comfyanonymous/ComfyUI && \
    cd /root && git checkout c6812947e98eb384250575d94108d9eb747765d9 && \
    cd /root && pip install  -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu121

RUN git-lfs install && git clone https://huggingface.co/QQGYLab/ELLA /root/ELLA && \
    mkdir /root/models/ella_encoder && cp -r /root/ELLA/models--google--flan-t5-xl--text_encoder /root/models/ella_encoder && \
    mkdir /root/models/ella && cp /root/ELLA/ella-sd1.5-tsc-t5xl.safetensors /root/models/ella/ella-sd1.5-tsc-t5xl.safetensors

RUN pip install modal httpx tqdm websocket-client boto3 supabase flask cupy-cuda12x redis Pillow

# COPY model.json /root/model.json
# COPY helpers.py /root/helpers.py



COPY . /root
COPY ./controlnet.jpg /root/input/controlnet.jpg
COPY ./SD_StandardNoise.png /root/input/SD_StandardNoise.png

COPY queue_processing.py /root/custom_nodes/eliai/prestartup_script.py


WORKDIR /root
RUN python -c "from comfyapp import download_files; download_files(filter='node');"
RUN python "/root/custom_nodes/ComfyUI-Impact-Pack/install.py"
"""
 
 
class Input(BaseModel):
    prompt: str = Field(
        description="The prompt to generate an image from.",
        examples=[
            "A cinematic shot of a baby racoon wearing an intricate italian priest robe.",
        ],
    )
 
 
class Output(BaseModel):
    image: Image = Field(
        description="The generated image.",
    )
 
 
class FalModel(
    fal.App,
    image=ContainerImage.from_dockerfile_str(dockerfile_str),
    kind="container",
  ):
    machine_type = "GPU"
 
    def setup(self) -> None:
        download_files(filter='model')
        subprocess.run(["python", "/root/custom_nodes/ComfyUI-Impact-Pack/install.py"], check=True)

        run_comfyui_server(port=8189)

        # import torch
        # from diffusers import AutoPipelineForText2Image
 
        # # Load SDXL
        # self.pipeline = AutoPipelineForText2Image.from_pretrained(
        #     "stabilityai/stable-diffusion-xl-base-1.0",
        #     torch_dtype=torch.float16,
        #     variant="fp16",
        # )
        # self.pipeline.to("cuda")
 
        # # Apply fal's spatial optimizer to the pipeline.
        # self.pipeline.unet = fal.toolkit.optimize(self.pipeline.unet)
        # self.pipeline.vae = fal.toolkit.optimize(self.pipeline.vae)
 
        # # Warm up the model.
        # self.pipeline(
        #     prompt="a cat",
        #     num_inference_steps=30,
        # )
 
    @fal.endpoint("/")
    def text_to_image(self, input: Input) -> Output:
        try:
            run_comfyui_server(port=8189)

            item = input.model_dump()
            run_task(item)
        except Exception as e:
            print(e)
        return {'status': 200}
        return Output(image=Image.from_pil(image))