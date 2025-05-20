import json
import os
import soundfile as sf
from datetime import timedelta


def format_timestamp(seconds: float) -> str:
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    millis = int((td.total_seconds() - total_seconds) * 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def break_into_lines(text, max_chars=80):
    import textwrap
    return textwrap.wrap(text, width=max_chars)


def get_audio_duration(filepath):
    with sf.SoundFile(filepath) as f:
        frames = len(f)
        samplerate = f.samplerate
        return frames / samplerate


def generate_srt_from_subtitles_json(subtitle_json_path, audio_dir, output_srt_path):
    with open(subtitle_json_path, "r", encoding="utf-8") as f:
        subtitles = json.load(f)

    srt_entries = []
    current_time = 0.0
    index = 1

    for entry in subtitles:
        audio_filename = entry["audio"]
        text = entry["text"]

        audio_path = os.path.join(audio_dir, audio_filename)
        duration = get_audio_duration(audio_path)

        lines = break_into_lines(text)
        line_duration = duration / len(lines)

        for line in lines:
            start_ts = format_timestamp(current_time)
            end_ts = format_timestamp(current_time + line_duration)

            srt_entries.append(f"{index}\n{start_ts} --> {end_ts}\n{line}\n")
            current_time += line_duration
            index += 1

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_entries))

    print(f"SRT saved to: {output_srt_path}")


def merge_srt_files(srt_paths, audio_paths, output_path):
    current_offset = 0.0
    index = 1
    srt_output = []

    for srt_file, audio_file in zip(srt_paths, audio_paths):
        duration = get_audio_duration(audio_file)

        with open(srt_file, "r", encoding="utf-8") as f:
            blocks = f.read().strip().split("\n\n")

        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < 2:
                continue
            timestamp_line = lines[1]
            start, end = timestamp_line.split(" --> ")
            start_time = parse_srt_time(start) + current_offset
            end_time = parse_srt_time(end) + current_offset

            new_ts = f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}"
            srt_output.append(f"{index}\n{new_ts}\n" + "\n".join(lines[2:]) + "\n")
            index += 1

        current_offset += duration

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_output))
    print(f"Merged SRT saved to: {output_path}")


def parse_srt_time(srt_time_str):
    h, m, rest = srt_time_str.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
