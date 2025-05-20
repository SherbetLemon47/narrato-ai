import os
import re
from bs4 import BeautifulSoup
from ebooklib import epub, ITEM_DOCUMENT
from InquirerPy import inquirer


def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title).strip().replace(" ", "_")


ROMAN_NUMERAL_MAP = {
    "M": 1000,
    "CM": 900,
    "D": 500,
    "CD": 400,
    "C": 100,
    "XC": 90,
    "L": 50,
    "XL": 40,
    "X": 10,
    "IX": 9,
    "V": 5,
    "IV": 4,
    "I": 1,
}


def roman_to_int(roman):
    roman = roman.upper()
    i = 0
    num = 0
    while i < len(roman):
        if i + 1 < len(roman) and roman[i : i + 2] in ROMAN_NUMERAL_MAP:
            num += ROMAN_NUMERAL_MAP[roman[i : i + 2]]
            i += 2
        elif roman[i] in ROMAN_NUMERAL_MAP:
            num += ROMAN_NUMERAL_MAP[roman[i]]
            i += 1
        else:
            return None
    return num


def convert_title_roman_numerals(title):
    def replacer(match):
        roman = match.group(1)
        integer = roman_to_int(roman)
        if integer:
            return match.group(0).replace(roman, str(integer))
        return match.group(0)

    title = re.sub(
        r"\b(Chapter|Book|Part)\s+([IVXLCDM]+)\b",
        lambda m: f"{m.group(1)} {roman_to_int(m.group(2)) or m.group(2)}",
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r"^([IVXLCDM]+)(\.?)(\s|$)",
        lambda m: f"{roman_to_int(m.group(1)) or m.group(1)}{m.group(2)}{m.group(3)}",
        title,
    )

    return title


def strip_redundant_heading(title, content):
    lines = content.strip().splitlines()
    if not lines:
        return content

    first_line = lines[0].strip()
    normalized_title = re.sub(r"\W+", "", title).lower()
    normalized_first_line = re.sub(r"\W+", "", first_line).lower()

    if (
        normalized_first_line in normalized_title
        or normalized_title in normalized_first_line
    ):
        return "\n".join(lines[1:]).strip()

    if re.match(r"^(chapter\s*)?[ivxlcdm\d]+\.*$", first_line, re.IGNORECASE):
        return "\n".join(lines[1:]).strip()

    return content


def extract_chapter_text(soup, start_id, next_id=None):
    content = []
    start_elem = soup.find(id=start_id)
    if not start_elem:
        return ""

    current = (
        start_elem.find_next_sibling()
        if start_elem.name in ["h1", "h2", "h3"]
        else start_elem
    )
    while current:
        if next_id and current.get("id") == next_id:
            break
        if (
            current.name in ["h1", "h2", "h3"]
            and "chapter" in current.get_text().lower()
        ):
            break
        content.append(current.get_text())
        current = current.find_next_sibling()

    return "\n".join(content).strip()


def save_chapter_to_file(index, title, content, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    safe_title = sanitize_filename(title)
    file_name = f"{index:02d}_{safe_title}.txt"
    file_path = os.path.join(output_dir, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"{content}")


def extract_chapters_from_epub(epub_file, output_dir="chapters", debug=False):
    if not os.path.exists(epub_file):
        raise FileNotFoundError(f"EPUB file not found: {epub_file}")

    book = epub.read_epub(epub_file)
    chapters = []

    def process_toc_items(items, prefix=""):
        for idx, item in enumerate(items):
            if isinstance(item, tuple) and len(item) == 2:
                part_title, children = item

                if isinstance(part_title, epub.Link):
                    part_title_str = part_title.title.strip()
                elif isinstance(part_title, epub.Section):
                    part_title_str = part_title.title.strip()
                else:
                    part_title_str = str(part_title).strip()

                new_prefix = f"{prefix} - {part_title_str}".strip(" -")
                process_toc_items(children, new_prefix)

            elif isinstance(item, epub.Link):
                title = item.title.strip()
                if title.lower() in [
                    "cover",
                    "title page",
                    "copyright",
                ] or title.lower().startswith("by"):
                    continue

                full_title = f"{prefix} - {title}".strip(" -")

                href_parts = item.href.split("#")
                file_name = href_parts[0]
                fragment_id = href_parts[1] if len(href_parts) > 1 else None

                doc = next(
                    (
                        d
                        for d in book.get_items_of_type(ITEM_DOCUMENT)
                        if d.file_name.endswith(file_name)
                    ),
                    None,
                )
                if not doc:
                    continue

                soup = BeautifulSoup(doc.get_content().decode("utf-8"), "html.parser")

                next_fragment = None
                for j in range(idx + 1, len(items)):
                    if isinstance(items[j], epub.Link):
                        next_parts = items[j].href.split("#")
                        if next_parts[0] == file_name and len(next_parts) > 1:
                            next_fragment = next_parts[1]
                            break
                        else:
                            break

                if fragment_id:
                    content = extract_chapter_text(soup, fragment_id, next_fragment)
                else:
                    content = soup.get_text().strip()

                if content:
                    cleaned_content = strip_redundant_heading(full_title, content)
                    full_title = convert_title_roman_numerals(full_title)
                    chapters.append({"title": full_title, "content": cleaned_content})

    process_toc_items(book.toc)

    if not chapters:
        for doc in sorted(
            book.get_items_of_type(ITEM_DOCUMENT), key=lambda d: d.file_name
        ):
            soup = BeautifulSoup(doc.get_content().decode("utf-8"), "html.parser")
            chapter_headers = soup.find_all(
                ["h1", "h2", "h3"], string=re.compile(r"(chapter|book)", re.I)
            )

            for header in chapter_headers:
                title = header.get_text().strip()
                content = []
                for tag in header.find_next_siblings():
                    if tag.name in ["h1", "h2", "h3"] and re.search(
                        r"(chapter|book)", tag.get_text(), re.I
                    ):
                        break
                    content.append(tag.get_text())
                if content:
                    cleaned_content = strip_redundant_heading(
                        title, "\n".join(content).strip()
                    )
                    title = convert_title_roman_numerals(title)
                    chapters.append({"title": title, "content": cleaned_content})

    if debug:
        print(f"\nExtracted {len(chapters)} chapters.")

    choose_and_save_chapters(chapters, output_dir, debug=debug)

    return chapters


def choose_and_save_chapters(chapters, output_dir, debug=False):
    choices = [
        {"name": f"{idx+1:02d}. {chapter['title']}", "value": idx, "enabled": False}
        for idx, chapter in enumerate(chapters)
    ]

    selected_indices = inquirer.checkbox(
        message="Select / Deselect chapters to save:",
        choices=choices,
        instruction="(Use space to select, enter to confirm)",
    ).execute()

    if not selected_indices:
        print("No chapters selected. Exiting without saving.")
        return

    for save_idx, original_idx in enumerate(selected_indices, start=1):
        chapter = chapters[original_idx]
        file_index = f"{save_idx:03d}"
        safe_title = sanitize_filename(chapter["title"])
        file_name = f"{file_index}_{safe_title}.txt"
        file_path = os.path.join(output_dir, file_name)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(chapter["title"] + "\n\n......\n\n" + chapter["content"])

        if debug:
            print(f"Saved: {file_name}")
