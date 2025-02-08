# ---
# cmd: ["modal", "serve", "06_gpu_and_ml/comfyui/comfyapp.py"]
# deploy: true
# ---
#
# # Run ComfyUI interactively and as an API
#
# [ComfyUI](https://github.com/comfyanonymous/ComfyUI) is a no-code Stable Diffusion GUI that allows you to design and execute advanced image generation pipelines.
#
# ![example comfyui image](./comfyui.png)
#
# In this example, we show you how to
#
# 1. run ComfyUI interactively to develop workflows
#
# 2. serve a ComfyUI workflow as an API
#
# Combining the UI and the API in a single app makes it easy to iterate on your workflow even after deployment.
# Simply head to the interactive UI, make your changes, export the JSON, and redeploy the app.
#
# An alternative approach is to port your ComfyUI workflow from the JSON format to Python code.
# The Python approach further reduces inference latency by a few hundred milliseconds to a second, but introduces some extra complexity.
# You can read more about it [in this blog post](https://modal.com/blog/comfyui-prototype-to-production).
#
# ## Quickstart
#
# This example serves the [ComfyUI inpainting example workflow](https://comfyanonymous.github.io/ComfyUI_examples/inpaint/),
# which "fills in" part of an input image based on a prompt.
# For the prompt `"Spider-Man visits Yosemite, rendered by Blender, trending on artstation"`,
# on [this input image](https://raw.githubusercontent.com/comfyanonymous/ComfyUI_examples/master/inpaint/yosemite_inpaint_example.png) we got this output:
#
# ![example comfyui image](./comfyui_gen_image.jpg)
#
# 1. Stand up the ComfyUI server in development mode:
# ```bash
# modal serve 06_gpu_and_ml/comfyui/comfyapp.py
# ```
#
# 2. In another terminal, run inference:
# ```bash
# python 06_gpu_and_ml/comfyui/comfyclient.py --dev --modal-workspace your-modal-workspace --prompt "your prompt here"
# ```
# You can find your Modal workspace name by running `modal profile current`.
#
# The first inference will take a bit longer because the server will need to boot up (~20-30s).
# Successive inference calls while the server is up should take a few seconds or less.
#
# ## Setup
#
# First, we define the environment we need to run ComfyUI -- system software, Python package, etc.
#
# You can add custom checkpoints and plugins to this environment by editing the `model.json` file in this directory.

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

import modal
import eliai
from eliai import supabase
from lora_manager import load_loras
from task_runner import run_task

# comfyui_commit_sha = "1900e5119f70d6db0677fe91194050be3c4476c4"
comfyui_commit_sha = "0d4e29f13fafb8fc003a213bb38d4ef4e4e6aa8a"

comfyui_image = (  # build up a Modal Image to run ComfyUI, step by step
    modal.Image.from_registry(  # start from basic Linux with Python
        "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime",
        force_build=False
    )
    .env({
        "DEBIAN_FRONTEND":"noninteractive",
        "TZ":"Etc/UTC",
    })
    # .apt_install("git -y")
    .run_commands("apt-get update && apt-get install ffmpeg libsm6 libxext6 git git-lfs -y")
    # .run_commands("pip uninstall torch && pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121")
    .run_commands(  # install ComfyUI
        "cd /root && git init .",
        "cd /root && git remote add --fetch origin https://github.com/comfyanonymous/ComfyUI",
        f"cd /root && git checkout {comfyui_commit_sha}",
        "cd /root && pip install  -r requirements.txt",
        force_build=False
    )
    .run_commands(
        "git-lfs install",
        "git clone https://huggingface.co/QQGYLab/ELLA /root/ELLA",
        "mkdir /root/models/ella_encoder && cp -r /root/ELLA/models--google--flan-t5-xl--text_encoder /root/models/ella_encoder",
        "mkdir /root/models/ella && cp /root/ELLA/ella-sd1.5-tsc-t5xl.safetensors /root/models/ella/ella-sd1.5-tsc-t5xl.safetensors",
        force_build=False
    )
    .pip_install("httpx", "tqdm", "websocket-client", "boto3", "supabase", "flask", "cupy-cuda12x", "Pillow", force_build=False)  # add web dependencies
    .copy_local_file(  # copy over the ComfyUI model definition JSON and helper Python module
        pathlib.Path(__file__).parent / "model.json", "/root/model.json"
    )
    .copy_local_file(
        pathlib.Path(__file__).parent / "helpers.py", "/root/helpers.py"
    )
    # .copy_local_dir(
    #     pathlib.Path(__file__).parent / "models", "/root/ComfyUI/models"
    # )
)

app = modal.App(name="example-comfyui")

# Some additional code for managing ComfyUI lives in `helpers.py`.
# This includes functions like downloading checkpoints and plugins to the right directory on the ComfyUI server.
with comfyui_image.imports():
    from helpers import connect_to_local_server, download_to_comfyui, get_images

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


def download_files(filter="node, model", skip_list=[]):
    models = json.loads(
        (pathlib.Path(__file__).parent / "model.json").read_text()
    )
    for m in models:
        if m["url"] in skip_list:
            continue
        if m["url"].endswith(".git") and "node" not in filter:
            continue
        if not m["url"].endswith(".git") and "model" not in filter:
            continue
        download_to_comfyui(m["url"], m["path"],git_sha=m.get("git_sha", None))
# ## Running ComfyUI interactively and as an API on Modal
#
# Below, we use Modal's class syntax to run our customized ComfyUI environment and workflow on Modal.
#
# Here's the basic breakdown of how we do it:
# 1. We add another step to the image [`build`](https://modal.com/docs/guide/model-weights)
# with `download_models`, which adds the custom checkpoints and plugins defined in `model.json`.
# 2. We stand up a "headless" ComfyUI server with `prepare_comfyui` when our app starts.
# 3. We serve a `ui` (by decorating with `@web_server`), so that we can interactively develop our ComfyUI workflow.
# 4. We stand up an `api` with `web_endpoint`, so that we can run our workflows as a service.
#
# For more on how to run web services on Modal, check out [this guide](https://modal.com/docs/guide/webhooks).
@app.cls(
    allow_concurrent_inputs=1,
    gpu="a10g",
    image=comfyui_image,
    timeout=300,
    container_idle_timeout=60,
    mounts=[
        modal.Mount.from_local_file(
            pathlib.Path(__file__).parent / "controlnet.jpg",
            "/root/input/controlnet.jpg",
        ),
        modal.Mount.from_local_file(
            pathlib.Path(__file__).parent / "SD_StandardNoise.png",
            "/root/input/SD_StandardNoise.png",
        ),
        modal.Mount.from_local_file(
            pathlib.Path(__file__).parent / "workflow_api.json",
            "/root/workflow_api.json",
        ),
        modal.Mount.from_local_file(
            pathlib.Path(__file__).parent / "workflow_api_upscale_basic.json",
            "/root/workflow_api_upscale_basic.json",
        ),
        modal.Mount.from_local_file(
            pathlib.Path(__file__).parent / "workflow_api_upscale_advanced.json",
            "/root/workflow_api_upscale_advanced.json",
        ),
        modal.Mount.from_local_file(
            pathlib.Path(__file__).parent / "workflow_api_flux_upscale.json",
            "/root/workflow_api_flux_upscale.json",
        ),
        modal.Mount.from_local_file(
            pathlib.Path(__file__).parent / "workflow_api_inpaint.json",
            "/root/workflow_api_inpaint.json",
        ),
        # modal.Mount.from_local_file(
        #     pathlib.Path(__file__).parent / "models/loras" / "add_detail.safetensors",
        #     "/root/models/loras/add_detail.safetensors",
        # ),
        # modal.Mount.from_local_file(
        #     pathlib.Path(__file__).parent / "models/embeddings" / "UnrealisticDream.pt",
        #     "/root/models/embeddings/UnrealisticDream.pt",
        # )
    ],
    secrets=[modal.Secret.from_name("engine-secret")]
)
class ComfyUI:
    @modal.build()
    def download_models(self):
        download_files()
        subprocess.run(["python", "/root/custom_nodes/ComfyUI-Impact-Pack/install.py"], check=True)

    

    @modal.enter()
    def prepare_comfyui(self):
        # runs on a different port as to not conflict with the UI instance
        run_comfyui_server(port=8189)

    # @modal.web_server(8188, startup_timeout=30)
    # def ui(self):
    #     self._run_comfyui_server()

    @modal.method()
    def run_task_eliai(self, item):
        run_task(item)
    
    @modal.wsgi_app()
    def flask_app(self):
        from flask import Flask, request, Response
        

        web_app = Flask(__name__)

        
        @web_app.post("/run")
        def run():
            item = None
            try:
                item = request.json
                run_task(item)
                # self.run_task_eliai.spawn(item)

            except Exception as e:
                print(e)
            return Response(status=200)

        @web_app.post("/echo")
        def echo():
            return request.json

        return web_app




# ### The workflow for developing workflows
#
# When you run this script with `modal deploy 06_gpu_and_ml/comfyui/comfyapp.py`, you'll see a link that includes `ComfyUI.ui`.
# Head there to interactively develop your ComfyUI workflow. All of your custom checkpoints/plugins from `model.json` will be loaded in.
#
# To serve the workflow after you've developed it, first export it as "API Format" JSON:
# 1. Click the gear icon in the top-right corner of the menu
# 2. Select "Enable Dev mode Options"
# 3. Go back to the menu and select "Save (API Format)"
#
# Save the exported JSON to the `workflow_api.json` file in this directory.
#
# Then, redeploy the app with this new workflow by running `modal deploy 06_gpu_and_ml/comfyui/comfyapp.py` again.
#
# ## Further optimizations
#
# There is more you can do with Modal to further improve performance of your ComfyUI API endpoint.
#
# For example:
# - Apply [keep_warm](https://modal.com/docs/guide/cold-start#maintain-a-warm-pool-with-keep_warm) to the `ComfyUI` class to always have a server running
# - Cache downloaded checkpoints/plugins to a [Volume](https://modal.com/docs/guide/volumes) to avoid full downloads on image rebuilds
#
# If you're interested in building a platform for running ComfyUI workflows with dynamically-defined dependencies and workflows,
# please [reach out to us on Slack](https://modal.com/slack).
