#!/usr/bin/env python3
"""Reassemble and verify the first city district archive."""
from pathlib import Path
import hashlib
import zipfile

root = Path(__file__).resolve().parent
expected = 'b0b15396ebbeeec2ef5921ae42acdf57e8aad35d070b83889f572371de65eff6'
output = root / 'huizhou_city_districts_part1.zip'
digest = hashlib.sha256()
with output.open('wb') as out:
    for index in range(25):
        part = root / f'city_part1.zip.part{index:02d}'
        with part.open('rb') as source:
            while chunk := source.read(1024 * 1024):
                out.write(chunk)
                digest.update(chunk)
if digest.hexdigest() != expected:
    output.unlink()
    raise SystemExit('SHA-256 mismatch; assembled file deleted.')
with zipfile.ZipFile(output) as archive:
    bad = archive.testzip()
    if bad:
        raise SystemExit(f'ZIP CRC failure: {bad}')
print(f'OK: {output} SHA-256 {expected}')
