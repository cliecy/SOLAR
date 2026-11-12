"""Replay preserved controls using the shared campaign computation."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from replay_campaign import replay


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=Path(__file__).resolve().parents[1] / 'evidence/old450')
    parser.add_argument('--output', type=Path, default=Path('replayed-old450'))
    args = parser.parse_args()
    print(replay(args.inputs, args.output))
