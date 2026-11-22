#!/usr/bin/env python3
"""Récupère les stats publiques des chaînes YouTube et les ajoute à data/history.json."""
import json
import os
import pathlib
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).parent
HISTORY = ROOT / "data" / "history.json"
VIDEOS = ROOT / "data" / "videos.json"
VIDEO_HISTORY = ROOT / "data" / "video_history.json"
KEEP_DAYS = 30  # durée conservée dans l'historique des vues par vidéo
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
        title = item["snippet"]["title"]
        vids = None
        try:
            uploads = item["contentDetails"]["relatedPlaylists"]["uploads"]
            vids = fetch_videos(uploads, key)
            videos["channels"][item["id"]] = {"title": title, "videos": vids}
            print(f"     {len(vids)} vidéos récupérées")
        except Exception as exc:
            print(f"[erreur vidéos] {ref} : {exc}")
        # Le compteur de vues de la chaîne est mis à jour par YouTube avec plusieurs jours
        # de retard : on préfère la somme des vues des vidéos, quasi en temps réel.
        channel_views = int(stats["viewCount"])
        entry = {
            "date": today,
            "subs": None if stats.get("hiddenSubscriberCount") else int(stats["subscriberCount"]),
            "views": max(channel_views, sum(v["views"] for v in vids)) if vids else channel_views,
            "videos": len(vids) if vids else int(stats["videoCount"]),
        }
        channel = history["channels"].setdefault(item["id"], {"history": []})
        channel["title"] = title
        channel["thumb"] = item["snippet"]["thumbnails"]["default"]["url"]
        channel["history"] = [h for h in channel["history"] if h["date"] != today] + [entry]
        print(f"[ok] {title} : {entry} (compteur chaîne : {channel_views} vues)")

    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")
    VIDEOS.write_text(json.dumps(videos, ensure_ascii=False, indent=1), encoding="utf-8")
    save_video_history(videos)


def save_video_history(videos: dict) -> None:
    """Ajoute un relevé horodaté [heure UTC, vues] pour chaque vidéo (une ligne par vidéo)."""
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    cutoff = (now - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hist = json.loads(VIDEO_HISTORY.read_text(encoding="utf-8"))["videos"] if VIDEO_HISTORY.exists() else {}
    for ch in videos["channels"].values():
        for v in ch["videos"]:
            hist.setdefault(v["id"], []).append([stamp, v["views"]])
    for vid, pts in hist.items():
        old = [p for p in pts if p[0] < cutoff]
        # garde le dernier relevé avant la limite pour que la courbe démarre au bord du graphique
        hist[vid] = old[-1:] + [p for p in pts if p[0] >= cutoff]
    lines = [f" {json.dumps(vid)}: {json.dumps(pts, separators=(',', ':'))}" for vid, pts in hist.items()]
    VIDEO_HISTORY.write_text('{"videos": {\n' + ",\n".join(lines) + "\n}}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
