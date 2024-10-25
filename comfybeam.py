

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

from beam import Volume, endpoint, Image, task_queue, function
import eliai
from eliai import supabase
from lora_manager import load_loras
from helpers import connect_to_local_server, download_to_comfyui, get_images

# comfyui_commit_sha = "1900e5119f70d6db0677fe91194050be3c4476c4"
comfyui_commit_sha = "c6812947e98eb384250575d94108d9eb747765d9"

image = (
    Image(
        base_image="pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime",
        python_version="python3.12",
    )
    .add_commands(["apt-get update -y", "apt-get install neovim -y", "apt-get update && apt-get install git ffmpeg libsm6 libxext6 git-lfs -y"])
    .add_commands([
        "cd /root && git init .",
        "cd /root && git remote add --fetch origin https://github.com/comfyanonymous/ComfyUI",
        f"cd /root && git checkout {comfyui_commit_sha}",
        "cd /root && pip install  -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu121",
    ])
    .add_commands([
        "git-lfs install",
        "git clone https://huggingface.co/QQGYLab/ELLA /root/ELLA",
        "mkdir /root/models/ella_encoder && cp -r /root/ELLA/models--google--flan-t5-xl--text_encoder /root/models/ella_encoder",
        "mkdir /root/models/ella && cp /root/ELLA/ella-sd1.5-tsc-t5xl.safetensors /root/models/ella/ella-sd1.5-tsc-t5xl.safetensors",
    ])
    .add_python_packages(["httpx", "tqdm", "websocket-client", "boto3", "supabase", "flask", "cupy-cuda12x", "Pillow"])
)


    

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



MODELS_VOLUME = "./models"
LOCALFILES_VOLUME = "./localfiles"

@function(cpu=1, memory=2, volumes=[Volume(name="models", mount_path=MODELS_VOLUME), Volume(name="localfiles", mount_path=LOCALFILES_VOLUME)])
def download_ella():
    # Command to create directory and copy files
    # commands = [
    #     "git-lfs install",
    #     "git clone https://huggingface.co/QQGYLab/ELLA /root/ELLA",
    #     "cp -r /root/ELLA/models--google--flan-t5-xl--text_encoder /volumes/models/ella_encoder",
    #     "cp /root/ELLA/ella-sd1.5-tsc-t5xl.safetensors /volumes/models/models/ella/ella-sd1.5-tsc-t5xl.safetensors"
    # ]

    # for command in commands:
    #     subprocess.run(command, shell=True, check=True)
    return {"status": "success"}


def download_models():
    shutil.copyfile("./localfiles/model.json", pathlib.Path(__file__).parent / "model.json")
    download_files(filter='node')

    shutil.copyfile("./localfiles/controlnet.jpg", "/root/input/controlnet.jpg")
    shutil.copyfile("./localfiles/extra_model_paths.yaml", "/root/extra_model_paths.yaml")

    shutil.copyfile("./localfiles/workflow_api.json", pathlib.Path(__file__).parent / "workflow_api.json")
    shutil.copyfile("./localfiles/workflow_api_inpaint.json", pathlib.Path(__file__).parent / "workflow_api_inpaint.json")
    shutil.copyfile("./localfiles/workflow_api_flux_upscale.json", pathlib.Path(__file__).parent / "workflow_api_flux_upscale.json")
    shutil.copyfile("./localfiles/workflow_api_upscale.json", pathlib.Path(__file__).parent / "workflow_api_upscale.json")

    subprocess.run(["python", "/root/custom_nodes/ComfyUI-Impact-Pack/install.py"], check=True)

@task_queue(
    cpu=1.0,
    memory=6,
    gpu="RTX4090",
    on_start=download_models,
    image=image,
    keep_warm_seconds=30,
    volumes=[Volume(name="models", mount_path=MODELS_VOLUME), Volume(name="localfiles", mount_path=LOCALFILES_VOLUME)],
)
def run(**inputs):
    item = None
    try:
        run_comfyui_server(port=8189)

        item = inputs
        run_task(item)
    except Exception as e:
        print(e)
    return {'status': 200}


# if __name__ == "__main__":
#     download_ella()



# @function(cpu="100m", memory="100Mi")  # Each function runs on 100 millicores of CPU
# def square(x):
#     sum = 0

#     for i in range(x):
#         sum += i**2

#     return {"sum": sum}


# def main():
#     print(square.local(x=10))
#     print(square.remote(x=10))

#     # Run a remote container for every item in list
#     for i in square.map(range(5)):
#         print(i)


# if __name__ == "__main__":
#     main()