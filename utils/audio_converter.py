import re
import os
import soundfile as sf
import torch
import json
from kokoro import KPipeline
from utils.audio_merger import merge_audio_files
from utils.sentence_streamer import stream_sentences
from utils.subtitle_generator import generate_srt_from_subtitles_json


device = "cuda" if torch.cuda.is_available() else "cpu"


pipeline = KPipeline(lang_code="a")


def convert_to_audio(text, voice, chunk_id, output_dir):
    generator = pipeline(text, voice=voice)
    output_path = f"{output_dir}/{chunk_id}.wav"

    for _, _, audio in generator:
        sf.write(output_path, audio, 24000)
    return output_path, text


def format_name(raw_name):
    name = re.sub(r",\s*\d{4}-\d{4}", "", raw_name).strip()

    if "," in name:
        parts = [part.strip() for part in name.split(",", maxsplit=1)]
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}"
    return name


def process_introduction_audio(metadata, output_dir, voice):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    title = metadata.get("Title", "Unknown Title")
    author_raw = metadata.get("Author", "Unknown Author")
    translator_raw = metadata.get("Translator", "").strip()

    author = format_name(author_raw)
    translator = format_name(translator_raw) if translator_raw.lower() != "none" else ""

    if translator:
        intro = (
            f"Welcome, to the audiobook edition of {title}, "
            f"written by {author} and beautifully translated by {translator}. "
            "Sit back, relax, and enjoy."
        )
    else:
        intro = (
            f"Welcome, to the audiobook edition of {title} by {author}. "
            "Sit back, relax, and enjoy."
        )

    chunk_id = "introduction"
    audio_path, _ = convert_to_audio(
        text=intro, chunk_id=chunk_id, output_dir=output_dir, voice=voice
    )

    subtitle_data = [{"audio": f"{chunk_id}.wav", "text": intro}]
    subtitle_json_path = os.path.join(output_dir, "subtitles.json")

    with open(subtitle_json_path, "w", encoding="utf-8") as f:
        json.dump(subtitle_data, f, indent=2)

    generate_srt_from_subtitles_json(
        subtitle_json_path=subtitle_json_path,
        audio_dir=output_dir,
        output_srt_path=os.path.join(output_dir, "introduction.srt"),
    )

    print("Introduction Audio Generated Successfully..")

    return os.path.join(output_dir, "introduction.wav"), os.path.join(
        output_dir, "introduction.srt"
    )


def process_texts_to_audio(input_dir, output_dir, voice):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    chapter_audio_paths = []
    chapter_srt_paths = []

    for file_name in os.listdir(input_dir):
        if file_name.endswith(".txt"):
            chapter_name = os.path.splitext(file_name)[0]
            chapter_dir = os.path.join(output_dir, chapter_name)
            os.makedirs(chapter_dir, exist_ok=True)

            txt_path = os.path.join(input_dir, file_name)
            subtitle_data = []
            chunk_id = 0
            # base_name = os.path.splitext(file_name)[0]
            # audio_output_dir = os.path.join(output_dir, base_name)

            print(f"\nProcessing Chapter: {chapter_name}")

            for chunk in stream_sentences(txt_path):
                chunk_id_str = f"{chunk_id:06d}"
                # print(f"  Chunk {chunk_id_str}:")
                # print(f"  {chunk[:60]}..." if len(chunk) > 60 else f"  {chunk}")
                audio_path, text = convert_to_audio(
                    text=chunk,
                    chunk_id=chunk_id_str,
                    output_dir=chapter_dir,
                    voice=voice,
                )
                subtitle_data.append(
                    {"audio": os.path.basename(audio_path), "text": text}
                )
                chunk_id += 1

            subtitle_json_path = os.path.join(chapter_dir, "subtitles.json")
            with open(subtitle_json_path, "w", encoding="utf-8") as f:
                json.dump(subtitle_data, f, indent=2)

            merged_chapter_path = os.path.join(output_dir, f"{chapter_name}.wav")
            merge_audio_files(None, chapter_dir, merged_chapter_path)
            chapter_audio_paths.append(merged_chapter_path)

            chapter_srt_path = os.path.join(output_dir, f"{chapter_name}.srt")
            generate_srt_from_subtitles_json(
                subtitle_json_path=subtitle_json_path,
                audio_dir=chapter_dir,
                output_srt_path=chapter_srt_path,
            )
            chapter_srt_paths.append(chapter_srt_path)
            for filename in os.listdir(chapter_dir):
                file_path = os.path.join(chapter_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)


    return chapter_audio_paths, chapter_srt_paths
