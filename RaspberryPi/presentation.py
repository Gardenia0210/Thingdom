"""Present completed responses on the board speaker and display."""

import re
from pathlib import Path


def word_records(reply):
    words = reply.get("words_used_id")
    return [item for item in words if isinstance(item, dict)] if isinstance(words, list) else []


def present(reply, display, player, cards, synthesize, assets, moods):
    progress = reply.get("islands_progress")
    mood = reply.get("ai_mood")
    mood_id = moods.get(mood) if isinstance(mood, str) else None
    if type(mood_id) is int and 1 <= mood_id <= 9:
        display.display_image(str(assets / "moods" / f"{mood_id}.png"), islands_progress=progress)
    message = reply.get("message")
    if isinstance(message, str) and message.strip():
        audio = synthesize(message)
        if not audio or not player.play_file(audio, wait=True, delete_after_play=True):
            raise RuntimeError("The board could not play the agent response.")
    for record in word_records(reply):
        word = record.get("words")
        if not isinstance(word, str) or not word.strip():
            continue
        key = word.strip().lower()
        path = assets / "words" / f"{key}.png" if re.fullmatch(r"[a-z0-9 _-]+", key) else None
        image = str(path) if path and path.is_file() else None
        card = cards.create_card(image, word, record.get("chinese_translation") or "")
        display.display_image(card, islands_progress=progress)
        break
