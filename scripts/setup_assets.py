import sys
import os
import requests

# Menambahkan root directory ke sys.path untuk import log
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from log import logger

def download_file(url, dest):
    if not os.path.exists(dest):
        logger.info(f"Downloading {dest}...")
        try:
            r = requests.get(url, stream=True)
            r.raise_for_status()
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"✅ Downloaded {dest}")
        except Exception as e:
            logger.error(f"❌ Failed to download {dest}: {e}")
    else:
        logger.info(f"OK: {dest} already exists.")

def main():
    os.makedirs("assets", exist_ok=True)
    # Placeholder URLs. For production, the user can replace these with real links or assets.
    assets = {
        "assets/lofi.mp3": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=lofi-study-112191.mp3",
        "assets/gta.mp4": "https://cdn.pixabay.com/video/2024/09/25/233077_large.mp4", 
        "assets/beep.mp3": "https://cdn.pixabay.com/download/audio/2022/03/10/audio_c8c8a73467.mp3?filename=beep-07a.mp3",
        "assets/pop.mp3": "https://cdn.pixabay.com/download/audio/2021/08/04/audio_3d1da9c087.mp3?filename=pop-39222.mp3",
        "assets/subway.mp4": "https://cdn.pixabay.com/video/2020/05/04/38075-416629938_tiny.mp4",
        "assets/slime.mp4": "https://cdn.pixabay.com/video/2023/10/22/186000-876939988_tiny.mp4",
        "assets/phonk.mp3": "https://cdn.pixabay.com/download/audio/2023/04/07/audio_354c414995.mp3?filename=phonk-145718.mp3"
    }

    for path, url in assets.items():
        download_file(url, path)

if __name__ == "__main__":
    main()
