"""Compare a 16-image CPU replay to the preserved full evaluation, without hardware."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import sys
import tarfile
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiment_common.durable import sha


def compare(session: str, reference: str) -> dict[str, object]:
    session, reference = str(uuid.UUID(session)), str(uuid.UUID(reference))
    folder = ROOT / 'results/mnist_tiled_transfer_20261022' / session
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['status'] != 'completed' or manifest.get('smoke_only') is not True or manifest['expected_test_images'] != 16:
        raise ValueError('Expected a completed 16-image smoke evaluation')
    if manifest['hardware_calls_this_process'] != 0:
        raise ValueError('Smoke must be CPU only')
    receipt = json.loads((ROOT / 'archives' / (reference + '.json')).read_text(encoding='utf-8'))
    archive = ROOT / 'archives' / (reference + '.tar.gz')
    if sha(archive) != receipt['archive_sha256']:
        raise ValueError('Reference archive checksum mismatch')
    counts = np.load(folder / 'test_counts.npy', allow_pickle=False)
    with tarfile.open(archive, 'r:gz') as stored:
        stream = stored.extractfile(reference + '/test_counts.npy')
        if stream is None:
            raise ValueError('Missing reference counts')
        with stream:
            version = np.lib.format.read_magic(stream)
            if version != (1, 0):
                raise ValueError('Unexpected archived NumPy header')
            shape, fortran, dtype = np.lib.format.read_array_header_1_0(stream)
            if shape != (10000, 36864) or fortran or dtype != np.dtype('uint8'):
                raise ValueError('Unexpected reference counts layout')
            expected_counts = np.frombuffer(stream.read(16 * shape[1]), dtype=dtype).reshape(16, shape[1])
        predictions = stored.extractfile(reference + '/predictions.npz')
        if predictions is None:
            raise ValueError('Missing reference predictions')
        with predictions, np.load(io.BytesIO(predictions.read()), allow_pickle=False) as expected, np.load(folder / 'predictions.npz', allow_pickle=False) as actual:
            same_labels = np.array_equal(actual['argmax'], expected['argmax'][:16])
            same_logits = np.allclose(actual['logits'], expected['logits'][:16], rtol=1e-6, atol=1e-6)
    same_counts = np.array_equal(counts, expected_counts)
    if not (same_counts and same_labels and same_logits):
        raise ValueError(f'Replay regression: counts={same_counts}, predictions={same_labels}, logits={same_logits}')
    return dict(session=session, reference=reference, images=16, counts_exact=True,
                predictions_exact=True, logits_rtol=1e-6, logits_atol=1e-6, hardware_calls=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--reference', required=True)
    args = parser.parse_args()
    print(json.dumps(compare(args.session, args.reference), indent=2))
