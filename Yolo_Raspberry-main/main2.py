"""Print the most confident category from a caller-supplied image."""
import argparse
from detector import ObjectDetector


def top1_class(img_path: str, weights: str, confidence: float = 0.25) -> str:
    """Preserve the original top-category output without a demo image."""
    return ObjectDetector(weights, confidence).top1(img_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('--weights', required=True)
    parser.add_argument('--confidence', type=float, default=0.25)
    args = parser.parse_args()
    print(top1_class(args.image, args.weights, args.confidence))
