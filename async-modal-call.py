import threading
import modal
import requests
from flask import Flask, request, Response

image = modal.Image.debian_slim().pip_install("flask").pip_install("requests")
app = modal.App("flask-modal", image=image)
web_app = Flask(__name__)

@app.function()
def request_task(url, json):
    requests.post(url, json, headers={"Content-Type": "application/json"})


def fire_and_forget(url, json):
    threading.Thread(target=request_task, args=(url, json)).start()

@app.function()
@modal.wsgi_app()
def flask_app():
    return web_app


@web_app.post("/run")
async def run():
    data = request.json
    # fire_and_forget("https://eliai-team--example-comfyui-comfyui-flask-app.modal.run/run", data)
    
    comfyui_class = modal.Cls.lookup("example-comfyui", "ComfyUI")
    obj = comfyui_class()

    call = obj.run_task_eliai.spawn(data)
    return {"call_id": call.object_id}