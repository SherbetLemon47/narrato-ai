import requests
from bs4 import BeautifulSoup
import os
import re
from clint.textui import progress

def get_gutenberg_metadata_epub(url, output_dir="downloads"):
    match = re.search(r'/(\d+)', url)
    if not match:
        raise ValueError("Invalid Project Gutenberg URL format")
    book_id = match.group(1)

    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Failed to fetch the book page")

    soup = BeautifulSoup(response.text, 'html.parser')

    metadata = {}
    metadata_table = soup.find('table', {'class': 'bibrec'})
    if metadata_table:
        for row in metadata_table.find_all('tr'):
            header_tag = row.find('th')
            value_tag = row.find('td')
            if header_tag and value_tag:
                header = header_tag.get_text(strip=True)
                value = value_tag.get_text(strip=True)
                metadata[header] = value

    title = metadata.get("Title", "Unknown")
    author = metadata.get("Author", "Unknown")
    translator = metadata.get("Translator", "None")

    print("\n📘 Book Metadata:")
    print(f"Title     : {title}")
    print(f"Author    : {author}")
    print(f"Translator: {translator}")

    epub_link = None
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.endswith('.epub3.images') or href.endswith('.epub.images') or href.endswith('.epub.noimages') or href.endswith('.epub'):
            if 'epub.noimages' in href:
                epub_link = href
                break
            elif not epub_link:
                epub_link = href

    if not epub_link:
        raise Exception("No EPUB link found")

    if epub_link.startswith('/'):
        epub_link = 'https://www.gutenberg.org' + epub_link

    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{title.replace(' ', '_')}.epub")

    print("\n📥 Downloading EPUB...")
    print(f"EPUB URL: {epub_link}")

    with requests.get(epub_link, stream=True) as r:
        r.raise_for_status()
        total_length = r.headers.get('content-length')
        total_length = int(total_length) if total_length is not None else None

        with open(filename, 'wb') as f:
            if total_length is None:
                f.write(r.content)
            else:
                for chunk in progress.bar(r.iter_content(chunk_size=1024),
                                          expected_size=(total_length // 1024) + 1):
                    if chunk:
                        f.write(chunk)
                        f.flush()

    print(f"\n✅ EPUB downloaded: {filename}")

    cover_url = None
    img_tag = soup.find("img", {"class": "cover-art"})
    if img_tag and img_tag.get("src"):
        cover_url = img_tag["src"]


    cover_path = None
    if cover_url:
        print(f"\n🖼️  Downloading Cover Image: {cover_url}")
        try:
            cover_ext = os.path.splitext(cover_url)[1]
            cover_filename = os.path.join(output_dir, f"{title.replace(' ', '_')}_cover{cover_ext}")
            with requests.get(cover_url, stream=True) as r:
                r.raise_for_status()
                with open(cover_filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                            f.flush()
            cover_path = cover_filename
            print(f"✅ Cover image saved to: {cover_path}")
        except Exception as e:
            print("⚠️ Failed to download cover image:", e)

    return {"Title": title, "Author": author, "Translator": translator}, filename, cover_path