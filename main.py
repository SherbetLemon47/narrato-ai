import os
import subprocess
from yaspin import yaspin
from InquirerPy import inquirer
from InquirerPy.separator import Separator
from utils.downloader import get_gutenberg_metadata_epub
from utils.ebook_parser import extract_chapters_from_epub
from utils.audio_converter import process_texts_to_audio, process_introduction_audio, format_name
from utils.audio_merger import merge_audio_files
from utils.subtitle_generator import merge_srt_files
from utils.video_generator import (
    merge_video_files,
    generate_intro_video,
    process_chapters_from_directory,
)

supported_audios = [
    Separator(f"-- Female Voices --"),
    "af_heart",
    "af_bella",
    "af_nicole",
    "af_aoede",
    Separator(f"-- Male Voices --"),
    "am_adam",
    "am_fenrir",
    "am_michael",
    "am_puck",
]

confirm = False
while not confirm:
    command = "cls" if os.name == "nt" else "clear"
    subprocess.run(command, shell=True)
    ebookLoc = inquirer.select(
        message="Where is the eBook located:",
        choices=["Project Gutenberg", "Local Device"],
    ).execute()
    link = None
    loc = None
    if ebookLoc == "Project Gutenberg":
        link = inquirer.text(message="Paste Link to eBook Page:").execute()
    else:
        loc = inquirer.text(
            message="Paste location to eBook (.epub file only):"
        ).execute()

    confirm = inquirer.confirm(message="Confirm?").execute()
    if not confirm:
        continue
    print("Starting Ebook Parsing....")
    if ebookLoc == "Project Gutenberg":
        print("Downloading eBook from Project Gutenberg...")
        metadata = None
        ebook = None
        cover_path = None
        try:
            metadata, ebook, cover_path = get_gutenberg_metadata_epub(link, "./ebooks/")
        except:
            raise ValueError("Downloading failed, please ensure link is accurate.")

        chapters = extract_chapters_from_epub(
            ebook, output_dir=f"{metadata['Title']}/chapters/"
        )

        confirm = inquirer.confirm(
            message="Proceed with Audiobook Conversion?"
        ).execute()
        if not confirm:
            break

        voice_choice = inquirer.select(
            message="Select a voice for audiobook generation:",
            choices=supported_audios,
        ).execute()

        print(voice_choice)

        full_audiobook = inquirer.confirm(
            message="Do you want Full Audiobook? (Default: Separated audiobook for each chapter) (Y/N)"
        ).execute()

        print("Starting AudioBook Generation")

        with yaspin(text="🎙️ Generating Introduction...", color="cyan") as spinner:
            intro_audio_path, intro_srt_path = process_introduction_audio(
                metadata, output_dir=f"{metadata['Title']}/audio/", voice=voice_choice
            )
            spinner.ok("✅")

        with yaspin(text="🎧 Generating Chapter Audio... ", color="cyan") as spinner:
            chapter_audio_paths, chapter_srt_paths = process_texts_to_audio(
                input_dir=f"{metadata['Title']}/chapters/",
                output_dir=f"{metadata['Title']}/audio/",
                voice=voice_choice,
            )
            spinner.ok("✅")

        with yaspin(
            text="🎧 Generating Introduction Video... ", color="cyan"
        ) as spinner:
            generate_intro_video(
                book_title=metadata["Title"],
                book_author=format_name(metadata["Author"]),
                book_image=cover_path,
                audio_path=intro_audio_path,
            )
            spinner.ok("✅")

        with yaspin(text="🎥 Generating Chapter Videos... ", color="cyan") as spinner:
            process_chapters_from_directory(
                input_dir=f"{metadata['Title']}/chapters/",
                audio_dir=f"{metadata['Title']}/audio/",
                cover_path=cover_path,
                book_title=metadata["Title"],
                book_author=format_name(metadata["Author"]),
                num_images=3
            )
            spinner.ok("✅")

        if full_audiobook:
            with yaspin(text="🔊 Merging Audio Files...", color="cyan") as spinner:
                merge_audio_files(
                    intro_path=intro_audio_path,
                    folder_path=None,
                    output_file=f"{metadata['Title']}/audiobook.wav",
                    audio_files=[intro_audio_path] + chapter_audio_paths,
                )
                spinner.ok("✅")

            with yaspin(text="📝 Merging Subtitle Files...", color="cyan") as spinner:
                final_srt_path = f"{metadata['Title']}/audiobook.srt"
                merge_srt_files(
                    srt_paths=[intro_srt_path] + chapter_srt_paths,
                    audio_paths=[intro_audio_path] + chapter_audio_paths,
                    output_path=final_srt_path,
                )
                spinner.ok("✅")
            with yaspin(text="🎬 Merging Video Files...", color="cyan") as spinner:
                video_paths = [intro_audio_path.replace(".wav", ".mp4")] + [
                    path.replace(".wav", ".mp4") for path in chapter_audio_paths
                ]
                merged_video_path = f"{metadata['Title']}/audiobook.mp4"
                merge_video_files(video_paths, output_path=merged_video_path)
                spinner.ok("✅")
    if not confirm:
        continue
