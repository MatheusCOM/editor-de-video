#!/usr/bin/env python3
"""Mede o vídeo: duração, resolução, fps, orientação, áudio.

Uso: python3 engine/probe.py video.mp4
"""
import json
import sys

from common import probe

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    print(json.dumps(probe(sys.argv[1]), ensure_ascii=False, indent=2))
