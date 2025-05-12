import re
import os
from sentence_streamer import stream_sentences
from kokoro import KPipeline
import soundfile as sf
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"


pipeline = KPipeline(lang_code='a')
def convert_to_audio(text, chunk_id, output_dir):
    generator = pipeline(text, voice='af_heart')
    for i, (gs, ps, audio) in enumerate(generator):
        sf.write(f'{output_dir}/{chunk_id}.wav', audio, 24000)

def format_name(raw_name):
    name = re.sub(r',\s*\d{4}-\d{4}', '', raw_name).strip()

    if ',' in name:
        parts = [part.strip() for part in name.split(',', maxsplit=1)]
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}"
    return name

def process_introduction_audio(metadata, output_dir):
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
            "Let the words transport you to another time and place."
        )
    else:
        intro = (
            f"Welcome, to the audiobook edition of {title} by {author}. "
            "Sit back, relax, and enjoy the story as it unfolds."
        )

    convert_to_audio(text=intro, chunk_id="Introduction", output_dir=output_dir)
    print("Introduction Audio Generated Successfully..")
    

def process_texts_to_audio(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    chunk_id = 0
    for file_name in os.listdir(input_dir):
        if file_name.endswith(".txt"):
            txt_path = os.path.join(input_dir, file_name)
            # base_name = os.path.splitext(file_name)[0]
            # audio_output_dir = os.path.join(output_dir, base_name)

            os.makedirs(output_dir, exist_ok=True)

            print(f"\nProcessing file: {file_name}")

            for chunk in stream_sentences(txt_path):
                chunk_id_str = f"{chunk_id:06d}"
                # print(f"  Chunk {chunk_id_str}:")
                # print(f"  {chunk[:60]}..." if len(chunk) > 60 else f"  {chunk}")

                convert_to_audio(chunk, chunk_id_str, output_dir)
                chunk_id += 1

            print(f"  --> {chunk_id} chunks processed and saved to {output_dir}")
            print("-" * 60)
