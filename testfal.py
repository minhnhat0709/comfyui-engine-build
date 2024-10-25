import fal
from pydantic import BaseModel
from fal.toolkit import Image
 
 
class Input(BaseModel):
    prompt: str
 
 
class Output(BaseModel):
    image: Image
 
 
class MyApp(fal.App, keep_alive=300):
    machine_type = "GPU-A100"
    requirements = [
        "diffusers==0.28.0",
        "torch==2.3.0",
        "accelerate",
        "transformers",
    ]
 
    def setup(self):
        import torch
        from diffusers import StableDiffusionXLPipeline, DPMSolverSinglestepScheduler
 
        self.pipe = StableDiffusionXLPipeline.from_pretrained(
            "sd-community/sdxl-flash",
            torch_dtype=torch.float16,
        ).to("cuda")
        self.pipe.scheduler = DPMSolverSinglestepScheduler.from_config(
            self.pipe.scheduler.config,
            timestep_spacing="trailing",
        )
 
    @fal.endpoint("/")
    def run(self, request: Input) -> Output:
        result = self.pipe(request.prompt, num_inference_steps=7, guidance_scale=3)
        image = Image.from_pil(result.images[0])
        return Output(image=image)