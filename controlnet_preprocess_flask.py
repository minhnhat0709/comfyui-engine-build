import base64
import json
import os
import pathlib
import io
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from PIL import Image
from comfyapp import run_task
from helpers import connect_to_local_server, download_to_comfyui, get_images
import asyncio
import traceback

app = FastAPI()

# convert png bytes to jpg base64 string
def png_bytes_to_jpg_base64(image_bytes: bytes):
    png_image = Image.open(io.BytesIO(image_bytes))
    rgb_image = png_image.convert('RGB')
    jpg_bytes_io = io.BytesIO()
    rgb_image.save(jpg_bytes_io, format='JPEG')
    jpg_bytes = jpg_bytes_io.getvalue()
    png_image.close()
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

@app.post("/controlnet/detect")
async def run(request: Request):
    try:
        item = await request.json()

        workflow_path = pathlib.Path(__file__).parent / "workflow_api_controlnet.json"
        workflow_data = json.loads(workflow_path.read_text())

        imageBase64 = item["controlnet_input_images"][0]
        imageBytes = base64.b64decode(imageBase64.split(',')[1])
        image = Image.open(io.BytesIO(imageBytes))
        input_path = "/root/input/controlnet_input.png"
        image.save(input_path)
        image.close()

        workflow_data["1"]["inputs"]["image"] = "controlnet_input.png"
        workflow_data["2"]["inputs"]["preprocessor"] = preprocessor_map[item["controlnet_module"]]

        server_address = "127.0.0.1:8189"
        ws = connect_to_local_server(server_address)

        try:
            images = get_images(ws, workflow_data, server_address)
        finally:
            ws.close()

        result = [png_bytes_to_jpg_base64(image) for image in images]
        os.remove(input_path)

        return JSONResponse(content={"images": result})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(content={"images": []})

@app.post("/echo")
async def echo(request: Request):
    data = await request.json()
    return JSONResponse(content=data)
