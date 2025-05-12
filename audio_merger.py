from pydub import AudioSegment
import os

def merge_audio_files(intro_path, folder_path, output_file):
    combined = AudioSegment.empty()

    if intro_path:
        combined=AudioSegment.from_wav(intro_path)
    wav_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.wav')])

    for filename in wav_files:
        file_path = os.path.join(folder_path, filename)
        audio = AudioSegment.from_wav(file_path)
        combined += audio

    combined.export(output_file, format="wav")
    print(f"Combined audio saved to: {output_file}")

