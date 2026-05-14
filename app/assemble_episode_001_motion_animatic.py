from pathlib import Path
import subprocess
import shutil


PROJECT_ROOT = Path("/Users/uditsurajsingh/Documents/animation/anime_agent_system")

KEYFRAME_DIR = PROJECT_ROOT / "data/episodes/episode_001/keyframes"
FINAL_DIR = PROJECT_ROOT / "data/episodes/episode_001/final"
TEMP_DIR = FINAL_DIR / "temp_motion_clips"

FINAL_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_VIDEO = FINAL_DIR / "episode_001_aro_only_motion_animatic_v2.mp4"
CONCAT_FILE = TEMP_DIR / "concat_motion_list.txt"
SUBTITLE_FILE = FINAL_DIR / "episode_001_aro_only_motion_animatic_v2.srt"


SHOTS = [
    {
        "file": "S001_open_sea_sunrise.png",
        "duration": 5,
        "motion": "slow_zoom_in",
    },
    {
        "file": "S002_aro_on_mast.png",
        "duration": 5,
        "motion": "slow_zoom_in",
    },
    {
        "file": "S003_aro_opens_chest.png",
        "duration": 6,
        "motion": "slow_zoom_in",
    },
    {
        "file": "S004_aro_studies_map.png",
        "duration": 6,
        "motion": "slow_zoom_in",
    },
    {
        "file": "S005_aro_treasure_joke.png",
        "duration": 6,
        "motion": "small_pan_right",
    },
    {
        "file": "S006_rival_ship_fog.png",
        "duration": 6,
        "motion": "slow_zoom_in",
    },
    {
        "file": "S007_cannon_blast_aro_laughs.png",
        "duration": 7,
        "motion": "small_pan_left",
    },
    {
        "file": "S008_aro_jumps_from_mast.png",
        "duration": 7,
        "motion": "slow_zoom_in",
    },
    {
        "file": "S009_map_points_island.png",
        "duration": 6,
        "motion": "slow_zoom_in",
    },
    {
        "file": "S010_aro_faces_island.png",
        "duration": 6,
        "motion": "slow_zoom_in",
    },
]


SUBTITLES = """1
00:00:00,000 --> 00:00:05,000
Narrator: Beyond the Red Sea, some maps are better left buried.

2
00:00:10,000 --> 00:00:16,000
Aro: Finally! Treasure!

3
00:00:16,000 --> 00:00:22,000
Aro: Huh. That is probably not normal.

4
00:00:22,000 --> 00:00:28,000
Aro: It is glowing. That means expensive.

5
00:00:28,000 --> 00:00:34,000
[Explosion nearby]

6
00:00:34,000 --> 00:00:41,000
Aro: Great. I was getting bored.

7
00:00:47,000 --> 00:00:53,000
Narrator: The map pointed to an island erased from every sea chart.

8
00:00:54,000 --> 00:01:00,000
Aro: Then we go there.
"""


def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg is not installed. Install it with: brew install ffmpeg"
        )


def validate_keyframes():
    missing = []

    for shot in SHOTS:
        path = KEYFRAME_DIR / shot["file"]
        if not path.exists():
            missing.append(path)

    if missing:
        print("Missing keyframes:")
        for path in missing:
            print(f" - {path}")
        raise FileNotFoundError("Fix missing keyframes before assembling.")

    total = sum(shot["duration"] for shot in SHOTS)
    print(f"Total duration: {total} seconds")

    if total != 60:
        raise ValueError(f"Expected 60 seconds, got {total}.")


def motion_filter(motion: str, duration: int) -> str:
    frames = duration * 24

    base_scale = (
        "scale=2200:1240:force_original_aspect_ratio=increase,"
        "crop=2200:1240"
    )

    if motion == "slow_zoom_in":
        zoompan = (
            f"zoompan=z='min(zoom+0.0008,1.08)':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1920x1080:fps=24"
        )

    elif motion == "small_pan_right":
        zoompan = (
            f"zoompan=z='1.05':"
            f"x='(iw-iw/zoom)*on/{frames}':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1920x1080:fps=24"
        )

    elif motion == "small_pan_left":
        zoompan = (
            f"zoompan=z='1.05':"
            f"x='(iw-iw/zoom)*(1-on/{frames})':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1920x1080:fps=24"
        )

    else:
        zoompan = (
            f"zoompan=z='1.0':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1920x1080:fps=24"
        )

    return f"{base_scale},{zoompan},format=yuv420p"


def create_motion_clip(index: int, shot: dict) -> Path:
    input_image = KEYFRAME_DIR / shot["file"]
    output_clip = TEMP_DIR / f"{index:03d}_{Path(shot['file']).stem}.mp4"

    vf = motion_filter(shot["motion"], shot["duration"])

    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", str(input_image),
        "-t", str(shot["duration"]),
        "-vf", vf,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "24",
        str(output_clip),
    ]

    print(f"Creating clip {index:03d}: {shot['file']}")
    subprocess.run(cmd, check=True)

    return output_clip


def write_concat_file(clips):
    lines = []

    for clip in clips:
        lines.append(f"file '{clip}'")

    CONCAT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote concat file: {CONCAT_FILE}")


def write_subtitles():
    SUBTITLE_FILE.write_text(SUBTITLES, encoding="utf-8")
    print(f"Wrote subtitles: {SUBTITLE_FILE}")


def concat_clips():
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(CONCAT_FILE),
        "-c", "copy",
        str(OUTPUT_VIDEO),
    ]

    print("Combining motion clips...")
    subprocess.run(cmd, check=True)
    print(f"Saved video: {OUTPUT_VIDEO}")


def main():
    check_ffmpeg()
    validate_keyframes()
    write_subtitles()

    clips = []
    for i, shot in enumerate(SHOTS, start=1):
        clip = create_motion_clip(i, shot)
        clips.append(clip)

    write_concat_file(clips)
    concat_clips()

    print("\nDone.")
    print(f"Video: {OUTPUT_VIDEO}")
    print(f"Subtitles: {SUBTITLE_FILE}")


if __name__ == "__main__":
    main()