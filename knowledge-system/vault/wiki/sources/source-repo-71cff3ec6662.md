---
id: source-repo-71cff3ec6662
title: 'Source: GitHub地址如下，里面有整个pipeline，除了我正文说的方法，还做了很多一致性的处理，比'
type: source
source_id: repo-71cff3ec6662
source_type: repo
status: integrated
sources:
- repo-71cff3ec6662
raw_captures:
- vault/raw/repos/repo-71cff3ec6662/manifest.json
source_score:
  relevance: 0.75
  novelty: 0.85
  evidence_completeness: 0.9
  actionability: 1.0
  total: 0.863
  decision: integrate
  reasons:
  - priority:medium
  - domain_present
  - typed_or_tagged
  - no_duplicate_seen
  - uri_present
  - raw_text_substantial
  - source_type_present
  - no_linked_evidence_gap
  - processor:repo_extractor
  - routing_metadata_present
  - value_type_present
  - next_action_visible
tags:
- external_link
- linked-evidence
- parent-x-2051388640740401425
- repo
- repo_extractor
- source
updated: '2026-05-08'
---

# Source: GitHub地址如下，里面有整个pipeline，除了我正文说的方法，还做了很多一致性的处理，比

> [!info] Raw Evidence
> Raw capture manifest: `vault/raw/repos/repo-71cff3ec6662/manifest.json`

## Why This Was Saved

This source is connected to [[GitHub地址如下，里面有整个pipeline，除了我正文说的方法，还做了很多一致性的处理，比]] and should be integrated before any bookmark cleanup decision.

## Original

- URI: https://github.com/LayrKits/Sprite-Pipeline
- Author: Unknown
- Processor: `repo_extractor`
- Priority: `medium`
- Domain: `local_repo`

## Intake Score

| Axis | Score | Notes |
|---|---:|---|
| Relevance | 0.75 | Priority, domain, tags, and value type. |
| Novelty | 0.85 | Duplicate URI/title check against the current vault. |
| Evidence Completeness | 0.90 | Raw text, URI, author, source type, and linked-evidence gaps. |
| Actionability | 1.00 | Processor routing, metadata, and next visible action. |
| Total | 0.86 | Decision: `integrate`. |

Reasons: priority:medium, domain_present, typed_or_tagged, no_duplicate_seen, uri_present, raw_text_substantial, source_type_present, no_linked_evidence_gap, processor:repo_extractor, routing_metadata_present, value_type_present, next_action_visible

## Source Text

# Sprite Sheet Pipeline

## Repository Tree
- .gitignore
- Cleanup/.gitkeep
- docs/ANIMATION_PIPELINE_NOTES.md
- docs/FRAME_EXTRACTION.md
- docs/INTEGRATION_GUIDE.md
- docs/QUICKSTART.md
- docs/reference/PROMPTING_IMAGE_MODELS.md
- docs/reference/PROMPTING_VIDEO_MODELS.md
- docs/WORKSPACE_CONVENTIONS.md
- Final Sprite Sheets/.gitkeep
- README.md
- requirements.txt
- skills/sprite-sheet-pipeline/SKILL.md
- sprite_gallery_manifest.js
- sprite_gallery_pins.json
- sprite_viewer.html
- tools/animation_pipeline.py
- tools/build_sprite_gallery_manifest.py
- tools/extract_frames_ffmpeg.py
- tools/make_contact_sheet.py
- tools/matte_light_background.py
- tools/resize_sprite_sheet.py
- tools/select_frames.py
- Videos/.gitkeep
- Videos/Processed/.gitkeep
- Videos/To Be Processed/.gitkeep
- work/.gitkeep
- work/contact_sheets/.gitkeep
- work/extracted/.gitkeep
- work/frames/.gitkeep
- work/matted/.gitkeep
- work/previews/.gitkeep
- work/reports/.gitkeep
- work/sheets/.gitkeep

## Selected Files
### README.md

# Sprite Sheet Pipeline

Reusable video-to-sprite-sheet pipeline for turning ordered animation frames into
clean horizontal `256 x 256` sprite strips.

This repo includes reusable workflow docs, processing tools, a static viewer,
and a generic AI-assistant skill. It intentionally excludes generated assets,
videos, scratch outputs, demo sheets, and project-specific art.

## Quick Start

1. If using an AI assistant, give it
   `skills/sprite-sheet-pipeline/SKILL.md` or install that folder in the
   assistant's skill system. Ask it to use the `sprite-sheet-pipeline` skill.
2. Set up Python dependencies:

   ```bash
   python3 -m venv .venv
   ./.venv/bin/python -m pip install -r requirements.txt
   ```

   FFmpeg is not installed by `requirements.txt`; install it separately so
   `tools/extract_frames_ffmpeg.py` can call the `ffmpeg` command:

   ```bash
   # macOS
   brew install ffmpeg

   # Windows, with winget
   winget install Gyan.FFmpeg

   # Ubuntu/Debian Linux
   sudo apt install ffmpeg
   ```
3. To create source footage, use:
   - `docs/reference/PROMPTING_IMAGE_MODELS.md` for first poses, character
     references, and transition frames.
   - `docs/reference/PROMPTING_VIDEO_MODELS.md` for Kling or other
     image-to-video prompts.
4. To process footage, follow `docs/QUICKSTART.md`: extract frames, matte if
   needed, build the sprite sheet, review the preview/report, and promote only
   approved outputs.
5. After promotion, run:

   ```bash
   python tools/build_sprite_gallery_manifest.py
   ```

6. Open `sprite_viewer.html` directly in a browser to inspect final sheets.

## Included

- `tools/`: frame extraction, matting, cleanup/repack, contact sheet, resize, and
  viewer manifest utilities.
- `docs/`: active workflow notes, quickstart, folder conventions, extraction
  notes, and game integration guidance.
- `docs/reference/`: text-only image/video prompting references for creating
  clean animation source footage when needed.
- `skills/sprite-sheet-pipeline/`: generic AI-assistant skill that routes
  image prompting, video prompting, processing, validation, and promotion tasks
  to the right docs.
- `sprite_viewer.html`: static browser viewer for horizontal sprite sheets.
- `sprite_gallery_manifest.js`: empty starter manifest for the viewer.
- `sprite_gallery_pins.json`: empty starter pin list for the viewer.
- Empty `Videos/`, `work/`, `Final Sprite Sheets/`, and `Cleanup/` folders with
  `.gitkeep` files so the repo starts with the expected shape.

## Basic Flow

1. Put source animation videos in `Videos/` or `Videos/To Be Processed/`.
2. Extract ordered frames into `work/extracted/<character>/<action>/`.
3. Matte light backgrounds into `work/matted/<character>/<action>/` when needed.
4. Build a sprite strip with `tools/animation_pipeline.py`.
5. Review the preview image and JSON report.
6. Promote only approved sheets and matching cells into
   `Final Sprite Sheets/<GameName>/<CharacterName>/<animation>/`.
7. Run `python tools/build_sprite_gallery_manifest.py`.
8. Open `sprite_viewer.html` directly in a browser.

See `docs/QUICKSTART.md` for copy-paste commands.

## Asset Policy

Keep generated materials out of this repo unless they are tiny, intentional,
text-documented references that are required to explain or test pipeline
behavior. Normal source videos, extracted frames, matted frames, previews,
reports, final sheets, and game/demo art should stay ignored by default.


### docs/ANIMATION_PIPELINE_NOTES.md

# Canonical Video Frame Sprite Pipeline

This file is the active workflow. The older image-generation and prompt-driven
sheet process has been archived under
`archive/legacy-sheet-and-generation-workflow/`.

## Pipeline Contract

The source of truth is now an animation video. Frame extraction is the first
active processing step before cleanup and layout.

Use FFmpeg first:

```bash
python tools/extract_frames_ffmpeg.py \
  --input Videos/hero_run.mp4 \
  --output-dir work/extracted/hero/run \
  --fps 30
```

This cleanup pipeline starts after extraction, with a folder of ordered frame
images:

```text
work/extracted/<character>/<action>/frame_0001.png
work/extracted/<character>/<action>/frame_0002.png
work/extracted/<character>/<action>/frame_0003.png
```

The tool then normalizes those frames into a game-ready horizontal strip.

For Kling clips with an off-white background, run the provisional matte before
cleanup:

```bash
python tools/matte_light_background.py \
  --source-frames-dir work/extracted/hero/run \
  --output-dir work/matted/hero/run
```

Then run the sprite-sheet cleanup on `work/matted/...` with
`--background-mode alpha`.

## What The Extractor Must Provide

The frame extraction step should produce:

- one folder per animation
- one image per intended animation frame
- filenames that sort in playback order
- transparent PNGs when possible
- otherwise, frames on a perfectly flat chroma background such as `#00ff00`
- full character, weapon, cloth, and effects visible in every frame
- the same source canvas for every frame after watermark removal
- no important pixels touching the source frame edge
- consistent camera angle, resolution, and approximate character scale
- an `extraction_report.json` when using `tools/extract_frames_ffmpeg.py`

The extractor should avoid:

- mixed animations in one folder
- frame numbers that sort incorrectly, such as `1.png`, `10.png`, `2.png`
- complex backgrounds unless they have already been removed
- floor shadows, labels, text, watermarks, and UI overlays
- accidental crops of staff tips, limbs, cloth trails, dust, or spell effects
- tight character crops that make each animation choose a different effective
  zoom

## FFmpeg Extraction Notes

The default command we are trying first is equivalent to:

```bash
ffmpeg -i input_video.mp4 -vf "fps=30" -pix_fmt rgb24 frames/frame_%04d.png
```

Use `fps=30` when the Kling MP4 should be sampled as a constant 30 fps animation
timeline. The `fps` filter may duplicate or drop frames to hit the requested
rate. If a later pass needs every decoded source frame exactly as stored, omit
`--fps` in the wrapper.

## Provisional Light Matte

`tools/matte_light_background.py` is a local bridge for light/off-white Kling
backgrounds. It:

- estimates background color from frame corners
- removes pixels near that light background color
- preserves ordered filenames
- writes `matte_report.json`

This is not a full segmentation model. Replace or refine it when the dedicated
matting package is chosen.

## Cleanup And Layout Steps

All extracted frame folders should pass through `tools/animation_pipeline.py`.

The script performs the durable work:

- reads frame files in natural filename order
- optionally removes a flat chroma-key background
- despills green antialiasing when chroma mode is used
- removes tiny noise components
- preserves the source video canvas by default, scaling the full extracted
  frame into a transparent `256 x 256` cell
- keeps empty space around the character so idle, attack, and effect-heavy
  animations retain the same camera scale
- scales consistently across the sheet
- writes a true horizontal `256 x 256` strip
- writes individual cleaned frames
- writes a checker/guide preview
- writes a validation JSON report

`--layout-mode preserve-canvas` is the normal video workflow. Use
`--layout-mode fit-foreground` only for legacy recovery or a deliberate
foreground-normalized export; that older mode recenters each frame to
`TARGET

### docs/FRAME_EXTRACTION.md

# Frame Extraction

This is Step 2 of the video-to-sprite-sheet pipeline: convert a Kling MP4 into
ordered PNG frames so matting, luminance, cleanup, and sprite-sheet layout can
process images one by one.

## Preferred Tool: FFmpeg

FFmpeg is the first extraction tool to use because it is fast, mature, and
already installed on this machine.

Check the local install:

```bash
ffmpeg -version
ffprobe -version
```

Use the wrapper:

```bash
python tools/extract_frames_ffmpeg.py \
  --input Videos/hero_run.mp4 \
  --output-dir work/extracted/hero/run \
  --fps 30
```

If the video has a bottom watermark, crop it out during extraction before any
matting step:

```bash
python tools/extract_frames_ffmpeg.py \
  --input Videos/hero_run.mp4 \
  --output-dir work/extracted/hero/run_cropped \
  --fps 30 \
  --crop iw:840:0:0
```

`--crop` accepts FFmpeg's crop expression in `w:h:x:y` form. For a `960 x 960`
Kling clip with the watermark in the bottom-right corner, `iw:840:0:0` keeps the
full width and removes the bottom 120 pixels.

This crop is only for watermark/UI removal. Keep the rest of the video canvas
intact so every animation preserves the same character scale and empty space.

The wrapper writes:

- `frame_0001.png`, `frame_0002.png`, and so on
- `extraction_report.json` with source metadata, frame count, and exact command

## Direct FFmpeg Command

The direct command is:

```bash
ffmpeg -i input_video.mp4 -vf "fps=30" -pix_fmt rgb24 frames/frame_%04d.png
```

With a crop:

```bash
ffmpeg -i input_video.mp4 -vf "crop=iw:840:0:0,fps=30" -pix_fmt rgb24 frames/frame_%04d.png
```

Use this when you want constant 30 fps output. The `fps` filter converts the
video to a specified constant frame rate, which means FFmpeg may duplicate or
drop frames if the source timestamps do not already match that rate.

For literal decoded source frames, omit the fps filter:

```bash
ffmpeg -i input_video.mp4 -fps_mode passthrough -pix_fmt rgb24 frames/frame_%04d.png
```

## Why PNG

PNG keeps the extracted images lossless. `-q:v 2` is useful for JPEG-style
quality-based image outputs, but it is not needed for PNG quality.

## OpenCV Alternative

OpenCV is still a reasonable fallback when we need custom frame selection logic
inside Python. The basic approach is:

```python
import cv2 as cv

cap = cv.VideoCapture("Videos/hero_run.mp4")
index = 1
while cap.isOpened():
    ok, frame = cap.read()
    if not ok:
        break
    cv.imwrite(f"work/extracted/hero/run/frame_{index:04d}.png", frame)
    index += 1
cap.release()
```

Do not use OpenCV as the first option unless we need Python-side selection,
inspection, or per-frame logic during extraction. OpenCV's own docs note that
video capture depends on a proper FFmpeg or GStreamer install, so using FFmpeg
directly keeps this step simpler.


### docs/INTEGRATION_GUIDE.md

# Game Integration Guide

Use this after the pipeline creates a cleaned horizontal sprite sheet from
extracted animation frames.

## Output Assumptions

Pipeline outputs are horizontal strips:

- frame width: `256`
- frame height: `256`
- transparent background
- normal video outputs preserve the source canvas scale across animations

For normal video outputs, use the same draw origin or pivot for every animation
of a character. The empty transparent space is intentional; it keeps idle,
attack, and effect-heavy animations from changing apparent zoom.

## Canvas Draw Formula

For a `256 x 256` frame:

```js
const scale = renderWidth / frameWidth;
const drawX = actorPivotX - characterPivotX * scale;
const drawY = actorPivotY - characterPivotY * scale;
```

Then draw the animation at `drawX`, `drawY`, `renderWidth`, `renderHeight`.
Keep `characterPivotX` and `characterPivotY` constant for every animation of
the same character.

If a sheet was intentionally exported with `--layout-mode fit-foreground`, then
use the legacy guide values instead:

```js
const spriteGroundY = 220;
const spriteGroundRatio = spriteGroundY / frameHeight;
const drawX = actorCenterX - renderWidth / 2;
const drawY = actorFeetY - renderHeight * spriteGroundRatio;
```

## Frame Count And FPS

Cycle duration is:

```text
durationSeconds = frameCount / fps
```

If extraction changes the frame count but FPS stays the same, the visual cycle
changes speed.

Example:

```text
12 frames at 16 fps = 0.75s
10 frames at 16 fps = 0.625s
```

To preserve the old duration after changing frame count:

```text
newFps = newFrameCount / oldDurationSeconds
```

## Promotion Checklist

Before copying an output into a game:

- Preview the sheet and any animation preview you generate from it.
- Confirm the JSON report `status` is `pass`.
- Review duplicate-frame warnings.
- Review motion-pop warnings.
- Check that every animation uses the same apparent character scale.
- Update animation `frameWidth`, `frameHeight`, `frameCount`, and `fps`.
- Update cache-busting query strings if the game uses them.
- Update special frame logic if gameplay depends on frame numbers.

## Frame Meaning

Video extraction makes frame selection explicit. If the game maps gameplay state
to particular frame numbers, write down the new meaning before promotion.

For example, a jump sheet might reserve:

- early frames for crouch and liftoff
- middle frames for rising, apex, and falling
- final frames for landing and recovery

Keep those mappings in sync with the final promoted sheet.


### docs/QUICKSTART.md

# Quickstart

Use this when you have a Kling MP4 or other character animation video and need a
clean horizontal `256 x 256` sprite strip. The current default target is a
12-frame sheet at 256px cells, with a 24-frame 256px sheet kept when a smoother
reference is useful.

## Setup

From `2D Animation Pipeline`:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

Use `./.venv/bin/python` in the commands below after setup.

FFmpeg is an external command-line tool, not a Python package. On this machine it
is already installed at `/opt/homebrew/bin/ffmpeg`.

## Step 1: Extract Frames

Use FFmpeg first. This creates ordered RGB PNG frames and an
`extraction_report.json`.

```bash
python tools/extract_frames_ffmpeg.py \
  --input Videos/hero_run.mp4 \
  --output-dir work/extracted/hero/run \
  --fps 30
```

The `--fps 30` option uses FFmpeg's `fps` filter. That is correct when the Kling
video should be sampled as a 30 fps animation timeline. If you need every decoded
source frame without constant-fps resampling, omit `--fps`.

The equivalent direct FFmpeg command is:

```bash
ffmpeg -i Videos/hero_run.mp4 -vf "fps=30" -pix_fmt rgb24 work/extracted/hero/run/frame_%04d.png
```

For bottom-right Kling watermarks on a `960 x 960` clip, crop the bottom band at
extraction time:

```bash
python tools/extract_frames_ffmpeg.py \
  --input Videos/hero_run.mp4 \
  --output-dir work/extracted/hero/run_cropped \
  --fps 30 \
  --crop iw:840:0:0
```

## Step 2: Matte Light Background

Use this when the extracted PNGs are RGB frames on a light/off-white background:

```bash
python tools/matte_light_background.py \
  --source-frames-dir work/extracted/hero/run \
  --output-dir work/matted/hero/run
```

This is a first-pass local matte. It estimates the background color from frame
corners and removes pixels close to that light background. Skip this step if the
extractor already produced transparent PNGs.

## Step 3: Build Sprite Sheet

For video sources, keep the full extracted video canvas. This preserves the
character's size and empty space across idle, attack, and effect-heavy
animations. The pipeline still removes transparent noise, but it should not zoom
into the visible character.

## Transparent Extracted Frames

Use this when frame extraction produced transparent PNGs:

```bash
python tools/animation_pipeline.py \
  --source-frames-dir work/matted/hero/run \
  --frames 12 \
  --background-mode alpha \
  --layout-mode preserve-canvas \
  --output work/sheets/hero/run/hero_run_12f_256.png \
  --preview work/previews/hero_run_12f_preview.png \
  --frames-dir work/frames/hero/run_12f_256 \
  --report work/reports/hero_run_12f_report.json \
  --frame-prefix hero_run
```

## Chroma-Key Extracted Frames

Use this when frame extraction produced frames on a solid green background:

```bash
python tools/animation_pipeline.py \
  --source-frames-dir work/extracted/hero/jump \
  --frames 16 \
  --background-mode chroma \
  --layout-mode preserve-canvas \
  --key "#00ff00" \
  --output work/sheets/hero/jump/hero_jump_16f_256.png \
  --preview work/previews/hero_jump_16f_preview.png \
  --frames-dir work/frames/hero/jump_16f_256 \
  --report work/reports/hero_jump_16f_report.json \
  --frame-prefix hero_jump
```

## Frame Folder Rules

- Put only one animation in each `work/extracted/<character>/<action>/` folder.
- Name frames so natural filename sorting matches playback order, for example
  `0001.png`, `0002.png`, `0003.png`.
- Pass `--frames` as an explicit safety check.
- Crop only watermark/UI bands. Do not crop around the character, or each
  animation can end up with a different effective zoom.
- Use `--background-mode alpha` for already-transparent frames.
- Use `--background-mode chroma` for flat-key backgrounds.

## Read The Output

Check these files before promotion:

- output sheet: final horizontal PNG for the game
- preview PNG: visual order, clipping, preserved canvas scale, and timing feel
- individual 

### docs/reference/PROMPTING_IMAGE_MODELS.md

# Prompting Image Models

Use this reference when creating the first animation-safe pose, a character reference image, or a transition frame before video generation. The first pose becomes the first frame of the animation source footage.

This workflow has been tested with GPT Image 2 and Nano Banana 2, but the rules apply to any image model used before the sprite pipeline.

## First Pose Contract

Create one full-body character image on exact chroma green:

- Hex: `#00FF00`
- RGB: `0,255,0`

The green background must be perfectly flat. Require no shadows, no floor, no gradients, no props, no lighting falloff, and no background objects.

The character design must not use this green anywhere, including clothing, gems, magic, outlines, antialiasing, or glow.

Frame the character for animation, not as a portrait:

- full body visible from head to feet
- full weapon, cape, hair, and loose cloth visible
- no cropping
- character centered in frame
- generous empty margin on all sides
- no part of the character enters the outer 20-30% border area
- for idle/game animation, character height is roughly 40-50% of the canvas unless a larger scale is intentional

Video models often animate wider than the first pose suggests. If a weapon, cape, hand, foot, hair, or effect starts near an edge, it may leave the frame during motion.

## Transition Frames

For non-idle animations, prefer creating a transition pose with the image model before using the video model.

Give the image model the base character reference or idle frame, then ask for the first frame of the new animation as a small transition away from idle. Do not ask for the most extreme action pose first. This helps attack, run, jump, and magic animations flow naturally out of idle and avoids spending video-model seconds on idle.

Use bridge frames when a final pose is good but does not connect well back to idle or into the next animation. Creating one or a few image-model bridge frames is often cheaper than rerunning video.

## Prompt Requirements

Always specify:

- one character only
- full-body 2D game character
- exact starting pose
- camera/view angle
- character centered in frame
- animation-safe margins
- full weapon/effects visible
- clean readable silhouette
- stable design with clear separated limbs
- flat `#00FF00` background only
- no text, watermark, border, shadow, floor, props, or extra effects

## First Pose Prompt Template

```text
Create one full-body 2D game character image for sprite animation source footage.

Character: [describe character, outfit, weapon, proportions, style].
Pose: [exact starting pose].
Camera/view: [side view, 3/4 side view, front view, etc.].

Requirements:
- one character only
- full body visible from head to feet
- full weapon, hair, cape, loose cloth, and accessories visible
- character centered in frame
- generous animation-safe empty margin on all sides
- no part of the character enters the outer 20-30% border area
- character occupies roughly 40-50% of canvas height
- clean readable silhouette with separated limbs
- stable design and proportions
- flat exact chroma green background only: #00FF00, RGB 0,255,0
- do not use #00FF00 anywhere on the character

Do not include text, watermark, border, floor, shadow, props, lighting falloff, gradients, background objects, extra characters, or extra effects.
```

## Transition Frame Prompt Template

```text
Use the uploaded character reference as the exact design reference.

Create the first transition frame for a [animation name] animation. Keep the character centered, keep the same camera angle, keep the same scale, keep the same flat #00FF00 background, and preserve the same generous margins.

The pose should be a small transition away from idle toward [describe action], not the most extreme action pose.

Preserve exact character design, outfit, proportions, weapon, silhouette, and 2D art style. Full body and full weapon must remain visible. No cropping. No text, watermark, border, shadow, f

### docs/reference/PROMPTING_VIDEO_MODELS.md

# Prompting Video Models

Use this reference when animating an image-model pose into source footage for frame extraction. The output is controlled sprite-pipeline footage, not cinematic video.

Kling is the main target, but the same constraints apply to other image-to-video models.

## Core Prompt Rules

Use the image-model result as the first frame. The video prompt must be strict and mechanical.

Always include:

- use uploaded image as exact first frame
- preserve exact character design, outfit, proportions, weapon, silhouette, and 2D art style
- locked camera
- no zoom, no pan, no rotation, no cuts
- character always centered in frame
- full body, weapon, and all motion fully inside the frame at all times
- no horizontal travel across the screen
- maintain flat chroma green background `#00FF00` with no variation
- no shadows on the ground or background
- no lighting changes or gradients
- no motion blur

Kling tends to drift toward cinematic motion, interpolation shortcuts, and pretty effects. Pull it back toward deterministic motion, sprite readability, and clean frame extraction.

## Animation Constraints

Require motion readable in approximately 12-24 frames:

- each phase is clearly visible: anticipation, action, follow-through, recovery
- no frame skipping
- no pose snapping
- no teleporting between poses
- each frame shows visible progression from the previous frame
- motion stays compact and contained within the frame

Always describe the animation as a step-by-step mechanical sequence, not as a vague action.

Bad:

```text
fast overhead sword slash
```

Good:

```text
Use the uploaded image as the exact first frame. Slight weight shift. Arms raise weapon overhead. Brief anticipation pause. Forward step. Downward strike. Follow-through. Return to ready stance.
```

If using a transition frame, reference the uploaded image as the starting pose rather than saying "start from idle stance".

## Character Control Constraints

Always include:

- do not change anatomy or proportions
- do not add or remove limbs
- do not duplicate weapons or hands
- do not warp hands or fingers
- do not change costume or accessories
- weapon remains consistent in position, ownership, and orientation unless switching hands is intentional

## Style Constraints

Always include:

- maintain 2D sprite readability
- prioritize clear silhouette over realism
- avoid cinematic effects
- avoid depth of field
- avoid particle spam that obscures the character

Non-vertical effects are usually safer than vertical effects. A magic trail during an attack is less likely to cause character drift than landing dust or takeoff wind.

For vertical animations like jump, fall, and landing, generate clean body motion first. Add landing dust, takeoff wind, or other vertical effects separately as their own overlay/effect animation.

## Video Prompt Template

```text
Use the uploaded image as the exact first frame.

Preserve the exact character design, outfit, proportions, weapon, silhouette, and 2D art style. Locked camera. No zoom, no pan, no rotation, no cuts, no camera shake. Character remains centered in frame. Full body, full weapon, hair, cape, cloth, and all motion stay fully inside the frame at all times. No horizontal travel across the screen.

Maintain a flat exact chroma green background: #00FF00, RGB 0,255,0. No background variation, no gradients, no floor, no shadows, no lighting changes, no motion blur.

Animation sequence:
1. [anticipation step]
2. [main action step]
3. [follow-through step]
4. [recovery or return-to-ready step]

Motion must be readable in approximately 12-24 frames. Each frame should show clear progression from the previous frame. No frame skipping, no pose snapping, no teleporting.

Do not change anatomy or proportions. Do not add or remove limbs. Do not duplicate weapons or hands. Do not warp hands or fingers. Do not change costume or accessories. Keep the weapon consistent.

Maintain 2D sprite readability and a clean silhouette. A

### docs/WORKSPACE_CONVENTIONS.md

# Workspace Conventions

Use these folders for the video-to-sprite-sheet workflow:

- `Videos/`: source animation videos. Keep originals here.
- `work/extracted/<character>/<action>/`: frame images extracted from one video
  animation, plus the extraction report.
- `work/matted/<character>/<action>/`: transparent PNGs produced by the light
  background matte or a future matting package.
- `work/frames/<character>/<action>_<frame-count>f_256/`: individual frames written by the
  cleanup pipeline.
- `work/previews/`: checker/guide preview sheets for inspection.
- `work/reports/`: JSON validation reports.
- `Final Sprite Sheets/<GameName>/<CharacterName>/<animation>/sheets/`:
  promoted sprite sheets ready for game integration.
- `Final Sprite Sheets/<GameName>/<CharacterName>/<animation>/frames/`:
  individual `256 x 256` PNG cells used by the promoted sheets.
- `Videos/Processed/`: original videos after their approved sprites are
  promoted.
- `Cleanup/`: old scratch outputs, rejected experiments, and non-promoted
  generated artifacts. This folder is ignored by git.
- `archive/legacy-sheet-and-generation-workflow/`: preserved old prompt/grid
  workflow.

The `work/` folder is scratch output. The durable deliverables are the source
videos in `Videos/Processed/`, promoted final sprite sheets, and the individual
frame cells that exactly match those promoted sheets. Once an animation is
approved, move every other generated artifact for that pass into `Cleanup/`.


## Capture Note

First-slice repo intake captures selected text files and a tree manifest, not a full repository archive.

## External Links

- None captured

## Media Links

- None captured
