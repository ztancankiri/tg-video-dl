import os
import time
import requests
import uuid
import re
from dotenv import load_dotenv
from yt_dlp import YoutubeDL
import instaloader

load_dotenv(override=True)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN not found.")

API_URL = f"https://api.telegram.org/bot{TOKEN}"
LAST_UPDATE_ID = 0

YOUTUBE_REGEX = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+", re.IGNORECASE)

INSTAGRAM_REGEX = re.compile(
    r"^(https?://)?(www\.)?instagram\.com/(reel|p|tv)/.+", re.IGNORECASE)


def download_youtube_video(url, output_path="./downloads"):
    id = uuid.uuid4()
    ydl_opts = {
        'outtmpl': f'{output_path}/{id}.%(ext)s',
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet': True
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


def download_instagram_video(instagram_url, output_dir="downloads"):
    # Validate and extract shortcode using regex
    match = re.search(
        r"(?:instagram\.com)/(?:reel|p|tv)/([A-Za-z0-9_-]+)", instagram_url)
    if not match:
        raise ValueError("Invalid Instagram video URL.")

    id = uuid.uuid4()

    shortcode = match.group(1)

    # Init Instaloader (no login)
    L = instaloader.Instaloader()
    post = instaloader.Post.from_shortcode(L.context, shortcode)

    if not post.is_video:
        raise ValueError("This post does not contain a video.")

    video_url = post.video_url
    os.makedirs(output_dir, exist_ok=True)
    video_path = os.path.join(output_dir, f"{id}.mp4")

    # Download the video only
    with requests.get(video_url, stream=True) as r:
        r.raise_for_status()
        with open(video_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    return video_path


def get_updates(offset=None, timeout=60):
    url = f"{API_URL}/getUpdates"
    params = {'timeout': timeout, 'offset': offset}
    resp = requests.get(url, params=params)
    return resp.json()


def send_message(chat_id, text):
    url = f"{API_URL}/sendMessage"
    data = {'chat_id': chat_id, 'text': text}
    requests.post(url, data=data)


def send_video(chat_id, filepath, caption=None):
    url = f"{API_URL}/sendVideo"
    with open(filepath, 'rb') as video_file:
        files = {'video': video_file}
        data = {'chat_id': chat_id}
        if caption:
            data['caption'] = caption
        return requests.post(url, data=data, files=files).json()


def handle_message(message):
    chat_id = message['chat']['id']
    text = message.get('text', '')

    if YOUTUBE_REGEX.match(text.strip()):
        try:
            print(f"Downloading video from: {text}")
            filepath = download_youtube_video(text)
            send_video(chat_id, filepath, caption="Here is your video 🎬")
            os.remove(filepath)
        except Exception as e:
            print(f"Error: {e}")
            send_message(chat_id, "❌ Failed to download or send the video.")
    elif INSTAGRAM_REGEX.match(text.strip()):
        try:
            print(f"Downloading video from: {text}")
            filepath = download_instagram_video(text)
            send_video(chat_id, filepath, caption="Here is your video 🎬")
            os.remove(filepath)
        except Exception as e:
            print(f"Error: {e}")
            send_message(chat_id, "❌ Failed to download or send the video.")
    else:
        send_message(chat_id, "Send a YouTube link to get the video!")


def main():
    global LAST_UPDATE_ID
    while True:
        updates = get_updates(offset=LAST_UPDATE_ID + 1)
        for update in updates.get('result', []):
            LAST_UPDATE_ID = update['update_id']
            message = update.get('message')
            if message:
                handle_message(message)
        time.sleep(1)


if __name__ == "__main__":
    main()
