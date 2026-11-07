"""Offline regression tests; no cloud, broker or model download is required."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Yolo_Raspberry-main'))
sys.path.insert(0, str(ROOT / 'kids_language_2-main'))
from detector import ObjectDetector
from agent_system_v2.events import build_object_event
from train import train


class PipelineTests(unittest.TestCase):
    def test_event_uses_real_detection(self):
        event = build_object_event('  bottle  ', 'travel')
        payload = json.loads(event.split('\n', 1)[1])
        self.assertEqual(payload, {'event': 'object_detected', 'object_name': 'bottle',
                                   'chapter_type': 'travel'})
        self.assertIn('child has not spoken', event)

    def test_empty_detection_and_chapter_rejected(self):
        for name, chapter in [('', 'fruit'), ('apple', ''), (None, 'school')]:
            with self.assertRaises(ValueError):
                build_object_event(name, chapter)

    def test_top_category_and_counts_use_model_results(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            weights = Path(directory) / 'model.pt'
            image = Path(directory) / 'photo.jpg'
            weights.touch()
            image.touch()
            result = MagicMock()
            result.names = {0: 'bottle', 1: 'cup'}
            result.boxes.__len__.return_value = 3
            result.boxes.cls.cpu().tolist.return_value = [0, 1, 0]
            result.boxes.conf.cpu().tolist.return_value = [0.6, 0.9, 0.7]
            result.boxes.xyxy.cpu().tolist.return_value = [[0, 0, 10, 10]] * 3
            factory = MagicMock()
            factory.return_value.predict.return_value = [result]
            with patch.dict(sys.modules, {'ultralytics': types.SimpleNamespace(YOLO=factory)}):
                detector = ObjectDetector(str(weights))
                self.assertEqual(detector.top1(str(image)), 'cup')
                self.assertEqual(detector.summary(str(image)), '2 bottle, 1 cup')
                factory.assert_called_once()
                result.boxes = None
                self.assertEqual(detector.top1(str(image)), '')
                self.assertEqual(detector.summary(str(image)), 'no detections')
                with self.assertRaises(FileNotFoundError):
                    detector.detect(str(Path(directory) / 'absent.jpg'))

    def test_missing_weights_do_not_trigger_download(self):
        with self.assertRaises(FileNotFoundError):
            ObjectDetector('missing-weights.pt')

    def test_training_rejects_missing_dataset(self):
        with self.assertRaises(FileNotFoundError):
            train('missing.yaml', 'missing.pt', 2, 640, 'cpu', 'runs', 'test')

    def test_stream_parser_handles_fragmented_unicode(self):
        from agent_system_v2.agents.stream_parser import StreamingAiMessageExtractor
        tokens = []
        parser = StreamingAiMessageExtractor(on_token=tokens.append)
        payload = json.dumps({'ai_message': 'Hello "friend"! 你好 🌈', 'words_used_id': [5]})
        for fragment in payload:
            parser.feed(fragment)
        self.assertEqual(parser.get_accumulated_message(), 'Hello "friend"! 你好 🌈')
        self.assertEqual(''.join(tokens), 'Hello "friend"! 你好 🌈')


if __name__ == '__main__':
    unittest.main()
