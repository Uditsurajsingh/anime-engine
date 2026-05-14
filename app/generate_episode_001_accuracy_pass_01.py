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

COMFY_OUTPUT_DIR = Path("/Users/uditsurajsingh/AI/comfyui/output")
DEST_DIR = PROJECT_ROOT / "data/episodes/episode_001/variants/accuracy_pass_01"

CHECKPOINT_NAME = "animagine-xl-4.0-opt.safetensors"


# ============================================================
# SHARED PROMPT BLOCKS
# ============================================================

ARO_IDENTITY = """
Captain Aro, solo male teenage anime sea-adventure hero, messy black hair,
small scar under left eye, red sleeveless jacket, straw-colored beige scarf around neck,
dark navy knee-length shorts, brown sandals, lean agile male body,
playful fearless grin, original character
""".replace("\n", " ").strip()


STYLE_BLOCK = """
original nautical shonen anime adventure style, 2d anime look, bold black outlines,
clean cel shading, vibrant tropical colors, expressive anime face,
cinematic anime composition, sharp lineart, masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip()


ARO_NEGATIVE = """
multiple characters, crowd, duplicate character, girl, feminine body, different character,
wrong outfit, missing scarf, red scarf, yellow shorts, missing scar, pirate hat, eyepatch,
armor, modern clothes, modern shoes, photorealistic, realistic, 3d render, cgi,
blurry, lowres, bad anatomy, bad hands, extra fingers, missing fingers, extra limbs,
cropped, out of frame, text, watermark, signature, logo
""".replace("\n", " ").strip()


# ============================================================
# TASKS: 5 WEAK SHOTS × 4 VARIANTS EACH
# ============================================================

TASKS = [
    # ------------------------------------------------------------
    # S002 - Aro on mast
    # ------------------------------------------------------------
    *[
        {
            "name": f"S002_aro_on_mast_seed_{seed}",
            "filename": f"S002_aro_on_mast_seed_{seed}.png",
            "seed": seed,
            "width": 1024,
            "height": 576,
            "steps": 30,
            "cfg": 5.5,
            "sampler": "euler_ancestral",
            "scheduler": "normal",
            "positive": f"""
{ARO_IDENTITY}, full body visible, standing on top of a wooden ship mast,
heroic introduction pose, face clearly visible, camera looking slightly upward,
open sea and sunrise behind him, wind blowing scarf, strong readable silhouette,
adventure hero entrance shot, {STYLE_BLOCK}
""".replace("\n", " ").strip(),
            "negative": f"""
silhouette, face hidden, back view only, tiny character, unreadable face,
low angle hiding face, {ARO_NEGATIVE}
""".replace("\n", " ").strip(),
        }
        for seed in [310002, 310012, 310022, 310032]
    ],

    # ------------------------------------------------------------
    # S003 - Aro opens chest
    # ------------------------------------------------------------
    *[
        {
            "name": f"S003_aro_opens_chest_seed_{seed}",
            "filename": f"S003_aro_opens_chest_seed_{seed}.png",
            "seed": seed,
            "width": 1024,
            "height": 576,
            "steps": 30,
            "cfg": 5.5,
            "sampler": "euler_ancestral",
            "scheduler": "normal",
            "positive": f"""
{ARO_IDENTITY}, kneeling on wooden ship deck, both hands opening an old wooden treasure chest,
inside the chest is a glowing ancient sea map, blue-green magical light shining on Aro's excited face,
treasure discovery moment, chest clearly visible, glowing map clearly visible,
cinematic medium shot, story focus on chest and map, {STYLE_BLOCK}
""".replace("\n", " ").strip(),
            "negative": f"""
no chest, missing chest, no map, missing map, closed chest, empty hands,
standing far away, treasure pile only, face not visible, {ARO_NEGATIVE}
""".replace("\n", " ").strip(),
        }
        for seed in [310003, 310013, 310023, 310033]
    ],

    # ------------------------------------------------------------
    # S006 - Rival ship through fog
    # ------------------------------------------------------------
    *[
        {
            "name": f"S006_rival_ship_fog_seed_{seed}",
            "filename": f"S006_rival_ship_fog_seed_{seed}.png",
            "seed": seed,
            "width": 1024,
            "height": 576,
            "steps": 30,
            "cfg": 5.5,
            "sampler": "euler_ancestral",
            "scheduler": "normal",
            "positive": """
wide cinematic shot from behind Captain Aro's small wooden adventure ship,
Aro small in foreground looking toward the distance, a dark rival ship emerging through thick sea fog
in the background, visible wooden hull, tall sails, cannon ports, threatening silhouette,
ocean waves, tense nautical confrontation, dramatic fog layers, clear enemy ship shape,
original nautical shonen anime adventure style, 2d anime look, bold black outlines,
clean cel shading, vibrant tropical colors with gray fog contrast, cinematic wide shot,
sharp lineart, masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip(),
            "negative": """
no ship, missing rival ship, abstract shape, fantasy portal, moon, planet, spaceship,
sci-fi ship, modern battleship, city, castle, crowd, multiple characters,
photorealistic, realistic, 3d render, cgi, blurry, lowres, text, watermark, signature, logo
""".replace("\n", " ").strip(),
        }
        for seed in [310006, 310016, 310026, 310036]
    ],

    # ------------------------------------------------------------
    # S009 - Map points to island
    # ------------------------------------------------------------
    *[
        {
            "name": f"S009_map_points_island_seed_{seed}",
            "filename": f"S009_map_points_island_seed_{seed}.png",
            "seed": seed,
            "width": 1024,
            "height": 576,
            "steps": 30,
            "cfg": 5.5,
            "sampler": "euler_ancestral",
            "scheduler": "normal",
            "positive": f"""
close-up of glowing ancient sea map held in Captain Aro's hands,
old parchment map clearly visible, bright magical blue-green route line on the map
pointing toward a dark forbidden island symbol, compass drawing, nautical symbols,
mystical light, Aro's red sleeveless jacket and beige scarf partially visible at edge of frame,
ocean and mysterious island silhouette faintly visible in background,
clear story focus on the map route, {STYLE_BLOCK}
""".replace("\n", " ").strip(),
            "negative": """
no map, missing map, empty ocean only, person only, face closeup only,
modern map, GPS, city map, unreadable mess, random paper, book, scroll only,
photorealistic, realistic, 3d render, cgi, blurry, lowres, bad hands, extra fingers,
text, watermark, signature, logo
""".replace("\n", " ").strip(),
        }
        for seed in [310009, 310019, 310029, 310039]
    ],

    # ------------------------------------------------------------
    # S010 - Aro faces island
    # ------------------------------------------------------------
    *[
        {
            "name": f"S010_aro_faces_island_seed_{seed}",
            "filename": f"S010_aro_faces_island_seed_{seed}.png",
            "seed": seed,
            "width": 1024,
            "height": 576,
            "steps": 30,
            "cfg": 5.5,
            "sampler": "euler_ancestral",
            "scheduler": "normal",
            "positive": f"""
Captain Aro, solo male teenage anime sea-adventure hero, messy black hair,
red sleeveless jacket, straw-colored beige scarf flowing in sea wind,
dark navy knee-length shorts, brown sandals, lean agile male body, original character,
seen from behind and slight side angle, clearly male teenage hero,
standing at the bow of a small wooden ship, facing a mysterious forbidden island ahead,
determined adventurous mood, dramatic sunrise sky, ocean horizon,
cinematic ending shot, {STYLE_BLOCK}
""".replace("\n", " ").strip(),
            "negative": f"""
girl, feminine body, different character, long hair, yellow jacket, green outfit,
red scarf, missing scarf, missing red jacket, multiple characters, duplicate character,
split screen, two panels, face closeup only, front portrait, {ARO_NEGATIVE}
""".replace("\n", " ").strip(),
        }
        for seed in [310010, 310020, 310030, 310040]
    ],
]


# ============================================================
# COMFYUI API HELPERS
# ============================================================

def load_workflow() -> dict:
    if not WORKFLOW_PATH.exists():
        raise FileNotFoundError(f"Workflow API JSON not found: {WORKFLOW_PATH}")

    with WORKFLOW_PATH.open("r", encoding="utf-8") as f:
        workflow = json.load(f)

    if not isinstance(workflow, dict):
        raise ValueError("Workflow file is not a valid ComfyUI API-format JSON.")

    return workflow


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

    workflow[save_id]["inputs"]["filename_prefix"] = f"accuracy_pass_01/{task['name']}"

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
        raise RuntimeError(f"ComfyUI rejected the workflow:\n{json.dumps(result, indent=2)}")

    return result["prompt_id"]


def wait_for_result(prompt_id: str, timeout_seconds: int = 1200) -> dict:
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

    print(f"Variant output folder: {DEST_DIR}")
    print(f"Total tasks: {len(TASKS)}")

    for task in TASKS:
        run_task(base_workflow, task)

    manifest_path = DEST_DIR / "accuracy_pass_01_manifest.json"

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(TASKS, f, indent=2)

    print("\nDone.")
    print(f"Generated variants: {DEST_DIR}")
    print(f"Manifest saved: {manifest_path}")


if __name__ == "__main__":
    main()