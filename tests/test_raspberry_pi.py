"""Offline checks for the board's device protocol and live-input workflow."""

import importlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "RaspberryPi"))
board = importlib.import_module("main")
from comm.mqtt_client import BoardMQTT
from presentation import present


class BoardTests(unittest.TestCase):
    def mqtt(self):
        client = BoardMQTT("localhost", 1883, "test-board")
        client.client = Mock()
        client.client.publish.return_value.rc = 0
        client.ready = True
        return client

    def test_object_ack_records_id_and_waits_for_completion(self):
        client = self.mqtt()
        base = client.prefix + "object_detected/"
        def deliver():
            for suffix, data in [
                ("response_v2", {"status": "success", "conversation_id": 17}),
                ("agent_response_v2", {"type": "complete", "conversation_id": 99}),
                ("agent_response_v2", {"type": "complete", "conversation_id": 17}),
            ]:
                client._on_message(None, None, SimpleNamespace(
                    retain=False, topic=base + suffix, payload=json.dumps(data)))
        with patch.object(client, "_poll", side_effect=deliver):
            reply = client.request("object", {"object_name": "pear"})
        self.assertEqual(reply["conversation_id"], 17)
        topic, wire = client.client.publish.call_args.args
        self.assertEqual(topic, "device/object_detected_v2")
        self.assertEqual(json.loads(wire), {"device_id": "test-board", "object_name": "pear"})

    def test_rejects_retained_and_partial_replies(self):
        client = self.mqtt()
        for retain, payload in [(True, '{"type":"complete"}'), (False, '{"type":"stream"}'),
                                (False, 'broken')]:
            client._on_message(None, None, SimpleNamespace(retain=retain, payload=payload))
        self.assertFalse(client.messages)

    def test_capture_retries_empty_detection(self):
        with TemporaryDirectory() as directory:
            photos = [Path(directory) / name for name in ("empty.jpg", "found.jpg")]
            for photo in photos:
                photo.touch()
            trigger = Mock()
            trigger.is_pressed.return_value = False
            trigger.wait_for_press.return_value = True
            camera, detector = Mock(), Mock()
            camera.capture_and_save.side_effect = photos
            detector.detect_closest_object.side_effect = [None, "pear"]
            self.assertEqual(board.identify(trigger, camera, detector, Mock(), Path(directory)), "pear")
            self.assertEqual(trigger.wait_for_press.call_count, 2)
            self.assertFalse(any(photo.exists() for photo in photos))

    def test_speech_uses_real_transcript_and_last_reply_ids(self):
        mqtt, recorder, render = Mock(), Mock(), Mock()
        def record(path):
            Path(path).touch()
            return path
        recorder.start_recording.side_effect = record
        opening = {"conversation_id": 4, "words_used_id": [{"id": 19}, {"id": "bad"}]}
        mqtt.request.return_value = {"conversation_id": 4, "message": "Reply"}
        with TemporaryDirectory() as directory, patch.object(
                board, "wait_for_gesture", side_effect=["short", "short", "long"]):
            board.interact(mqtt, Mock(), recorder, Mock(), Path(directory), directory,
                           opening, render, Mock(return_value="a pear"), 2, 30)
        mqtt.request.assert_called_once_with("speech", {
            "conversation_id": 4, "human_audio_message": "a pear", "words_id": [19],
        })
        recorder.stop_recording.assert_called_once()

    def test_missing_word_art_does_not_substitute_another_object(self):
        with TemporaryDirectory() as directory:
            cards, display, player = Mock(), Mock(), Mock()
            present({"words_used_id": [{"words": "lamp"}]}, display, player, cards,
                    Mock(), Path(directory), {})
        cards.create_card.assert_called_once_with(None, "lamp", "")
        display.display_image.assert_called_once()
        player.play_file.assert_not_called()
