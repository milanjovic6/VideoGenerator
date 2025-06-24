import os
from PIL import Image
import numpy as np
from moviepy.editor import ImageClip, CompositeVideoClip, ColorClip, concatenate_videoclips

W, H = 1920, 1080
IMAGE_FOLDER = "slike"
OUTPUT_FILE = "output.mp4"


def prepare_image(path):
    """Resize image to fit 1080p frame on a black background."""
    img = Image.open(path).convert("RGB")
    scale = H / img.height
    new_w = int(img.width * scale)
    img = img.resize((new_w, H), Image.LANCZOS)
    background = Image.new("RGB", (W, H), (0, 0, 0))
    x = (W - new_w) // 2
    background.paste(img, (x, 0))
    return background


def slide_clip(img, direction, duration=3):
    arr = img if isinstance(img, Image.Image) else Image.fromarray(img)
    clip = ImageClip(np.array(arr)).set_duration(duration)
    if direction == "bottom":
        clip = clip.set_position(lambda t: (0, H - H * (t / duration)))
    else:
        clip = clip.set_position(lambda t: (0, -H + H * (t / duration)))
    return CompositeVideoClip([clip], size=(W, H))


if __name__ == "__main__":
    image_files = sorted(
        [f for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    )
    images = [prepare_image(os.path.join(IMAGE_FOLDER, f)) for f in image_files]

    directions = ["bottom", "top", "bottom"]
    intro_clips = [slide_clip(images[i], directions[i]) for i in range(3)]
    intro = concatenate_videoclips(intro_clips)

    total_width = W * len(images)
    panorama = Image.new("RGB", (total_width, H))
    x = 0
    for img in images:
        panorama.paste(img, (x, 0))
        x += W

    pan_clip = ImageClip(np.array(panorama)).set_duration(5)
    scroll_dist = total_width + W
    pan_clip = pan_clip.set_position(lambda t: (-scroll_dist * (t / 5), 0))
    scroll = CompositeVideoClip([pan_clip], size=(W, H))

    ending = ColorClip((W, H), color=(0, 0, 0), duration=8)

    final_video = concatenate_videoclips([intro, scroll, ending])
    final_video.write_videofile(OUTPUT_FILE, fps=30)
