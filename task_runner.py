import random
import datetime
import json
import pathlib
import os
import json
import threading
from helpers import connect_to_local_server, download_to_comfyui, get_images
from eliai import supabase

import eliai
from lora_manager import load_loras
def workflow_run(workflow_data, task_id, user_id, seed, port=8189, schema="public"):
        # send requests to local headless ComfyUI server (on port 8189)
        try:
            
            server_address = f"127.0.0.1:{port}"
            ws = connect_to_local_server(server_address)
            images = get_images(ws, workflow_data, server_address)
            # eliai.image_uploading(images=images, seed=seed, task_id=task_id, user_id=user_id)
            ws.close()  # close the websocket
            
            # background_thread = threading.Thread(target=eliai.image_uploading, args=(images, seed, task_id, user_id, schema))
            # background_thread.start()

            eliai.image_uploading(images, seed, task_id, user_id, schema)
        except Exception as e:
            raise e
        
        # remove_all_files_and_dirs_in_folder("/root/input")
        
        return

def create_sketch2img_workflow(item, is_edit = False, is_test = False):
    print("creating workflow")
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

    def create_sketch2img_workflow_inpaint(item):
        workflow_file = "workflow_api_inpaint.json"
        workflow_data = json.loads(
            (pathlib.Path(__file__).parent / workflow_file).read_text()
        )
        print("downloading input image")
        if item.get("input_image_url") is not None:
            download_to_comfyui(item["input_image_url"], "input")
            workflow_data["219"]["inputs"]["strength"] = item["control_strength"]
            workflow_data["143"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
            workflow_data["216"]["inputs"]["control_net_name"] = item["control_net_name"]
            workflow_data["183"]["inputs"]["preprocessor"] = preprocessor_map[item["control_net_name"]]
        else:
            workflow_data["219"]["inputs"]["strength"] = 0
            workflow_data["300"]["inputs"]["strength"] = 0

            print("inserting prompt")
        # insert the prompt
        workflow_data["278"]["inputs"]["text_positive"] = item["prompt"]
        workflow_data["278"]["inputs"]["text_negative"] = item["negative_prompt"]

        print("inserting lora")
        if item.get("loras") is not None and len(item["loras"]) > 0:
            load_loras(item["loras"])
            print("lora_loaded")
            for index, lora in enumerate(item["loras"]):
                # download_to_comfyui(lora["download_url"], "models/loras", lora["name"])
                workflow_data["159"]["inputs"][f"lora_0{index+2}"] = lora["name"]
                workflow_data["159"]["inputs"][f"strength_0{index+2}"] = lora["weight"]
                workflow_data["278"]["inputs"]["text_positive"] += ", " + item["lora_triggers"]


        workflow_data["230"]["inputs"]["denoise"] = item["denoise"]
        workflow_data["230"]["inputs"]["seed"] = item["seed"]

        print("downloading mask")
        download_to_comfyui(item["mask"], "input")
        workflow_data["231"]["inputs"]["image"] = item["mask"].split("/")[-1]
        print("downloading image")
        download_to_comfyui(item["image"], "input")
        workflow_data["234"]["inputs"]["image"] = item["image"].split("/")[-1]

        return workflow_data
    def create_sketch2img_workflow_basic(item):
        workflow_file = "workflow_api.json"
        workflow_data = json.loads(
            (pathlib.Path(__file__).parent / workflow_file).read_text()
        )
        print("downloading input image")
        if item.get("input_image_url") is not None:
            download_to_comfyui(item["input_image_url"], "input")
            workflow_data["219"]["inputs"]["strength"] = item["control_strength"]
            workflow_data["143"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
            workflow_data["216"]["inputs"]["control_net_name"] = item["control_net_name"]
            workflow_data["183"]["inputs"]["preprocessor"] = preprocessor_map[item["control_net_name"]]
        else:
            workflow_data["219"]["inputs"]["strength"] = 0

            print("inserting prompt")
        # insert the prompt
        workflow_data["298"]["inputs"]["text_positive"] = item["prompt"]
        workflow_data["298"]["inputs"]["text_negative"] = item["negative_prompt"]

        print("inserting lora")
        if item.get("loras") is not None and len(item["loras"]) > 0:
            load_loras(item["loras"])
            print("lora_loaded")
            for index, lora in enumerate(item["loras"]):
                # download_to_comfyui(lora["download_url"], "models/loras", lora["name"])
                workflow_data["159"]["inputs"][f"lora_0{index+2}"] = lora["name"]
                workflow_data["159"]["inputs"][f"strength_0{index+2}"] = lora["weight"]
                workflow_data["298"]["inputs"]["text_positive"] += ", " + item["lora_triggers"]
        
        workflow_data["134"]["inputs"]["height"] = item["height"]
        workflow_data["134"]["inputs"]["width"] = item["width"]

        workflow_data["275"]["inputs"]["seed"] = item["seed"]
        workflow_data["286"]["inputs"]["seed"] = item["seed"]
        
        workflow_data["134"]["inputs"]["batch_size"] = item["batch_size"]
        return workflow_data
    
    if is_edit:
        workflow_data = create_sketch2img_workflow_inpaint(item)
    else:
        workflow_data = create_sketch2img_workflow_basic(item)
    

        
        

    
    

    

    

    return workflow_data

def create_upscale_workflow(item, isFlux = False):
    download_to_comfyui(item["input_image_url"], "input")

    def create_upscale_workflow_flux(item):
        workflow_data = json.loads(
            (pathlib.Path(__file__).parent / "workflow_api_flux_upscale.json").read_text()
        )
        workflow_data["59"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
        workflow_data["72"]["inputs"]["denoise"] = item["denoising_strength"]
        return workflow_data
    
    def create_upscale_workflow_basic(item):
        workflow_data = json.loads(
            (pathlib.Path(__file__).parent / "workflow_api_upscale_basic.json").read_text()
        )
        workflow_data["1"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
        return workflow_data

    def create_upscale_workflow_advanced(item):
        workflow_data = json.loads(
            (pathlib.Path(__file__).parent / "workflow_api_upscale_advanced.json").read_text()
        )
        workflow_data["97"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
        workflow_data["235"]["inputs"]["denoise"] = item["denoising_strength"]
        return workflow_data
    

    if item["type"] == "flux_upscale":
        workflow_data = create_upscale_workflow_flux(item)
    elif item["type"] == "ultimate_upscale":
        workflow_data = create_upscale_workflow_advanced(item)
    else:
        workflow_data = create_upscale_workflow_basic(item)
    

    return workflow_data

def remove_temp_file(list_file_name):
    for item in list_file_name:
        try:
            os.remove("/root/input/" + item)
            print(f"Removed file {item}")
        except Exception as e:
            print(f"File {item} not found. Skipping.")


def run_task( task, port=8189):
    try:
        item = task

        schema = 'public';
        if item.get("is_new_version") is True:
            schema = 'new_version';
        
        supabase.schema(schema).table("Tasks").update({
            "status": "processing",
        }).eq("task_id", item['task_id']).execute()

        if item["seed"] == 0:
            item["seed"] = random.randint(1,4294967294)
        
        # download input images to the container
        if "upscale" in item["type"]:
            workflow_data = create_upscale_workflow(item=item, isFlux=item["type"] == "flux_upscale")
        else:
            workflow_data = create_sketch2img_workflow(item=item, is_edit=item["type"] == "edit", is_test=item.get("is_test", False))
        
        
        
        print("ready to run")
        workflow_run(workflow_data, item["task_id"], item["user_id"], item["seed"], port, schema)
        remove_temp_file([item.get("input_image_url", "").split("/")[-1], item.get("mask", "").split("/")[-1], item.get("image", "").split("/")[-1]])
    except Exception as e:
        print(e)
        if item:
            supabase.schema(schema).table("Tasks").update({
                "status": "failed",
                "finished_at": datetime.datetime.utcnow().isoformat()
            }).eq("task_id", item['task_id']).execute()