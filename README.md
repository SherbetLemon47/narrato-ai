# 📖 narrato-ai

This Python script converts eBooks into audiobooks with video rendering support. It extracts chapters from EPUB files, converts them into audio using TTS, and generates a video representation.

---

## 🧰 Features

* Auto fetch eBooks from ProjectGutenberg library
* Convert `.epub` eBooks into chapter-wise and complete audiobooks
* Auto-generate subtitle files and chapter metadata
* Video generation with AI-generated images, fit for Youtube

---

## ⚒️ Tools

* BeautifulSoup for fetching book data
* Kokoro-TTS for audio-conversion
* Google Gemini for image-generation. (Future support for other providers)
* Moviepy for video generation and composition

---

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/SherbetLemon47/narrato-ai.git
cd narrato-ai
```

### 2. Create a Virtual Environment (Recommended)

Use either **virtualenv** or **conda** to isolate dependencies.

#### Using `virtualenv`:

```bash
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Or using `conda`:

```bash
conda create -n <environment_name> python=3.10
conda activate <environment_name>
```

### 3. Install Required Packages

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Configuration

Create a `.env` file in the project root directory with the necessary API keys:

```env
GEMINI_API_KEY=your_google_gemini_api_key_here
```

*Other keys may be required depending on the extensions you enable.*

---

## 🚀 Run the Application

Once everything is set up, run:

```bash
python main.py
```

Follow the interactive prompts to select your EPUB file and configure generation options.

---
## 🎓 TODO Journal

### Main Quest

- [x] Epub Downloads 
- [x] Text Extraction
- [x] Chunking
- [x] TTS
- [x] Audio Merging
- [x] Subtitle Generation
- [x] Image Generation
- [x] Video Generation

### SideQuests

- [x] Voice Options
- [x] Individual Chapter/Section Audios
- [ ] Youtube Integration


---

## 🤝 Contributions

Feel free to fork, enhance, or raise issues. PRs are welcome!

---

## 📄 License

MIT License – see [`LICENSE`](LICENSE) for details.