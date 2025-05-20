import re
import random

def stream_sentences(filepath):
    sentence_endings = re.compile(r'(?<=[.!?])\s+')
    sentence_buffer = []

    with open(filepath, 'r', encoding='utf-8') as file:
        buffer = ""
        for line in file:
            buffer += ' ' + line.strip()
            sentences = sentence_endings.split(buffer)

            if re.search(r'[.!?]["\']?\s*$', buffer):
                buffer = ""
            else:
                buffer = sentences.pop() if sentences else ""

            sentence_buffer.extend(sentences)

            while len(sentence_buffer) >= 2:
                chunk_size = min(random.choice([2, 3]), len(sentence_buffer))
                chunk = ' '.join(sentence_buffer[:chunk_size])
                yield chunk
                sentence_buffer = sentence_buffer[chunk_size:]

        if buffer:
            sentence_buffer.append(buffer.strip())

        if sentence_buffer:
            yield ' '.join(sentence_buffer)
