"""Print detected object counts from a caller-supplied image."""
import argparse
from detector import ObjectDetector


def predict_summary(img_path: str, weights: str, confidence: float = 0.25) -> str:
    """Preserve the original summary interface with explicit model input."""
    return ObjectDetector(weights, confidence).summary(img_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('--weights', required=True)
    parser.add_argument('--confidence', type=float, default=0.25)
    args = parser.parse_args()
    print(predict_summary(args.image, args.weights, args.confidence))
