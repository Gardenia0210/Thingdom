"""Train YOLO from a real detection dataset and explicit initialization weights."""
import argparse
from pathlib import Path


def train(data: str, weights: str, epochs: int, imgsz: int, device: str,
          project: str, name: str):
    """Delegate training to the original Ultralytics version."""
    if not Path(data).is_file() or not Path(weights).is_file():
        raise FileNotFoundError('Dataset YAML and initialization weights must exist.')
    if epochs < 1 or imgsz < 32:
        raise ValueError('Epochs must be positive and image size at least 32.')
    from ultralytics import YOLO
    return YOLO(str(Path(weights).resolve())).train(
        data=str(Path(data).resolve()), epochs=epochs, imgsz=imgsz,
        device=device, project=project, name=name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True)
    parser.add_argument('--weights', required=True)
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--project', default='runs/train')
    parser.add_argument('--name', default='thingdom')
    train(**vars(parser.parse_args()))
