import os
import re
from bs4 import BeautifulSoup
from ebooklib import epub, ITEM_DOCUMENT
from InquirerPy import inquirer


def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title).strip().replace(" ", "_")


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
                part_title_str = (
                    part_title.title.strip()
                    if isinstance(part_title, epub.Link)
                    else str(part_title).strip()
                )
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
                    chapters.append({"title": full_title, "content": content})

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
                    chapters.append(
                        {"title": title, "content": "\n".join(content).strip()}
                    )

    if debug:
        print(f"\nExtracted {len(chapters)} chapters.")

    choose_and_save_chapters(chapters, output_dir, debug=debug)

    return chapters


def choose_and_save_chapters(chapters, output_dir, debug=False):
    choices = [
        {"name": f"{idx+1:02d}. {chapter['title']}", "value": idx, "enabled": True}
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
            f.write(chapter["content"])

        if debug:
            print(f"Saved: {file_name}")
