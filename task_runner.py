import random
import datetime
import json
import pathlib
import os
import json
import threading
from helpers import connect_to_local_server, download_to_comfyui, get_images
from eliai import supabase, image_uploading

# import eliai
from lora_manager import load_loras
def workflow_run(workflow_data, task_id, user_id, seed, port=8189, schema="public"):
        # send requests to local headless ComfyUI server (on port 8189)
        try:
            
            server_address = f"127.0.0.1:{port}"
            print("starting connection")
            ws = connect_to_local_server(server_address)
            print("connected")
            images = get_images(ws, workflow_data, server_address)
            print("images received")
            # eliai.image_uploading(images=images, seed=seed, task_id=task_id, user_id=user_id)
            ws.close()  # close the websocket
            
            background_thread = threading.Thread(target=image_uploading, args=(images, seed, task_id, user_id, schema))
            background_thread.start()

            # eliai.image_uploading(images, seed, task_id, user_id, schema)
        except Exception as e:
            raise e
        
        # remove_all_files_and_dirs_in_folder("/root/input")
        
        return

def create_sketch2img_workflow(item, is_edit = False, is_test = False):
    print("creating workflow")
    preprocessor_map = {
      "canny": "CannyEdgePreprocessor",
      "depth": "DepthAnythingPreprocessor",
      "lineart": "LineArtPreprocessor",
      "mlsd": "M-LSDPreprocessor",
      "openpose": "OpenposePreprocessor",
      "scribble": "Scribble_XDoG_Preprocessor",
      "hed": "HEDPreprocessor",
      "seg": "SAMPreprocessor",
      "tile": "TilePreprocessor",
    }
    control_net_map = {
      "canny": "canny/lineart/anime_lineart/mlsd",
      "depth": "depth",
      "lineart": "canny/lineart/anime_lineart/mlsd",
      "mlsd": "canny/lineart/anime_lineart/mlsd",
      "openpose": "openpose",
      "scribble": "hed/pidi/scribble/ted",
      "hed": "hed/pidi/scribble/ted",
      "seg": "segment",
    }

    workflow_file = "./workflows/flux_sketch2img_inpaint_api.json"
    workflow_data = json.loads(
        (pathlib.Path(__file__).parent / workflow_file).read_text()
    )
    print("downloading input image")
    if item.get("input_image_url") is not None:
        download_to_comfyui(item["input_image_url"], "input")
        workflow_data["128"]["inputs"]["value"] = item["control_strength"]
        workflow_data["59"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
        workflow_data["91"]["inputs"]["type"] = control_net_map[item["control_net_name"]]
        workflow_data["90"]["inputs"]["preprocessor"] = preprocessor_map[item["control_net_name"]]
    else:
        workflow_data["128"]["inputs"]["value"] = 0
        workflow_data["156"]["inputs"]["value"] = 0

        print("inserting prompt")
    # insert the prompt
    workflow_data["127"]["inputs"]["value"] = item["prompt"]
    workflow_data["6"]["inputs"]["text"] = item["negative_prompt"]

    print("inserting lora")
    if item.get("loras") is not None and len(item["loras"]) > 0:
        load_loras(item["loras"])
        print("lora_loaded")
        for index, lora in enumerate(item["loras"]):
            # download_to_comfyui(lora["download_url"], "models/loras", lora["name"])
            workflow_data["100"]["inputs"][f"lora_0{index+2}"] = lora["name"]
            workflow_data["100"]["inputs"][f"strength_0{index+2}"] = lora["weight"]
            workflow_data["127"]["inputs"]["value"] += ", " + item.get("lora_triggers", "")
    
    # if item.get("reference_image_url") is not None:
    #     download_to_comfyui(item["reference_image_url"], "input")
    #     workflow_data["395"]["inputs"]["image"] = item["reference_image_url"].split("/")[-1]
    #     workflow_data["396"]["inputs"]["weight"] = item["reference_image_weight"]
    # else:
    #     workflow_data["396"]["inputs"]["weight"] = 0
    
    workflow_data["112"]["inputs"]["value"] = item["height"]
    workflow_data["111"]["inputs"]["value"] = item["width"]

    workflow_data["57"]["inputs"]["seed"] = item["seed"]
    # workflow_data["286"]["inputs"]["seed"] = item["seed"]
    
    workflow_data["110"]["inputs"]["batch_size"] = item["batch_size"]

    
    if is_edit:
        print("downloading mask")
        download_to_comfyui(item["mask"], "input")
        workflow_data["134"]["inputs"]["image"] = item["mask"].split("/")[-1]
        print("downloading image")
        download_to_comfyui(item["image"], "input")
        workflow_data["139"]["inputs"]["image"] = item["image"].split("/")[-1]

        workflow_data["138"]["inputs"]["value"] = True
        workflow_data["157"]["inputs"]["value"] = 1

    else:
        workflow_data["138"]["inputs"]["value"] = False
        workflow_data["157"]["inputs"]["value"] = 0
    
    

    return workflow_data

def create_upscale_workflow(item, isFlux = False):
    download_to_comfyui(item["input_image_url"], "input")

    # def create_upscale_workflow_flux(item):
    #     workflow_data = json.loads(
    #         (pathlib.Path(__file__).parent / "workflow_api_flux_upscale.json").read_text()
    #     )
    #     workflow_data["59"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
    #     workflow_data["72"]["inputs"]["denoise"] = item["denoising_strength"]
    #     return workflow_data
    
    # def create_upscale_workflow_basic(item):
    #     workflow_data = json.loads(
    #         (pathlib.Path(__file__).parent / "workflow_api_upscale_basic.json").read_text()
    #     )
    #     workflow_data["1"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
    #     return workflow_data

    # def create_upscale_workflow_advanced(item):
    #     workflow_data = json.loads(
    #         (pathlib.Path(__file__).parent / "workflow_api_upscale_advanced.json").read_text()
    #     )
    #     workflow_data["97"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
    #     workflow_data["235"]["inputs"]["denoise"] = item["denoising_strength"]
    #     return workflow_data
    

    # if item["type"] == "flux_upscale":
    #     workflow_data = create_upscale_workflow_flux(item)
    # elif item["type"] == "ultimate_upscale":
    #     workflow_data = create_upscale_workflow_advanced(item)
    # else:
    #     workflow_data = create_upscale_workflow_basic(item)

    workflow_data = json.loads(
        (pathlib.Path(__file__).parent / "./workflows/flux_upscale_api.json").read_text()
    )
    workflow_data["59"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
    workflow_data["90"]["inputs"]["value"] = item["denoising_strength"]
    
    return workflow_data


def create_rerender_workflow(item):
    download_to_comfyui(item["input_image_url"], "input")
    workflow_data = json.loads(
            (pathlib.Path(__file__).parent / "workflow_api_rerender.json").read_text()
        )
    
    workflow_data["379"]["inputs"]["image"] = item["input_image_url"].split("/")[-1]
    workflow_data["298"]["inputs"]["text_positive"] = item["prompt"]
    workflow_data["387"]["inputs"]["weight_style"] = item["weight_style"]
    return workflow_data

def remove_temp_file(list_file_name):
    for item in list_file_name:
        try:
            os.remove("/root/input/" + item)
            print(f"Removed file {item}")
        except Exception as e:
            print(f"File {item} not found. Skipping.")

import linecache

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
        
        if "rerender" in item["type"]:
            workflow_data = create_rerender_workflow(item=item)
        # download input images to the container
        elif "upscale" in item["type"]:
            workflow_data = create_upscale_workflow(item=item, isFlux=item["type"] == "flux_upscale")
        else:
            workflow_data = create_sketch2img_workflow(item=item, is_edit=item["type"] == "edit", is_test=item.get("is_test", False))
        
        
        # save workflow data to file
        workflow_file = f"./temp_workflow.json"
        with open(workflow_file, "w") as f:
            json.dump(workflow_data, f)
        
        print("ready to run")
        workflow_run(workflow_data, item["task_id"], item["user_id"], item["seed"], port, schema)
        remove_temp_file([item.get("input_image_url", "").split("/")[-1], item.get("mask", "").split("/")[-1], item.get("image", "").split("/")[-1]])
    except Exception as e:
        print(e)
        if item:
            engine_log_file = '/engine_1.txt'
            queue_log_file = '/queue_processing_5001.txt'

            line_number = 100
            line_number_q = 40

            # Read specific line from queue log file
            with open(queue_log_file, 'r') as f:
                queue_lines = f.readlines()
                queue_log = queue_lines[-line_number_q:]

            # Read specific line from engine log file
            with open(engine_log_file, 'r') as f:
                engine_lines = f.readlines()
                engine_log = engine_lines[-line_number:]

            log = engine_log + ["\n\n\n\n\n\n\n\n"] + queue_log + ["\n\n\n\n\n\n\n\n"] + [str(e)]
            supabase.schema(schema).table("Tasks").update({
                "status": "failed",
                "finished_at": datetime.datetime.utcnow().isoformat(),
                "logs": "\n".join(log)
            }).eq("task_id", item['task_id']).execute()


# if __name__ == "__main__":
#       engine_log_file = './engine_1.txt'

#       line_number = 100
#       line_number_q = 40

#       # Read specific line from queue log file
#       with open(engine_log_file, 'r', encoding="utf8") as f:
#           queue_lines = f.readlines()
#           print(len(queue_lines))
#           queue_log = queue_lines[-line_number:]

#       print (queue_log)