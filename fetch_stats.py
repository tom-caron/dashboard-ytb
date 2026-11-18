#!/usr/bin/env python3
"""Récupère les stats publiques des chaînes YouTube et les ajoute à data/history.json."""
import json
import os
import pathlib
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).parent
HISTORY = ROOT / "data" / "history.json"
VIDEOS = ROOT / "data" / "videos.json"
BASE = "https://www.googleapis.com/youtube/v3"
API = f"{BASE}/channels"


def get(endpoint: str, key: str, **params) -> dict:
    query = urllib.parse.urlencode({"key": key, **params})
    with urllib.request.urlopen(f"{BASE}/{endpoint}?{query}", timeout=30) as resp:
        return json.load(resp)


def fetch_videos(uploads: str, key: str) -> list:
    """Toutes les vidéos publiques de la chaîne, de la plus ancienne à la plus récente."""
    items, token = [], None
    while True:
        page = get("playlistItems", key, part="contentDetails", playlistId=uploads, maxResults=50,
                   **({"pageToken": token} if token else {}))
        items += [i["contentDetails"]["videoId"] for i in page.get("items", [])]
        token = page.get("nextPageToken")
        if not token:
            break
    videos = []
    for start in range(0, len(items), 50):
        batch = get("videos", key, part="snippet,statistics", id=",".join(items[start:start + 50]))
        for v in batch.get("items", []):
            videos.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "published": v["snippet"]["publishedAt"],
                "views": int(v["statistics"].get("viewCount", 0)),
            })
    return sorted(videos, key=lambda v: v["published"])


def fetch_channel(ref: str, key: str) -> dict:
    # "@handle" -> forHandle, sinon identifiant de chaîne "UC..."
    param = {"forHandle": ref} if ref.startswith("@") else {"id": ref}
    query = urllib.parse.urlencode({"part": "snippet,statistics,contentDetails", "key": key, **param})
    with urllib.request.urlopen(f"{API}?{query}", timeout=30) as resp:
        items = json.load(resp).get("items", [])
    if not items:
        raise ValueError(f"Chaîne introuvable : {ref}")
    return items[0]


def main() -> None:
    key = os.environ["YOUTUBE_API_KEY"]
    refs = json.loads((ROOT / "channels.json").read_text(encoding="utf-8"))["channels"]
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    today = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
    videos = {"date": today, "channels": {}}

    for ref in refs:
        try:
            item = fetch_channel(ref, key)
        except Exception as exc:  # une chaîne en erreur ne bloque pas les autres
            print(f"[erreur] {ref} : {exc}")
            continue
        stats = item["statistics"]
        entry = {
            "date": today,
            "subs": None if stats.get("hiddenSubscriberCount") else int(stats["subscriberCount"]),
            "views": int(stats["viewCount"]),
            "videos": int(stats["videoCount"]),
        }
        channel = history["channels"].setdefault(item["id"], {"history": []})
        channel["title"] = item["snippet"]["title"]
        channel["thumb"] = item["snippet"]["thumbnails"]["default"]["url"]
        channel["history"] = [h for h in channel["history"] if h["date"] != today] + [entry]
        print(f"[ok] {channel['title']} : {entry}")
        try:
            uploads = item["contentDetails"]["relatedPlaylists"]["uploads"]
            videos["channels"][item["id"]] = {"title": channel["title"], "videos": fetch_videos(uploads, key)}
            print(f"     {len(videos['channels'][item['id']]['videos'])} vidéos récupérées")
        except Exception as exc:
            print(f"[erreur vidéos] {ref} : {exc}")

    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")
    VIDEOS.write_text(json.dumps(videos, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
