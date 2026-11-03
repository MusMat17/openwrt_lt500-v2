#!/usr/bin/env python3
"""Package verified RC4 files, including the unchanged published SHA256SUMS."""
import hashlib
import pathlib
import sys
import zipfile

root = pathlib.Path(sys.argv[1])
checksums = (root / 'SHA256SUMS').read_text()
files = []
for line in checksums.splitlines():
    sha, name = line.split('  ', 1)
    assert pathlib.Path(name).name == name
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == sha, name
    files.append(name)
assert 'Cudy-LT500v2-OpenWrt-23.05.5-v2.0-zapret-rc4-sysupgrade.bin' in files
name = 'LT500v2-OpenWrt-23.05.5-RC4-zapret-bundle.zip'
archive = root / name
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for member in sorted(files + ['SHA256SUMS']):
        info = zipfile.ZipInfo(member, (2026, 11, 3, 3, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, (root / member).read_bytes(), compresslevel=9)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for member in files + ['SHA256SUMS']:
        assert z.read(member) == (root / member).read_bytes(), member
(root / (name + '.sha256')).write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + name + '\n')
print(f'{name}: {archive.stat().st_size} bytes; {len(files) + 1} members verified')
