"""Offline checks of the published map, model identity and path boundary."""
from pathlib import Path
import json
import unittest

from experiment_common.durable import sha
from experiment_common.runtime import ROOT, repo_path
from experiment_common.tiled_transfer import profiles, schedule


class ProtocolTests(unittest.TestCase):
    def test_complete_tiling(self) -> None:
        selected = profiles(ROOT / 'experiments/mnist_tiled_transfer_20261022/map_qualified.json')
        assignments = schedule(selected)
        self.assertEqual(sum(2 * len(p.block.bls) for p in selected), 24)
        self.assertEqual(len(selected), 10)
        self.assertEqual(len(assignments), 1600)
        self.assertEqual(max(a.load for a in assignments) + 1, 134)
        self.assertEqual({(a.filter, a.tap) for a in assignments}, {(f, t) for f in range(64) for t in range(25)})

    def test_model_bytes_match_published_comparison(self) -> None:
        comparison = json.loads((ROOT / 'data/COMPARISON.json').read_text(encoding='utf-8'))
        for relative, expected in comparison['model_asset_sha256'].items():
            self.assertEqual(sha(ROOT / relative), expected, relative)
        self.assertEqual(sha(ROOT / 'experiments/mnist_tiled_transfer_20261022/map_qualified.json'), comparison['map_sha256'])

    def test_paths_are_portable_and_contained(self) -> None:
        self.assertEqual(repo_path('configs/board.ini'), ROOT / 'configs/board.ini')
        for value in ('', '../outside', '/absolute', 'C:\\outside', '..\\outside'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                repo_path(value)


if __name__ == '__main__':
    unittest.main()
