#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
for entry in manifest['files']:
    path=(root/entry['path']).resolve()
    if not path.is_relative_to(root):
        raise SystemExit('PATH ESCAPE')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
        raise SystemExit(f"HASH MISMATCH: {entry['path']}")
print(f"Verified {len(manifest['files'])} package files for {manifest['source_commit']}")
