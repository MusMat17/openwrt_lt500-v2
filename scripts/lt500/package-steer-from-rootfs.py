#!/usr/bin/env python3
"""Recover standalone IPKs from a pristine, verified image package file list."""
import hashlib
import io
import pathlib
import re
import subprocess
import sys
import tarfile
import tempfile

root = pathlib.Path(sys.argv[1]).resolve()
output = pathlib.Path(sys.argv[2]).resolve()
version = sys.argv[3] if len(sys.argv) > 3 else '2.0.5-1'
output.mkdir(parents=True, exist_ok=True)
info = root / 'usr/lib/opkg/info'

def root_owner(member):
    member.uid = member.gid = 0
    member.uname = member.gname = 'root'
    return member

for module in ('core', 'vless', 'hysteria2', 'proxy', 'xsteer', 'obfs', 'tgws'):
    package = 'steer-' + module
    control = (info / (package + '.control')).read_text()
    assert f'Package: {package}\n' in control
    assert f'Version: {version}\n' in control
    assert 'Architecture: mipsel_24kc\n' in control
    names = (info / (package + '.list')).read_text().splitlines()
    assert names and all(n.startswith('/') and '..' not in pathlib.PurePosixPath(n).parts for n in names)
    with tempfile.TemporaryDirectory(prefix='lt500-ipk-') as directory:
        temp = pathlib.Path(directory)
        (temp / 'debian-binary').write_text('2.0\n')
        with tarfile.open(temp / 'control.tar.gz', 'w:gz', format=tarfile.GNU_FORMAT) as archive:
            for suffix in ('control', 'conffiles', 'preinst', 'postinst', 'prerm', 'postrm'):
                path = info / (package + '.' + suffix)
                if path.exists():
                    archive.add(path, arcname='./' + suffix, filter=root_owner)
            if not (info / (package + '.postinst')).exists():
                # Image creation removes the already-executed generic postinst.
                # Restore the exact template from include/package-ipkg.mk.
                data = b'#!/bin/sh\n[ "${IPKG_NO_SCRIPT}" = "1" ] && exit 0\n[ -s ${IPKG_INSTROOT}/lib/functions.sh ] || exit 0\n. ${IPKG_INSTROOT}/lib/functions.sh\ndefault_postinst $0 $@\n'
                member = tarfile.TarInfo('./postinst')
                member.size = len(data)
                member.mode = 0o755
                archive.addfile(member, io.BytesIO(data))
            status = (root / 'usr/lib/opkg/status').read_text()
            entry = next((p for p in status.split('\n\n') if p.startswith('Package: ' + package + '\n')), '')
            conffiles = re.search(r'^Conffiles:\n((?: .+\n?)+)', entry, re.M)
            if conffiles and not (info / (package + '.conffiles')).exists():
                data = ''.join(line.split()[0] + '\n' for line in conffiles.group(1).splitlines()).encode()
                member = tarfile.TarInfo('./conffiles')
                member.size = len(data)
                member.mode = 0o644
                archive.addfile(member, io.BytesIO(data))
        with tarfile.open(temp / 'data.tar.gz', 'w:gz', dereference=False, format=tarfile.GNU_FORMAT) as archive:
            for name in names:
                path = root / name.lstrip('/')
                assert path.exists() or path.is_symlink(), name
                archive.add(path, arcname='.' + name, recursive=False, filter=root_owner)
        # Ensure the recovered payload matches every installed file byte for byte.
        with tarfile.open(temp / 'data.tar.gz') as archive:
            assert set(archive.getnames()) == {'.' + n for n in names}
            for member in archive:
                path = root / member.name[2:]
                if member.isfile():
                    assert hashlib.sha256(archive.extractfile(member).read()).digest() == hashlib.sha256(path.read_bytes()).digest()
                elif member.issym():
                    assert member.linkname == str(path.readlink())
        destination = output / f'{package}_{version}_mipsel_24kc.ipk'
        assert not destination.exists(), destination
        with tarfile.open(destination, 'w:gz', format=tarfile.GNU_FORMAT) as archive:
            for member in ('debian-binary', 'data.tar.gz', 'control.tar.gz'):
                archive.add(temp / member, arcname='./' + member, filter=root_owner)
        print(destination.name)
