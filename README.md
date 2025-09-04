# AI-Powered Video Generator

This project automates the creation of short, engaging videos by combining AI-generated dialogue, synthesized speech, and custom video elements. It's designed to make it easy to produce content like explainer videos, comedic skits, or educational snippets featuring various characters.

## Demo Video

Watch a demo of the AI Video Generator in action:

[Watch Demo](https://www.youtube.com/shorts/1JCQIJ7xAtY)

## Features

*   **AI-Powered Dialogue Generation**: Leverages AI models to create natural-sounding dialogue for selected characters on a given topic, adhering to specific character personalities and constraints.
*   **Character-Based Video Generation**: Automatically selects appropriate character images, voice models, and positions based on the chosen scene.
*   **Dynamic Content**: Supports creating videos for various themes and characters by simply selecting a "scene" and providing a "topic."
*   **Customizable Video Assets**: Allows for easy addition of new characters, prompts, and background videos through configuration files.
*   **TTS Integration**: Synthesizes speech for generated dialogue using a Text-to-Speech SDK.
*   **Video Composition**: Combines synthesized audio, character animations, text overlays, and background footage into a final video file.
*   **Image Integration**: Automatically searches for and integrates relevant images for topics using web search and AI query refinement.
*   **Configurable Prompts**: Supports multiple prompt templates tailored to different shows/genres (e.g., Rick and Morty, Breaking Bad, Political Satire).
*   **Controlled Dialogue**: Features like character-specific speaking limits, emotional tagging for TTS, and conciseness constraints can be applied.

## Setup

### Prerequisites

*   **Python 3.7+**: Ensure you have a compatible Python version installed.
*   **FFmpeg**: Required by `moviepy` for video processing. Install it via your system's package manager (e.g., `brew install ffmpeg` on macOS, `sudo apt-get install ffmpeg` on Debian/Ubuntu).
*   **ImageMagick**: Required by `moviepy` for text rendering. Install it (e.g., `brew install imagemagick` on macOS, `sudo apt-get install imagemagick` on Debian/Ubuntu).
*   **OpenAI API Key**: Needed for dialogue generation and topic image refinement. Set it as an environment variable: `export OPENAI_API_KEY='your-openai-api-key'`.
*   **Fish Audio SDK**: Ensure the SDK is installed and configured with your API key.

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/willkn/ai-video-generation.git
    cd ai-video-generation
    ```

2.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: Make sure your `requirements.txt` includes `moviepy`, `pydub`, `fish_audio_sdk`, `openai`)*

### Configuration Files

The project relies on two JSON configuration files in the root directory:

1.  **`default_environments.json`**: Defines different "scenes" or character sets and their associated prompts.
    *   **Example Entry**:
        ```json
        {
            "Title": "Rick and Morty (Science)",
            "Characters": ["Rick", "Morty"],
            "Prompt": "...",
        }
        ```
2.  **`character_catalog.json`**: Maps character names to their specific assets (voice ID, image path, position, offsets).
    *   **Example Entry**:
        ```json
        {
            "Rick": {
                "voice_id": "...",
                "image_path": "assets/images/rick.png",
                "position": "right",
                "offset_x": -150,
                "offset_y": 100
            },
            "Morty": { ... }
        }
        ```

### Asset Directories

Ensure the following directories and files exist:

*   `assets/videos/`: Contains background video files (e.g., `minecraft.mp4`).
*   `assets/images/`: Contains character image files (e.g., `rick.png`, `morty.png`).

## Usage

Run the `main.py` script from your terminal:

```bash
python main.py


The script will guide you through a selection process:
Select a Scene: Choose from the list of available character sets and prompt types (e.g., "Rick and Morty (Science)", "Breaking Bad (Law)", "Trump and Biden (Politics)").
Enter a Topic: Provide a topic for the AI to explain. You can press Enter to use the default topic defined for the selected scene.
The script will then:
Generate a project name based on the scene and topic.
Fetch a relevant image for the topic using web search (SerpApi) and OpenAI query refinement.
Generate dialogue using the AI model.
Synthesize audio for the dialogue.
Compose the video with background, characters, text overlays, and the topic image.
Save the final video file to the projects/<project_name>/ directory.
Project Structure
code
Code
.
├── main.py                  # Main script to run the pipeline
├── requirements.txt         # Python dependencies
├── .env                     # (Optional) For environment variables like API keys
├── character_catalog.json   # Character asset mappings
├── script_generation.py     # Module for AI dialogue generation
├── audio_generation.py      # Module for TTS and audio collation
├── create_video.py          # Contains Project class, video processing functions
├── assets/
│   ├── videos/              # Background video files
│   └── images/              # Character image files
└── projects/                # Output directory for generated videos and assets
    └── <project_name>/
        ├── audio/           # Generated audio files
        │   ├── turn_001_Speaker.mp3
        │   └── combined_dialogue.mp3
        │   └── timed_script.json
        └── <project_name>_final_tiktok.mp4 # The final output video
