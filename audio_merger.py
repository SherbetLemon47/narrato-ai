from pydub import AudioSegment
import os

def merge_audio_files(intro_path=None, folder_path=None, output_file=None, audio_files=None):
    combined = AudioSegment.empty()
    files_to_merge = []

    if audio_files:
        files_to_merge = audio_files
    elif folder_path:
        files_to_merge = sorted(
            [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.wav')]
        )
        if intro_path:
            files_to_merge.insert(0, intro_path)

    for file_path in files_to_merge:
        audio = AudioSegment.from_wav(file_path)
        combined += audio

    combined.export(output_file, format="wav")
    print(f"Combined audio saved to: {output_file}")
