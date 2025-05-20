import os
import io
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from PIL import Image

load_dotenv(".env")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

TEXT_MODEL = "gemini-2.0-flash"
IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"


def generate_image_prompts(chapter_text: str, num_prompts: int = 5) -> list[str]:
    prompt = (
        f"Read the following chapter and generate {num_prompts} distinct and creative prompts for 16:9 image generation that tell the story. "
        f"Make each prompt vivid, specific, and visually descriptive. Each prompt should mention size and command to generate an image. Do not number them or add any extra text. Adhere return type to json format, return an array containing {num_prompts} prompts"
        f"The image must be in 16:9 format.\n\nChapter:\n{chapter_text}"
    )
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    )
    raw_text = response.text.strip()
    try:
        prompts_list = json.loads(raw_text)
        return prompts_list
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return []


def generate_image(prompt: str) -> bytes | None:
    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                return part.inline_data.data
    except Exception as e:
        print(f"Error generating image for prompt '{prompt}': {e}")
    return None


def save_image(image_data: bytes, filename: str, output_dir: str) -> str | None:
    try:
        os.makedirs(output_dir, exist_ok=True)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        image = image.resize((1920, 1080), Image.Resampling.LANCZOS)
        path = os.path.join(output_dir, f"{filename}.png")
        image.save(path)
        return path
    except Exception as e:
        print(f"Error saving image '{filename}': {e}")
    return None


def generate_images_from_chapter(
    chapter_text: str, num_images: int, output_dir: str
) -> list[str]:
    prompts = generate_image_prompts(chapter_text, num_images)
    image_paths = []
    for idx, prompt in enumerate(prompts, start=1):
        print(f"\nGenerating image {idx} for prompt:\n{prompt}")
        image_data = generate_image(prompt)
        if image_data:
            path = save_image(image_data, f"image_{idx}", output_dir)
            if path:
                image_paths.append(path)
        else:
            print(f"Failed to generate image {idx}.")
    return image_paths
