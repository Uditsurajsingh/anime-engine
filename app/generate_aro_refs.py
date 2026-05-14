import copy
import json
import shutil
import time
import urllib.request
import urllib.error
from pathlib import Path
from uuid import uuid4


# =========================
# CONFIG
# =========================

COMFY_SERVER = "http://127.0.0.1:8000"

PROJECT_ROOT = Path("/Users/uditsurajsingh/Documents/animation/anime_agent_system")
WORKFLOW_PATH = PROJECT_ROOT / "data/workflows/animagine_basic_api.json"

COMFY_OUTPUT_DIR = Path("/Users/uditsurajsingh/AI/comfyui/output")
DEST_DIR = PROJECT_ROOT / "data/characters"

CHECKPOINT_NAME = "animagine-xl-4.0-opt.safetensors"

DEFAULT_NEGATIVE = """
multiple people, multiple boys, multiple characters, crowd, group, team, crew,
duplicate character, clones, character sheet, multiple poses, split screen, collage,
sea background, ocean, sky, clouds, ship, detailed background, girl, feminine body,
child, toddler, yellow shorts, red scarf, missing scar, no scar, long scarf, tunic,
robe, dress, skirt, lowres, bad anatomy, bad hands, missing fingers, extra fingers,
extra limbs, cropped body, out of frame, worst quality, low quality, low score,
bad score, average score, text, signature, watermark, username, blurry,
photorealistic, realistic, 3d render, cgi, beard, armor, modern shoes, hat,
pirate hat, eyepatch
""".replace("\n", " ").strip()


TASKS = [
    {
        "name": "aro_3quarter_full_body",
        "filename": "aro_3quarter_full_body.png",
        "seed": 100011,
        "width": 768,
        "height": 1024,
        "steps": 28,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
solo, 1boy, teenage male anime sea-adventure hero, full body, three-quarter view,
standing still, single character only, centered composition, clean white background,
messy black hair, small scar under left eye, red sleeveless jacket, straw-colored scarf
around neck, dark knee-length shorts, brown sandals, lean agile male body, playful fearless
grin, simple character reference pose, original nautical anime adventure character,
bold black outlines, clean cel shading, vibrant tropical colors, expressive anime face,
sharp lineart, masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip(),
        "negative": DEFAULT_NEGATIVE,
    },
    {
        "name": "aro_face_smile",
        "filename": "aro_face_smile.png",
        "seed": 100012,
        "width": 768,
        "height": 768,
        "steps": 28,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
solo, 1boy, close-up portrait, teenage male anime sea-adventure hero, smiling face,
playful fearless grin, messy black hair, clearly visible small scar under left eye,
red sleeveless jacket collar visible, straw-colored scarf around neck, clean white background,
centered composition, original nautical anime adventure character, bold black outlines,
clean cel shading, vibrant tropical colors, expressive anime face, sharp lineart,
masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip(),
        "negative": DEFAULT_NEGATIVE,
    },
    {
        "name": "aro_action_pose",
        "filename": "aro_action_pose.png",
        "seed": 100013,
        "width": 768,
        "height": 1024,
        "steps": 28,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
solo, 1boy, teenage male anime sea-adventure hero, full body dynamic action pose,
jumping forward, playful fearless grin, messy black hair, small scar under left eye,
red sleeveless jacket, straw-colored scarf around neck flowing slightly, dark knee-length shorts,
brown sandals, lean agile male body, clean white background, centered composition,
original nautical anime adventure character, bold black outlines, clean cel shading,
vibrant tropical colors, expressive anime face, sharp lineart, masterpiece, high score,
great score, absurdres
""".replace("\n", " ").strip(),
        "negative": DEFAULT_NEGATIVE.replace("action scene,", "").replace("jumping,", ""),
    },
    {
        "name": "aro_comedy_shocked",
        "filename": "aro_comedy_shocked.png",
        "seed": 100014,
        "width": 768,
        "height": 1024,
        "steps": 28,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
solo, 1boy, teenage male anime sea-adventure hero, full body comedy shocked pose,
exaggerated surprised anime expression, wide eyes, open mouth, messy black hair,
small scar under left eye, red sleeveless jacket, straw-colored scarf around neck,
dark knee-length shorts, brown sandals, lean agile male body, clean white background,
centered composition, original nautical anime adventure character, bold black outlines,
clean cel shading, vibrant tropical colors, expressive anime face, sharp lineart,
masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip(),
        "negative": DEFAULT_NEGATIVE,
    },
]


# =========================
# COMFYUI HELPERS
# =========================

def load_workflow() -> dict:
    if not WORKFLOW_PATH.exists():
        raise FileNotFoundError(f"Workflow API JSON not found: {WORKFLOW_PATH}")
    with WORKFLOW_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_first_node_id(workflow: dict, class_type: str) -> str:
    for node_id, node in workflow.items():
        if node.get("class_type") == class_type:
            return node_id
    raise ValueError(f"Could not find node with class_type={class_type}")


def get_positive_negative_clip_ids(workflow: dict, ksampler_id: str) -> tuple[str, str]:
    ksampler_inputs = workflow[ksampler_id]["inputs"]

    positive_input = ksampler_inputs.get("positive")
    negative_input = ksampler_inputs.get("negative")

    if not isinstance(positive_input, list) or not isinstance(negative_input, list):
        raise ValueError("Could not identify positive/negative CLIP nodes from KSampler inputs.")

    positive_clip_id = str(positive_input[0])
    negative_clip_id = str(negative_input[0])

    return positive_clip_id, negative_clip_id


def prepare_workflow(base_workflow: dict, task: dict) -> dict:
    workflow = copy.deepcopy(base_workflow)

    checkpoint_id = find_first_node_id(workflow, "CheckpointLoaderSimple")
    latent_id = find_first_node_id(workflow, "EmptyLatentImage")
    ksampler_id = find_first_node_id(workflow, "KSampler")
    save_id = find_first_node_id(workflow, "SaveImage")

    positive_id, negative_id = get_positive_negative_clip_ids(workflow, ksampler_id)

    workflow[checkpoint_id]["inputs"]["ckpt_name"] = CHECKPOINT_NAME

    workflow[positive_id]["inputs"]["text"] = task["positive"]
    workflow[negative_id]["inputs"]["text"] = task["negative"]

    workflow[latent_id]["inputs"]["width"] = task["width"]
    workflow[latent_id]["inputs"]["height"] = task["height"]
    workflow[latent_id]["inputs"]["batch_size"] = 1

    workflow[ksampler_id]["inputs"]["seed"] = task["seed"]
    workflow[ksampler_id]["inputs"]["steps"] = task["steps"]
    workflow[ksampler_id]["inputs"]["cfg"] = task["cfg"]
    workflow[ksampler_id]["inputs"]["sampler_name"] = task["sampler"]
    workflow[ksampler_id]["inputs"]["scheduler"] = task["scheduler"]
    workflow[ksampler_id]["inputs"]["denoise"] = 1.0

    workflow[save_id]["inputs"]["filename_prefix"] = f"auto_refs/{task['name']}"

    return workflow


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not connect to ComfyUI at {url}. Is ComfyUI open? Error: {e}")


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def queue_prompt(workflow: dict) -> str:
    payload = {
        "prompt": workflow,
        "client_id": str(uuid4()),
    }

    result = post_json(f"{COMFY_SERVER}/prompt", payload)

    if "error" in result:
        raise RuntimeError(f"ComfyUI rejected the workflow: {json.dumps(result, indent=2)}")

    return result["prompt_id"]


def wait_for_result(prompt_id: str, timeout_seconds: int = 900) -> dict:
    start = time.time()

    while True:
        if time.time() - start > timeout_seconds:
            raise TimeoutError(f"Timed out waiting for prompt_id={prompt_id}")

        history = get_json(f"{COMFY_SERVER}/history/{prompt_id}")

        if prompt_id in history:
            return history[prompt_id]

        time.sleep(2)


def extract_first_output_image(history_item: dict) -> Path:
    outputs = history_item.get("outputs", {})

    for _, output_data in outputs.items():
        images = output_data.get("images", [])
        if images:
            img = images[0]
            filename = img["filename"]
            subfolder = img.get("subfolder", "")
            image_type = img.get("type", "output")

            if image_type != "output":
                raise ValueError(f"Unexpected image type: {image_type}")

            return COMFY_OUTPUT_DIR / subfolder / filename

    raise ValueError("No output image found in ComfyUI history.")


def run_task(base_workflow: dict, task: dict) -> None:
    print(f"\nGenerating: {task['filename']}")

    workflow = prepare_workflow(base_workflow, task)
    prompt_id = queue_prompt(workflow)

    print(f"Queued prompt_id: {prompt_id}")

    history_item = wait_for_result(prompt_id)
    source_image = extract_first_output_image(history_item)

    if not source_image.exists():
        raise FileNotFoundError(f"Generated image not found: {source_image}")

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    destination = DEST_DIR / task["filename"]

    shutil.copy2(source_image, destination)

    print(f"Saved: {destination}")


def main() -> None:
    print("Loading ComfyUI API workflow...")
    base_workflow = load_workflow()

    for task in TASKS:
        run_task(base_workflow, task)

    manifest_path = DEST_DIR / "aro_reference_generation_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(TASKS, f, indent=2)

    print("\nDone.")
    print(f"Manifest saved: {manifest_path}")


if __name__ == "__main__":
    main()