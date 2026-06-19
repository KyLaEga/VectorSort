# VectorSort

<div align="center">
  <img src="https://img.shields.io/badge/PySide6-GUI-blue?style=for-the-badge" alt="PySide6">
  <img src="https://img.shields.io/badge/PyTorch-AI-orange?style=for-the-badge" alt="PyTorch">
  <img src="https://img.shields.io/badge/FAISS-Vectors-green?style=for-the-badge" alt="FAISS">
</div>

**VectorSort** is a powerful, offline, cross-platform desktop application designed to sort, filter, and cluster video and audio files based on reference media. Under the hood, it uses state-of-the-art neural networks (SigLIP for vision, AST for audio) and Facebook's FAISS library for instantaneous vector matching.

---

## 🚀 Features

- **Hybrid AI Loading:** AI models are downloaded automatically on first run directly within the app.
- **Multimodal AI:** Analyzes both the visual frames (using Google's `SigLIP`) and the audio tracks (using MIT's `AST`).
- **O(1) Vector Search:** Uses `faiss-cpu` to match thousands of files against your Reference/Trash matrices in milliseconds.
- **Native FFmpeg:** Comes with `imageio-ffmpeg` built-in. No need to install `ffmpeg` on your system.
- **Cross-Platform & Native UI:** Beautiful dark/light themes built with Qt (PySide6) for Windows, macOS, and Linux.
- **Drag & Drop:** Just drag a folder into the app to start analyzing.

## 🛠 How it Works

VectorSort relies on a **Reference Matrix** and a **Trash Matrix**:
1. You place examples of "good" media into the `Reference_Matrix` folder.
2. You place examples of "bad" or "unwanted" media into the `Trash_Matrix` folder.
3. The app extracts vector embeddings from these files and builds a FAISS index.
4. When you drag a new folder into the app, it extracts embeddings from each file and compares them against your matrices.
5. Files are automatically sorted into `ACCEPTED`, `REJECTED`, `REVIEW`, `DUPLICATE`, or `NO_AUDIO` folders.

## ⚙️ Building from Source

If you want to build the standalone executable yourself:

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# 2. Build the application using PyInstaller
pyinstaller vectorsort.spec
```
The compiled application will be located in the `dist/` directory.

## 🌐 GitHub Actions CI/CD

This repository is configured with GitHub Actions. Whenever a new tag (`v*.*.*`) is pushed, the pipeline will automatically build `.exe`, `.app`, and Linux binaries and attach them to the Release page.

---
*Created with ❤️ for media professionals and researchers.*
