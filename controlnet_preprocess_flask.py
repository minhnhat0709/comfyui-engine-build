import base64
import json
import os
import pathlib
import subprocess
from flask import Flask, request, Response, jsonify
from PIL import Image
import io
from comfyapp import run_task
from helpers import connect_to_local_server, download_to_comfyui, get_images

web_app = Flask(__name__)

# convert png bytes to jpg base64 string
def png_bytes_to_jpg_base64(image_bytes: bytes):
    # Load the PNG image from bytes
    png_image = Image.open(io.BytesIO(image_bytes))
    
    # Convert the image to RGB mode (JPEG does not support transparency)
    rgb_image = png_image.convert('RGB')
    
    # Save the image to a BytesIO object in JPEG format
    jpg_bytes_io = io.BytesIO()
    rgb_image.save(jpg_bytes_io, format='JPEG')
    
    # Get the JPEG bytes
    jpg_bytes = jpg_bytes_io.getvalue()
    
    return base64.b64encode(jpg_bytes).decode('utf-8')

preprocessor_map = {
      "canny": "CannyEdgePreprocessor",
      "depth": "DepthAnythingPreprocessor",
      "lineart": "LineArtPreprocessor",
      "mlsd": "M-LSDPreprocessor",
      "openpose": "OpenposePreprocessor",
      "scribble_xdog": "Scribble_XDoG_Preprocessor",
      "scribble_hed": "HEDPreprocessor",
      "segmentation": "SAMPreprocessor",
      "tile": "TilePreprocessor",
    }


@web_app.post("/controlnet/detect")
def run():
    item = None
    try:
        item = request.json
        
        workflow_data = json.loads(
            (pathlib.Path(__file__).parent / "workflow_api_controlnet.json").read_text()
        )

        imageBase64 = item["controlnet_input_images"][0]
        imageBytes = base64.b64decode(imageBase64.split(',')[1])
        image = Image.open(io.BytesIO(imageBytes))
        image.save("/root/input/controlnet_input.png")

        workflow_data["1"]["inputs"]["image"] = "controlnet_input.png"
        workflow_data["2"]["inputs"]["preprocessor"] = preprocessor_map[item["controlnet_module"]]


        server_address = f"127.0.0.1:8189"
        ws = connect_to_local_server(server_address)
        images = get_images(ws, workflow_data, server_address)
        ws.close()  # close the websocket

        result = []
        for image in images:
            result.append(png_bytes_to_jpg_base64(image))

        # remove the input image
        os.remove("/root/input/controlnet_input.png")
        return jsonify({"images": result})
    except Exception as e:
        print(e)
    return jsonify({"images": []})

@web_app.post("/echo")
def echo():
    return request.json

if __name__ == "__main__":
    from waitress import serve
    cmd = f"python main.py --dont-print-server --listen --port 8189"
    subprocess.Popen(cmd, shell=True)
    serve(web_app, host="0.0.0.0", port=5003)