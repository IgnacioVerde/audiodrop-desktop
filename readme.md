# AudioDrop Desktop

AudioDrop is a desktop music application for Windows that combines local music playback, playlist management, YouTube search and audio downloading in a single interface.

Built with **Python and PyQt6**, the application includes its own dependency management for tools such as **yt-dlp** and **FFmpeg**, allowing it to work without requiring users to configure them manually.

## Features

* Search YouTube directly from the application
* Preview search results before downloading
* Download individual tracks as MP3
* Download complete YouTube playlists
* Local music library
* Integrated audio player
* Play / pause / previous / next controls
* Seek and volume control
* Shuffle and repeat modes
* Custom playlists
* Persistent playlist storage
* Animated audio visualizer
* Light and dark themes
* Download queue and status tracking
* Automatic detection of required external tools
* Automatic download/update of yt-dlp and FFmpeg
* Windows installer support

## Tech Stack

* **Python**
* **PyQt6**
* **Qt Multimedia**
* **yt-dlp**
* **FFmpeg / ffprobe**
* **PyInstaller**
* **Inno Setup**

## Project Structure

```text
AudioDrop/
├── main.py
├── youtube_downloader.py
├── playlist_manager.py
├── tools_manager.py
├── config_manager.py
├── styles.py
├── utils.py
├── requirements.txt
├── assets/
└── installer/
```

The exact structure may vary between versions.

## Installation for Development

### Requirements

* Windows 10/11
* Python 3
* Git

Clone the repository:

```bash
git clone https://github.com/IgnacioVerde/audiodrop-desktop.git
cd audiodrop-desktop
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

Run AudioDrop:

```bash
python main.py
```

## External Tools

AudioDrop uses:

* `yt-dlp`
* `FFmpeg`
* `ffprobe`

The application is designed to detect missing tools and manage its own local copies instead of requiring a system-wide installation.

They are stored under the user's local application data directory.

## Building

The Windows executable can be generated using **PyInstaller**.

The project also includes support for creating a native Windows installer using **Inno Setup**.

## AudioDrop Android

An experimental Android version of AudioDrop is also under development.

Repository:

[AudioDrop Android](https://github.com/IgnacioVerde/audiodrop-android)

The Android version currently implements local music playback and core player functionality but is still a work in progress.

## Project Status

AudioDrop Desktop is functional and includes the main playback, library, playlist, search and download features.

Development is ongoing and additional improvements may be added over time.

## Disclaimer

AudioDrop is intended for personal and educational use.

Users are responsible for ensuring that they have the right to download or process any content used with the application and for complying with the terms of the services from which content is accessed.

## Author

**Ignacio Verde**

Software Developer · Automation · Infrastructure

GitHub: [@IgnacioVerde](https://github.com/IgnacioVerde)
