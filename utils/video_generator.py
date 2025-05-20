import os
import re
import torch
from PIL import Image, ImageFont, ImageDraw, Image
from moviepy import (
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
    TextClip,
    ColorClip,
    ImageSequenceClip,
)
from pydub import AudioSegment
from utils.ai_workflows import generate_images_from_chapter


def get_audio_duration(audio_path: str) -> float:
    audio = AudioSegment.from_file(audio_path)
    return audio.duration_seconds


def create_spinning_disc_video(
    disc_path: str,
    record_size: int = 300,
    duration: int = 5,
    fps: int = 30,
):
    disc = (
        ImageClip(disc_path).resized((record_size, record_size)).with_duration(duration)
    )
    return disc.rotated(lambda t: 360 * t / 2).with_fps(fps)
    # final = CompositeVideoClip(
    #     [spinning], size=(record_size, record_size)
    # ).with_duration(duration)
    # final.write_videofile(
    #     output_path, codec="libx264", fps=fps, preset="ultrafast", audio=False
    # )


def generate_static_text_image(
    book_title: str,
    author: str,
    chapter_title: str,
    font_path: str,
    text_color: str,
    max_width: int,
    max_height: int,
) -> str:
    dummy = Image.new("RGBA", (10, 10))
    draw = ImageDraw.Draw(dummy)

    def wrap_text(line: str, font: ImageFont.FreeTypeFont):
        words = line.split()
        lines = []
        current = ""
        for w in words:
            trial = (current + " " + w).strip()
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines

    low, high = 10, 120
    best = None
    while low <= high:
        mid = (low + high) // 2
        t_font = ImageFont.truetype(font_path, mid)
        a_font = ImageFont.truetype(font_path, int(mid * 0.8))
        c_font = ImageFont.truetype(font_path, int(mid * 0.8))

        wrapped_info = []
        total_heights = []
        for text, font in [
            (book_title, t_font),
            (author, a_font),
            (chapter_title, c_font),
        ]:
            lines = wrap_text(text, font)
            wrapped_info.append((lines, font))
            for ln in lines:
                bbox = font.getbbox(ln)
                total_heights.append(bbox[3] - bbox[1])

        total_h = sum(total_heights) + 10 * (len(total_heights) - 1)
        if total_h <= max_height:
            best = (t_font, a_font, c_font, wrapped_info, total_h)
            low = mid + 1
        else:
            high = mid - 1

    if best is None:
        raise RuntimeError("Text is too tall to fit even at the smallest font size.")

    t_font, a_font, c_font, wrapped_info, total_h = best
    img = Image.new("RGBA", (max_width, max_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = (max_height - total_h) // 2
    for lines, font in wrapped_info:
        for ln in lines:
            w = draw.textlength(ln, font=font)
            draw.text(((max_width - w) // 2, y), ln, font=font, fill=text_color)
            bbox = font.getbbox(ln)
            line_h = bbox[3] - bbox[1]
            y += line_h + 10

    out_path = f"temp_text_{book_title[:4]}_{chapter_title[:4]}.png"
    img.save(out_path)
    return out_path


def create_overlayed_video(
    background_video,
    output_path: str,
    book_title: str,
    book_author: str,
    chapter_title: str,
    center_image_path: str = None,
    font_path: str = "Rye.ttf",
    disc_image_path: str = "disc.png",
    video_width: int = 1920,
    final_height: int = 1080,
    overlay_height: int = 400,
    record_size: int = 300,
    center_img_width: int = 115,
    center_img_height: int = 200,
    text_color: str = "white",
    fps: int = 24,
):
    base_video = background_video
    duration = base_video.duration

    cx = 50 + (record_size - center_img_width) // 2
    cy = (overlay_height - record_size) // 2 + (record_size - center_img_height) // 2

    spinning_disc = create_spinning_disc_video(
        disc_path=disc_image_path, duration=duration, fps=fps, record_size=record_size
    ).with_position((50, (overlay_height - record_size) // 2))

    center_on_disc = (
        ImageClip(center_image_path)
        .resized((center_img_width, center_img_height))
        .with_duration(duration)
        .with_position((cx, cy))
    )

    # record_clip = CompositeVideoClip(
    #     [spinning_disc, center_on_disc], size=(video_width, overlay_height)
    # ).with_duration(duration)

    text_area_width = video_width - record_size - 100
    # text_img = generate_text_image(
    #     [book_title, book_author, chapter_title],
    #     text_area_width,
    #     overlay_height,
    #     font_path,
    #     text_color,
    # )
    text_png = generate_static_text_image(
        book_title,
        book_author,
        chapter_title,
        font_path,
        text_color,
        text_area_width,
        overlay_height,
    )

    text_clip = (
        ImageClip(text_png, is_mask=False)
        .with_duration(duration)
        .with_fps(fps)
        .with_position((record_size + 100, 0))
    )

    # overlay_clip = CompositeVideoClip(
    #     [record_clip, text_clip], size=(video_width, overlay_height)
    # ).with_position(("center", 0))

    final_video = CompositeVideoClip(
        [base_video, spinning_disc, center_on_disc, text_clip],
        size=(video_width, final_height),
    ).with_duration(duration)

    final_video.write_videofile(
        output_path,
        threads=6,
        fps=fps,
        audio_codec="aac",
        ffmpeg_params=[
            "-c:v",
            "h264_nvenc" if torch.cuda.is_available() else "libx264",
        ],
    )


def merge_video_files(video_paths, output_path):
    clips = []
    for video_path in video_paths:
        if os.path.exists(video_path):
            clips.append(VideoFileClip(video_path))
        else:
            print(f"⚠️ Skipping missing file: {video_path}")

    if not clips:
        raise ValueError("No valid video files provided for merging.")

    final_clip = concatenate_videoclips(clips, method="compose")
    final_clip.write_videofile(
        output_path,
        codec="h264_nvenc" if torch.cuda.is_available() else "libx264",
        audio_codec="aac",
        logger=None,
    )


def generate_video(
    chapter_text: str,
    audio_path: str,
    book_title: str,
    book_author: str,
    chapter_title: str,
    book_image: str,
    output_dir: str,
    num_images: int = 1,
) -> str:
    duration = get_audio_duration(audio_path)

    if not chapter_text.strip() or chapter_text.strip() == "":
        print("No chapter text detected. Generating default video...")
        return generate_intro_video(
            audio_path=audio_path,
            book_image=book_image,
            book_title=book_title,
            book_author=book_author,
        )

    print("Starting image generation from chapter...")
    image_paths = generate_images_from_chapter(chapter_text, num_images, output_dir)

    if not image_paths:
        raise RuntimeError("No images generated to create video.")

    video_path = os.path.join(output_dir, f"{chapter_title}.mp4")
    print("Creating video from generated images...")

    try:
        image_duration = duration / len(image_paths)
        final_video = ImageSequenceClip(
            image_paths, durations=[image_duration] * len(image_paths)
        )
        audio = AudioFileClip(audio_path).subclipped(0, duration)
        final_video = final_video.with_audio(audio)
        result = create_overlayed_video(
            background_video=final_video,
            output_path=video_path,
            center_image_path=book_image,
            book_author=book_author,
            chapter_title=chapter_title,
            book_title=book_title,
        )
    finally:
        for img_path in image_paths:
            try:
                os.remove(img_path)
            except Exception as e:
                print(f"Error deleting {img_path}: {e}")

    return result

def format_chapter_title(title):
    title = re.sub(r'^\d+_', '', title)
    title = title.replace('_', ' ')
    title = re.sub(r'\b0+(\d+)\b', r'\1', title)
    return title

def process_chapters_from_directory(
    input_dir: str,
    audio_dir: str,
    cover_path: str,
    book_title: str,
    book_author: str,
    num_images: int,
):
    txt_files = sorted([f for f in os.listdir(input_dir) if f.endswith(".txt")])

    for txt_file in txt_files:
        chapter_file_path = os.path.join(input_dir, txt_file)

        with open(chapter_file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        if "\n\n......\n\n" not in raw_text:
            print(f"Skipping {txt_file}: separator not found.")
            continue

        _, chapter_content = raw_text.split("\n\n......\n\n", 1)

        audio_path = os.path.join(audio_dir, f"{os.path.splitext(txt_file)[0]}.wav")
        chapter_title = format_chapter_title(os.path.splitext(txt_file)[0])
        output_path = os.path.join(audio_dir, f"{chapter_title}.mp4")

        print(f"Processing chapter: {chapter_title}")

        generate_video(
            chapter_text=chapter_content,
            audio_path=audio_path,
            book_title=book_title,
            book_author=book_author,
            chapter_title=chapter_title,
            book_image=cover_path,
            output_dir=os.path.dirname(output_path),
            num_images=num_images,
        )


def generate_intro_video(book_title, book_author, book_image, audio_path):
    video_width, video_height = 1920, 1080
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration

    with Image.open(book_image) as img:
        img = img.convert("RGB")
        img_ratio = img.width / img.height
        new_width = int(video_height * img_ratio)
        resized_img = img.resize((new_width, video_height), Image.Resampling.LANCZOS)
        temp_image_path = "temp_resized_cover.jpg"
        resized_img.save(temp_image_path)

    image_clip = (
        ImageClip(temp_image_path).with_duration(duration).with_position((0, 0))
    )

    text_x = image_clip.w + 40

    title_txt = TextClip(
        text=book_title,
        font_size=70,
        color="white",
        font="Rye.ttf",
        size=(video_width - text_x - 80, None),
        method="caption",
    )
    title_txt = title_txt.with_position(
        (text_x, video_height // 2 - 100)
    ).with_duration(duration)

    author_txt = TextClip(
        text=f"by {book_author}",
        font_size=50,
        color="white",
        font="Montserrat.ttf",
        method="caption",
        size=(video_width - text_x - 80, None),
    )
    author_txt = author_txt.with_position(
        (text_x, video_height // 2 + 20)
    ).with_duration(duration)

    background = ColorClip(
        size=(video_width, video_height), color=(51, 51, 153), duration=duration
    )

    video = CompositeVideoClip(
        [background, image_clip, title_txt, author_txt], size=(1920, 1080)
    )
    video = video.with_duration(duration)
    video = video.with_audio(audio_clip)

    output_path = audio_path.replace(".wav", ".mp4")

    video.write_videofile(
        output_path,
        fps=24,
        codec="h264_nvenc" if torch.cuda.is_available() else "libx264",
        logger=None,
    )

    if os.path.exists(temp_image_path):
        os.remove(temp_image_path)

    return output_path