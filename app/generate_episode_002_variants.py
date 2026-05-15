import copy
import json
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4


# ============================================================
# CONFIG
# ============================================================

COMFY_SERVER = "http://127.0.0.1:8000"

PROJECT_ROOT = Path("/Users/uditsurajsingh/Documents/animation/anime_agent_system")

WORKFLOW_PATH = PROJECT_ROOT / "data/workflows/animagine_basic_api.json"
PROMPT_JSON_PATH = PROJECT_ROOT / "data/episodes/episode_002/prompts/generation_prompts_v1.json"

COMFY_OUTPUT_DIR = Path("/Users/uditsurajsingh/AI/comfyui/output")

DEST_DIR = PROJECT_ROOT / "data/episodes/episode_002/keyframes/generated"


# ============================================================
# FILE LOADING
# ============================================================

def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid JSON structure in: {path}")

    return data


def load_workflow() -> dict:
    workflow = load_json(WORKFLOW_PATH)

    if not isinstance(workflow, dict):
        raise ValueError("Workflow file is not a valid ComfyUI API-format JSON.")

    return workflow


def load_prompt_config() -> dict:
    prompt_config = load_json(PROMPT_JSON_PATH)

    required_keys = ["episode_id", "model", "shots"]

    for key in required_keys:
        if key not in prompt_config:
            raise ValueError(f"Missing required key in prompt JSON: {key}")

    return prompt_config


# ============================================================
# COMFYUI WORKFLOW HELPERS
# ============================================================

def find_first_node_id(workflow: dict, class_type: str) -> str:
    for node_id, node in workflow.items():
        if node.get("class_type") == class_type:
            return str(node_id)

    raise ValueError(f"Could not find node with class_type={class_type}")


def get_positive_negative_clip_ids(workflow: dict, ksampler_id: str) -> tuple[str, str]:
    ksampler_inputs = workflow[ksampler_id]["inputs"]

    positive_input = ksampler_inputs.get("positive")
    negative_input = ksampler_inputs.get("negative")

    if not isinstance(positive_input, list) or not isinstance(negative_input, list):
        raise ValueError(
            "Could not identify positive/negative CLIP nodes from KSampler inputs. "
            "Make sure you saved the workflow in API format."
        )

    positive_clip_id = str(positive_input[0])
    negative_clip_id = str(negative_input[0])

    return positive_clip_id, negative_clip_id


def prepare_workflow(base_workflow: dict, model_config: dict, task: dict) -> dict:
    workflow = copy.deepcopy(base_workflow)

    checkpoint_id = find_first_node_id(workflow, "CheckpointLoaderSimple")
    latent_id = find_first_node_id(workflow, "EmptyLatentImage")
    ksampler_id = find_first_node_id(workflow, "KSampler")
    save_id = find_first_node_id(workflow, "SaveImage")

    positive_id, negative_id = get_positive_negative_clip_ids(workflow, ksampler_id)

    workflow[checkpoint_id]["inputs"]["ckpt_name"] = model_config["checkpoint"]

    workflow[positive_id]["inputs"]["text"] = task["positive"]
    workflow[negative_id]["inputs"]["text"] = task["negative"]

    workflow[latent_id]["inputs"]["width"] = model_config["width"]
    workflow[latent_id]["inputs"]["height"] = model_config["height"]
    workflow[latent_id]["inputs"]["batch_size"] = model_config.get("batch_size", 1)

    workflow[ksampler_id]["inputs"]["seed"] = task["seed"]
    workflow[ksampler_id]["inputs"]["steps"] = model_config["steps"]
    workflow[ksampler_id]["inputs"]["cfg"] = model_config["cfg"]
    workflow[ksampler_id]["inputs"]["sampler_name"] = model_config["sampler"]
    workflow[ksampler_id]["inputs"]["scheduler"] = model_config["scheduler"]
    workflow[ksampler_id]["inputs"]["denoise"] = 1.0

    workflow[save_id]["inputs"]["filename_prefix"] = f"episode_002/generated/{task['output_stem']}"

    return workflow


# ============================================================
# COMFYUI API HELPERS
# ============================================================

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
        raise RuntimeError(
            f"Could not connect to ComfyUI at {url}. "
            f"Make sure ComfyUI is open at {COMFY_SERVER}. Error: {e}"
        )


def get_json(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not read from ComfyUI at {url}. Error: {e}")


def queue_prompt(workflow: dict) -> str:
    payload = {
        "prompt": workflow,
        "client_id": str(uuid4()),
    }

    result = post_json(f"{COMFY_SERVER}/prompt", payload)

    if "error" in result:
        raise RuntimeError(
            f"ComfyUI rejected the workflow:\n{json.dumps(result, indent=2)}"
        )

    if "prompt_id" not in result:
        raise RuntimeError(
            f"ComfyUI response did not include prompt_id:\n{json.dumps(result, indent=2)}"
        )

    return result["prompt_id"]


def wait_for_result(prompt_id: str, timeout_seconds: int = 1200) -> dict:
    start = time.time()

    while True:
        elapsed = time.time() - start

        if elapsed > timeout_seconds:
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
                raise ValueError(f"Unexpected image type from ComfyUI: {image_type}")

            return COMFY_OUTPUT_DIR / subfolder / filename

    raise ValueError("No output image found in ComfyUI history.")


# ============================================================
# TASK CREATION
# ============================================================

def build_tasks(prompt_config: dict) -> list[dict]:
    model_config = prompt_config["model"]
    variants_per_shot = model_config.get("variants_per_shot", 4)

    tasks = []

    for shot in prompt_config["shots"]:
        shot_id = shot["shot_id"]
        base_filename = shot["base_filename"]
        base_seed = int(shot["base_seed"])

        for variant_index in range(1, variants_per_shot + 1):
            seed = base_seed + ((variant_index - 1) * 10)

            output_stem = f"{base_filename}_variant_{variant_index:02d}_seed_{seed}"

            task = {
                "episode_id": prompt_config["episode_id"],
                "shot_id": shot_id,
                "base_filename": base_filename,
                "variant_index": variant_index,
                "seed": seed,
                "output_stem": output_stem,
                "filename": f"{output_stem}.png",
                "positive": shot["positive"],
                "negative": shot["negative"],
                "duration_seconds": shot["duration_seconds"],
            }

            tasks.append(task)

    return tasks


# ============================================================
# GENERATION
# ============================================================

def run_task(base_workflow: dict, model_config: dict, task: dict) -> dict:
    print("\n------------------------------------------------------------")
    print(f"Generating: {task['filename']}")
    print(f"Shot: {task['shot_id']}")
    print(f"Variant: {task['variant_index']}")
    print(f"Seed: {task['seed']}")

    workflow = prepare_workflow(base_workflow, model_config, task)

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

    return {
        "episode_id": task["episode_id"],
        "shot_id": task["shot_id"],
        "variant_index": task["variant_index"],
        "seed": task["seed"],
        "filename": task["filename"],
        "path": str(destination),
        "positive": task["positive"],
        "negative": task["negative"],
    }


def write_manifest(results: list[dict]) -> None:
    manifest_path = DEST_DIR / "generation_manifest_v1.json"

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\nManifest saved:")
    print(manifest_path)


def main() -> None:
    print("Loading ComfyUI API workflow...")
    base_workflow = load_workflow()

    print("Loading Episode 002 prompt config...")
    prompt_config = load_prompt_config()

    model_config = prompt_config["model"]
    tasks = build_tasks(prompt_config)

    print(f"Episode: {prompt_config['episode_id']} - {prompt_config['title']}")
    print(f"Output folder: {DEST_DIR}")
    print(f"Total images to generate: {len(tasks)}")

    results = []

    for task in tasks:
        result = run_task(base_workflow, model_config, task)
        results.append(result)

    write_manifest(results)

    print("\nDone.")
    print(f"Generated images are in: {DEST_DIR}")


if __name__ == "__main__":
    main()