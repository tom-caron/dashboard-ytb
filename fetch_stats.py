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
API = "https://www.googleapis.com/youtube/v3/channels"


def fetch_channel(ref: str, key: str) -> dict:
    # "@handle" -> forHandle, sinon identifiant de chaîne "UC..."
    param = {"forHandle": ref} if ref.startswith("@") else {"id": ref}
    query = urllib.parse.urlencode({"part": "snippet,statistics", "key": key, **param})
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

    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
