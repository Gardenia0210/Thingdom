"""Run one real object-led learning session on the board."""

import json
import logging
import os
import re
import time
from contextlib import ExitStack, suppress
from pathlib import Path
from tempfile import TemporaryDirectory

from comm.mqtt_client import BoardMQTT
from presentation import present, word_records


def wait_for_gesture(button, long_press, deadline=None):
    """Return short, long, or timeout from the actual active-low button."""
    start = None
    while deadline is None or time.monotonic() < deadline:
        now = time.monotonic()
        if button.is_pressed():
            start = now if start is None else start
            if now - start >= long_press:
                return "long"
        elif start is not None:
            if now - start >= 0.04:
                return "short"
            start = None
        time.sleep(0.02)
    return "timeout"


def identify(trigger, camera, detector, display, assets):
    """Capture a fresh image only after a real pressure or button gesture."""
    while True:
        while trigger.is_pressed():
            time.sleep(0.03)
        if not trigger.wait_for_press():
            continue
        display.display_image(str(assets / "waiting" / "searching.png"))
        photo = camera.capture_and_save()
        if not photo:
            continue
        try:
            label = detector.detect_closest_object(photo)
            if label:
                return label
        finally:
            Path(photo).unlink(missing_ok=True)


def interact(mqtt, button, recorder, display, assets, directory, opening,
             render, transcribe, long_press, max_duration):
    conversation_id = opening.get("conversation_id")
    if type(conversation_id) is not int or conversation_id <= 0:
        raise RuntimeError("Backend did not return an active conversation ID.")
    reply = opening
    render(reply)
    while wait_for_gesture(button, long_press) == "short":
        display.display_image(str(assets / "waiting" / "recording.png"))
        recording = Path(directory) / "speech.wav"
        recording.unlink(missing_ok=True)
        if not recorder.start_recording(str(recording)):
            raise RuntimeError("Could not start the microphone.")
        try:
            action = wait_for_gesture(button, long_press, time.monotonic() + max_duration)
        finally:
            recorder.stop_recording()
        if action == "long":
            break
        if not recording.is_file():
            raise RuntimeError("The microphone produced no recording.")
        try:
            display.display_image(str(assets / "waiting" / "thinking.png"))
            message = transcribe(recording).strip()
        finally:
            recording.unlink(missing_ok=True)
        if not message:
            continue
        ids = [item["id"] for item in word_records(reply) if type(item.get("id")) is int]
        reply = mqtt.request("speech", {"conversation_id": conversation_id,
                                       "human_audio_message": message, "words_id": ids})
        render(reply)


def main():
    from config import (PROJECT_ROOT, DEVICE_ID, MQTT_BROKER, MQTT_PORT,
                        BUTTON_LONG_PRESS_TIME, MAX_DURATION, DASHSCOPE_API_KEY, MINIMAX_API_KEY)

    if not MQTT_BROKER or not re.fullmatch(r"[A-Za-z0-9_.-]+", DEVICE_ID):
        raise SystemExit("Set MQTT_BROKER and a valid DEVICE_ID in RaspberryPi/.env.")
    if not DASHSCOPE_API_KEY or not MINIMAX_API_KEY:
        raise SystemExit("Set DASHSCOPE_API_KEY and MINIMAX_API_KEY in RaspberryPi/.env.")
    chapter = os.getenv("CHAPTER_TYPE", "")
    if chapter and chapter not in {"fruit", "animal", "food", "travel", "school"}:
        raise SystemExit("CHAPTER_TYPE must be a Thingdom chapter key or empty.")
    moods = json.loads(os.getenv("MOOD_IMAGE_MAP", "{}"))
    if not isinstance(moods, dict):
        raise SystemExit("MOOD_IMAGE_MAP must be a JSON object.")
    trigger_kind = os.getenv("CAPTURE_TRIGGER", "pressure")
    if trigger_kind not in {"pressure", "button"}:
        raise SystemExit("CAPTURE_TRIGGER must be pressure or button.")

    from hardware.audio_player import AudioPlayer
    from hardware.audio_recorder import AudioRecorder
    from hardware.button import Button
    from hardware.camera_capture import CameraCapture
    from hardware.ep1831t_driver import EP1831TDriver
    from hardware.pressure_sensor import PressureSensor
    from utils.flashcard import FlashCardMaker
    from utils.object_detection import ObjectDetection
    from utils.speech_recognition import transcribe
    from utils.text_to_speech import synthesize_text

    logging.basicConfig(level=logging.INFO)
    assets = Path(PROJECT_ROOT) / "imgs"
    with ExitStack() as stack:
        directory = stack.enter_context(TemporaryDirectory(prefix="thingdom-"))

        def own(resource):
            stack.callback(resource.cleanup)
            return resource

        button = own(Button())
        trigger = own(PressureSensor()) if trigger_kind == "pressure" else button
        if not button._initialized or not trigger._initialized:
            raise RuntimeError("Button or capture trigger could not initialize; check GPIO configuration.")
        camera = own(CameraCapture(save_dir=directory))
        detector = ObjectDetection()
        detector._load_models()
        display = own(EP1831TDriver())
        recorder = own(AudioRecorder(save_dir=directory))
        player = own(AudioPlayer(os.getenv("AUDIO_OUTPUT_DEVICE") or None))
        cards = FlashCardMaker()
        mqtt = BoardMQTT(MQTT_BROKER, MQTT_PORT, DEVICE_ID, os.getenv("MQTT_USERNAME"),
                         os.getenv("MQTT_PASSWORD"), os.getenv("MQTT_TLS", "0") == "1")
        stack.callback(mqtt.close)
        mqtt.connect()
        if chapter:
            mqtt.request("chapter", {"chapter_type": chapter})

        def render(reply):
            def synthesize(message):
                return synthesize_text(message, str(Path(directory) / "reply.mp3"))
            present(reply, display, player, cards, synthesize, assets, moods)

        try:
            label = identify(trigger, camera, detector, display, assets)
            display.display_image(str(assets / "waiting" / "thinking.png"))
            opening = mqtt.request("object", {"object_name": label})
            interact(mqtt, button, recorder, display, assets, directory, opening,
                     render, transcribe, BUTTON_LONG_PRESS_TIME, MAX_DURATION)
        finally:
            if type(mqtt.conversation_id) is int and mqtt.conversation_id > 0:
                try:
                    mqtt.request("stop", {"conversation_id": mqtt.conversation_id}, timeout=15)
                except (ConnectionError, RuntimeError, TimeoutError) as error:
                    logging.warning("The backend did not confirm session stop: %s", error)
            with suppress(Exception):
                display.display_image(str(assets / "waiting" / "shutdown.png"))


if __name__ == "__main__":
    main()
