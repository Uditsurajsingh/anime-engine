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
DEST_DIR = PROJECT_ROOT / "data/episodes/episode_001/keyframes"

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
        "name": "S001_open_sea_sunrise",
        "filename": "S001_open_sea_sunrise.png",
        "seed": 300001,
        "width": 1024,
        "height": 576,
        "steps": 26,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
wide cinematic shot, open sea at sunrise, small wooden adventure ship sailing on calm ocean,
warm golden light, tropical sea atmosphere, gentle waves, original nautical shonen anime style,
2d anime look, bold black outlines, clean cel shading, vibrant tropical colors, dynamic cinematic framing,
beautiful establishing shot, no photorealism, masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip(),
        "negative": """
photorealistic, realistic, 3d render, cgi, lowres, blurry, text, watermark, signature,
dark horror atmosphere, modern ship, warship, crowd, multiple characters, bad anatomy, low quality
""".replace("\n", " ").strip(),
    },
    {
        "name": "S002_aro_on_mast",
        "filename": "S002_aro_on_mast.png",
        "seed": 300002,
        "width": 1024,
        "height": 576,
        "steps": 26,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
Captain Aro, solo, 1boy, original young sea-adventure anime hero, messy black hair,
small scar under left eye, red sleeveless jacket, straw-colored scarf, dark knee-length shorts,
brown sandals, lean agile body, playful fearless grin, standing high on ship mast,
heroic introduction pose, open sea background, sunrise lighting, original nautical shonen anime style,
2d anime look, bold black outlines, clean cel shading, vibrant tropical colors, dynamic cinematic framing,
masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip(),
        "negative": """
multiple characters, crowd, Mina, girl, photorealistic, realistic, 3d render, cgi,
lowres, blurry, text, watermark, signature, bad anatomy, bad hands, armor, modern shoes, pirate hat
""".replace("\n", " ").strip(),
    },
    {
        "name": "S003_aro_opens_chest",
        "filename": "S003_aro_opens_chest.png",
        "seed": 300003,
        "width": 1024,
        "height": 576,
        "steps": 26,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
Captain Aro, solo, 1boy, original young sea-adventure anime hero, messy black hair,
small scar under left eye, red sleeveless jacket, straw-colored scarf, dark knee-length shorts,
brown sandals, lean agile body, on wooden ship deck, opening an old treasure chest,
inside the chest is a glowing ancient map emitting blue-green mystical light, excited treasure-hunter expression,
original nautical shonen anime style, 2d anime look, bold black outlines, clean cel shading,
vibrant tropical colors, dynamic cinematic framing, masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip(),
        "negative": """
multiple characters, crowd, Mina, girl, photorealistic, realistic, 3d render, cgi,
lowres, blurry, text, watermark, signature, bad anatomy, bad hands, modern objects, gun
""".replace("\n", " ").strip(),
    },
    {
        "name": "S004_aro_studies_map",
        "filename": "S004_aro_studies_map.png",
        "seed": 300004,
        "width": 1024,
        "height": 576,
        "steps": 26,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
Captain Aro, solo, 1boy, medium close shot, original young sea-adventure anime hero,
messy black hair, small scar under left eye, red sleeveless jacket, straw-colored scarf,
holding a glowing ancient map with both hands, suspicious curious expression, mysterious blue-green light from the map
lighting his face, ship deck background, original nautical shonen anime style, 2d anime look,
bold black outlines, clean cel shading, vibrant tropical colors, cinematic composition,
masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip(),
        "negative": """
multiple characters, crowd, Mina, girl, photorealistic, realistic, 3d render, cgi,
lowres, blurry, text, watermark, signature, bad anatomy, bad hands, extra fingers
""".replace("\n", " ").strip(),
    },
    {
        "name": "S005_aro_treasure_joke",
        "filename": "S005_aro_treasure_joke.png",
        "seed": 300005,
        "width": 1024,
        "height": 576,
        "steps": 26,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
Captain Aro, solo, 1boy, medium shot, original young sea-adventure anime hero,
messy black hair, small scar under left eye, red sleeveless jacket, straw-colored scarf,
dark knee-length shorts, playful goofy grin, holding glowing ancient map carelessly,
comedic confident expression as if joking about treasure, ship deck background,
original nautical shonen anime style, 2d anime look, bold black outlines, clean cel shading,
vibrant tropical colors, expressive anime face, masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip(),
        "negative": """
multiple characters, crowd, Mina, girl, photorealistic, realistic, 3d render, cgi,
lowres, blurry, text, watermark, signature, bad anatomy, bad hands, horror mood
""".replace("\n", " ").strip(),
    },
    {
        "name": "S006_rival_ship_fog",
        "filename": "S006_rival_ship_fog.png",
        "seed": 300006,
        "width": 1024,
        "height": 576,
        "steps": 26,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
cinematic ship battle setup, Captain Aro visible on his ship in foreground,
rival ship emerging through thick sea fog in background, tense nautical confrontation,
dark silhouette of attacking rival vessel, ocean atmosphere, dramatic shonen anime scene,
original nautical shonen anime style, 2d anime look, bold black outlines, clean cel shading,
vibrant tropical colors with gray fog contrast, dynamic cinematic framing, masterpiece,
high score, great score, absurdres
""".replace("\n", " ").strip(),
        "negative": """
photorealistic, realistic, 3d render, cgi, lowres, blurry, text, watermark, signature,
modern battleship, sci-fi ship, crowd of characters, Mina focus, bad anatomy
""".replace("\n", " ").strip(),
    },
    {
        "name": "S007_cannon_blast_aro_laughs",
        "filename": "S007_cannon_blast_aro_laughs.png",
        "seed": 300007,
        "width": 1024,
        "height": 576,
        "steps": 26,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
Captain Aro, solo focus, 1boy, original young sea-adventure anime hero, messy black hair,
small scar under left eye, red sleeveless jacket, straw-colored scarf, laughing fearlessly,
cannon blast exploding nearby, water splash and smoke, action tension on ship deck,
original nautical shonen anime style, 2d anime look, bold black outlines, clean cel shading,
vibrant tropical colors, dynamic cinematic framing, expressive anime action shot,
masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip(),
        "negative": """
multiple characters, crowd, Mina, girl, photorealistic, realistic, 3d render, cgi,
lowres, blurry, text, watermark, signature, bad anatomy, bad hands, gore
""".replace("\n", " ").strip(),
    },
    {
        "name": "S008_aro_jumps_from_mast",
        "filename": "S008_aro_jumps_from_mast.png",
        "seed": 300008,
        "width": 1024,
        "height": 576,
        "steps": 26,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
Captain Aro, solo, 1boy, full body dynamic action pose, jumping down from ship mast,
messy black hair, small scar under left eye, red sleeveless jacket, straw-colored scarf flowing,
dark knee-length shorts, brown sandals, fearless grin, energetic shonen action moment,
ship deck and sea visible below, original nautical shonen anime style, 2d anime look,
bold black outlines, clean cel shading, vibrant tropical colors, dynamic cinematic framing,
masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip(),
        "negative": """
multiple characters, crowd, Mina, girl, photorealistic, realistic, 3d render, cgi,
lowres, blurry, text, watermark, signature, bad anatomy, bad hands, extra limbs
""".replace("\n", " ").strip(),
    },
    {
        "name": "S009_map_points_island",
        "filename": "S009_map_points_island.png",
        "seed": 300009,
        "width": 1024,
        "height": 576,
        "steps": 26,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
cinematic close shot of glowing ancient map in Captain Aro's hands,
mystical light, magical pointer line or glowing direction toward a forbidden island in the distance,
dark mysterious island silhouette on the horizon, ocean atmosphere, original nautical shonen anime style,
2d anime look, bold black outlines, clean cel shading, vibrant tropical colors, dramatic mystical mood,
masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip(),
        "negative": """
photorealistic, realistic, 3d render, cgi, lowres, blurry, text, watermark, signature,
modern map, GPS, city skyline, crowd, Mina focus, bad anatomy
""".replace("\n", " ").strip(),
    },
    {
        "name": "S010_aro_faces_island",
        "filename": "S010_aro_faces_island.png",
        "seed": 300010,
        "width": 1024,
        "height": 576,
        "steps": 26,
        "cfg": 5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "positive": """
Captain Aro seen from behind and slightly side angle, standing at the bow of his ship,
facing a mysterious forbidden island ahead, determined adventurous mood, sunrise or bright dramatic sky,
messy black hair, red sleeveless jacket, straw-colored scarf, original nautical shonen anime style,
2d anime look, bold black outlines, clean cel shading, vibrant tropical colors, cinematic ending shot,
masterpiece, high score, great score, absurdres
""".replace("\n", " ").strip(),
        "negative": """
multiple characters, crowd, Mina, girl, photorealistic, realistic, 3d render, cgi,
lowres, blurry, text, watermark, signature, bad anatomy, bad hands
""".replace("\n", " ").strip(),
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