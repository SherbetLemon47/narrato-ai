import os
import subprocess
from InquirerPy import inquirer
from downloader import get_gutenberg_metadata_epub
from ebook_parser import extract_chapters_from_epub
from audio_converter import process_texts_to_audio, process_introduction_audio
from audio_merger import merge_audio_files

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

    print(ebookLoc, link, loc)
    confirm = inquirer.confirm(message="Confirm?").execute()
    if not confirm:
        continue
    print("Starting Ebook Parsing....")
    if ebookLoc == "Project Gutenberg":
        print("Downloading eBook from Project Gutenberg...")
        metadata = None
        ebook = None
        try:
            metadata, ebook = get_gutenberg_metadata_epub(link, "./ebooks/")
        except:
            raise ValueError("Downloading failed, please ensure link is accurate.")

        extract_chapters_from_epub(ebook, output_dir=f"{metadata['Title']}/chapters/")

        confirm = inquirer.confirm(message="Proceed with Audiobook Conversion?").execute()
        if not confirm:
            break
        print("Generating Introduction..")
        process_introduction_audio(metadata,output_dir=f"{metadata['Title']}/audio/")
        print("Starting AudioBook Generation")
        print("Generating Audio Segments...")
        process_texts_to_audio(input_dir=f"{metadata['Title']}/chapters/",output_dir=f"{metadata['Title']}/audio/")
        print("Merging Audio...")
        merge_audio_files(intro_path=f"{metadata['Title']}/audio/introduction.wav",folder_path=f"{metadata['Title']}/audio/", output_file=f"{metadata['Title']}/audiobook.wav" )
    if not confirm:
        continue

