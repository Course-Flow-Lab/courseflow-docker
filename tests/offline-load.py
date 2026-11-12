#!/usr/bin/env python3
"""Offline imports must pin image IDs assigned by the destination Docker engine."""
import gzip
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='courseflow-offline-load-') as name:
    tmp = Path(name)
    package = tmp / 'release'
    package.mkdir()
    tags = ('ghcr.io/course-flow-lab/courseflow-api:v0.1.1',
            'ghcr.io/course-flow-lab/courseflow-webui:v0.1.1')
    (package / 'images.offline.env').write_text(f'API_IMAGE={tags[0]}\nWEB_IMAGE={tags[1]}\n')
    (package / 'images.tar.gz').write_bytes(gzip.compress(b'synthetic archive'))
    (package / 'SHA256SUMS').write_text(''.join(
        hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n'
        for p in (package / 'images.offline.env', package / 'images.tar.gz')))
    binary = tmp / 'bin'
    binary.mkdir()
    docker = binary / 'docker'
    docker.write_text('''#!/bin/bash
set -eu
if [[ "$1" == load ]]; then cat >/dev/null; echo 'Loaded synthetic archive'; exit 0; fi
if [[ "$1 $2" == 'image inspect' ]]; then
  case "${@: -1}" in
    ghcr.io/course-flow-lab/courseflow-api:v0.1.1) printf 'sha256:%064d\\n' 1;;
    ghcr.io/course-flow-lab/courseflow-webui:v0.1.1) printf 'sha256:%064d\\n' 2;;
    *) exit 1;;
  esac
  exit 0
fi
exit 1
''')
    docker.chmod(0o755)
    state = tmp / 'state'
    config = tmp / '.env'
    config.write_text(f'PUBLIC_URL=http://127.0.0.1:8100\nSTATE_DIR={state}\n')
    env = {**os.environ, 'PATH': f'{binary}:{os.environ["PATH"]}', 'CF_CONFIG': str(config)}
    subprocess.run([str(root / 'scripts/courseflow'), 'load', str(package)], env=env,
                   check=True, stdout=subprocess.PIPE, text=True)
    expected = f'API_IMAGE=sha256:{1:064d}\nWEB_IMAGE=sha256:{2:064d}\n'
    assert (state / 'images.local.env').read_text() == expected
print('Offline load pins destination engine image IDs')
