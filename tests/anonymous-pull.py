#!/usr/bin/env python3
import subprocess,sys,tempfile
from pathlib import Path
images=dict(line.split('=',1) for line in Path(sys.argv[1]).read_text().splitlines() if line and not line.startswith('#'))
with tempfile.TemporaryDirectory() as config:
 for image in images.values():
  subprocess.run(['docker','--config',config,'pull','--platform','linux/amd64',image],check=True)
print('Both GHCR images can be pulled without registry credentials')
