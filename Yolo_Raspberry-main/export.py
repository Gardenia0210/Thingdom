"""Export actual trained weights for later device integration."""
import argparse
from pathlib import Path


def export(weights: str, format: str, imgsz: int):
    """Export through Ultralytics; target runtimes must be installed separately."""
    if not Path(weights).is_file():
        raise FileNotFoundError(weights)
    from ultralytics import YOLO
    return YOLO(str(Path(weights).resolve())).export(format=format, imgsz=imgsz)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weights', required=True)
    parser.add_argument('--format', choices=['onnx', 'ncnn', 'torchscript'], required=True)
    parser.add_argument('--imgsz', type=int, default=640)
    print(export(**vars(parser.parse_args())))
