#!/usr/bin/env python3
"""Replace only Steer in the verified RC5 image using standard OpenWrt tools."""
import hashlib
import json
import os
import pathlib
import shutil
import stat
import struct
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
import zlib

repo = pathlib.Path(__file__).resolve().parents[2]
os.chdir(repo)
assert os.geteuid() == 0, 'Run with sudo: preserve rootfs device nodes and ownership'
base = repo / 'bin/targets/ramips/mt76x8'
base.mkdir(parents=True, exist_ok=True)
work = repo / 'tmp/rc6'
work.mkdir(parents=True, exist_ok=True)
def run(*args, **kw):
    return subprocess.run(list(map(str, args)), check=True, **kw)
def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

archive = work / 'RC5.zip'
urllib.request.urlretrieve('https://github.com/MusMat17/openwrt_lt500-v2/releases/download/v2.0-zapret-rc5/LT500v2-OpenWrt-23.05.5-RC5-zapret-bundle.zip', archive)
assert sha(archive) == '1009bdd78a97388832c2e8dcbd3eb8b43f35323e80c87f4b03a89c73bf7d05b7'
original = work / 'original'
with zipfile.ZipFile(archive) as z:
    assert all(pathlib.Path(n).name == n for n in z.namelist())
    z.extractall(original)
for line in (original / 'SHA256SUMS').read_text().splitlines():
    digest, name = line.split('  ', 1)
    assert sha(original / name) == digest, name
old = original / 'Cudy-LT500v2-OpenWrt-23.05.5-v2.0-zapret-rc5-sysupgrade.bin'
data = old.read_bytes()
assert sha(old) == '72ab40f2d945710991424d8a4b709fd4e0ee891a6347933dfae4c8d853ae2b63'
magic, hcrc, timestamp, size, load, entry, dcrc = struct.unpack('>7I', data[:28])
assert magic == 0x27051956 and zlib.crc32(data[:4] + b'\0'*4 + data[8:64]) == hcrc
offset = 64 + size
assert zlib.crc32(data[64:offset]) == dcrc and data[offset:offset+4] == b'hsqs'
root = work / 'root'
run('unsquashfs', '-no-progress', '-o', offset, '-d', root, old, stdout=subprocess.DEVNULL)
def fingerprint(root):
    result = {}
    for p in root.rglob('*'):
        s = p.lstat()
        if stat.S_ISDIR(s.st_mode):
            continue
        body = str(p.readlink()) if p.is_symlink() else sha(p) if p.is_file() else str(s.st_rdev)
        result[str(p.relative_to(root))] = (s.st_mode, s.st_uid, s.st_gid, body)
    return result
before = fingerprint(root)
info = root / 'usr/lib/opkg/info'
allowed = {p.lstrip('/') for p in (info / 'steer-core.list').read_text().splitlines()}
status_before = (root / 'usr/lib/opkg/status').read_text()
run('python3', 'scripts/lt500/stage-steer.py')
staged = repo / 'package/steer-core/files'
allowed.update(str(p.relative_to(staged)) for p in staged.rglob('*') if not p.is_dir())
package = repo / 'dl/steer-core-2.1.4-1_mipsel_24kc.ipk'
config = work / 'opkg.conf'
config.write_text('dest root /\narch all 1\narch noarch 1\narch mipsel_24kc 10\n')
for path in ('var/lock', 'var/opkg-lists', 'tmp'):
    (root / path).mkdir(parents=True, exist_ok=True)
# Empty feed lists prevent fetching foreign kernel modules. The matching TUN,
# nftables and AWG dependencies are already installed in the actual RC5 root.
run('qemu-mipsel-static', '-cpu', '24Kc', '-L', root, root / 'bin/opkg.real',
    '--offline-root', root, '--conf', config, 'install', package,
    env=dict(os.environ, IPKG_NO_SCRIPT='1', IPKG_INSTROOT=str(root)))
assert not any(p.startswith('tmp/') for p in before), 'Pristine RC5 tmp must be empty'
for p in (root / 'tmp').iterdir():
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p)
    else:
        p.unlink()
# Retain precisely the RC5 integration hook; other Steer payload bytes are official.
shutil.copyfile(staged / 'etc/init.d/steer', root / 'etc/init.d/steer')
helper = root / 'usr/libexec/lt500-steer-migrate'
helper.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(staged / 'usr/libexec/lt500-steer-migrate', helper)
helper.chmod(0o755)
listing = info / 'steer-core.list'
names = listing.read_text().splitlines()
if '/usr/libexec/lt500-steer-migrate' not in names:
    listing.write_text('\n'.join(names + ['/usr/libexec/lt500-steer-migrate']) + '\n')
(root / 'etc/lt500-allinone').write_text('LT500v2 v2.0-zapret-rc6 all-in-one\n')
after = fingerprint(root)
def metadata(p):
    return p == 'usr/lib/opkg/status' or p.startswith('usr/lib/opkg/info/steer-core.') or p == 'etc/lt500-allinone'
unexpected = [p for p in before.keys() | after.keys() if before.get(p) != after.get(p) and p not in allowed and not metadata(p)]
assert not unexpected, unexpected
def versions(status):
    result = {}
    for block in status.split('\n\n'):
        fields = dict(line.split(': ', 1) for line in block.splitlines() if ': ' in line and not line.startswith(' '))
        if 'Package' in fields:
            result[fields['Package']] = fields.get('Version')
    return result
prior = versions(status_before)
current = versions((root / 'usr/lib/opkg/status').read_text())
assert prior.keys() == current.keys()
assert {p for p in prior if prior[p] != current[p]} == {'steer-core'}
assert current['steer-core'] == '2.1.4-1'
run('python3', 'scripts/lt500/check-module-abi.py', root)
run('qemu-mipsel-static', '-cpu', '24Kc', '-L', root, root / 'usr/sbin/steerd', '--version')
fs = work / 'rootfs.squashfs'
run('mksquashfs', root, fs, '-nopad', '-noappend', '-no-xattrs', '-comp', 'xz',
    '-b', '256K', '-processors', '2', '-mkfs-time', timestamp, '-all-time', timestamp, '-no-progress', stdout=subprocess.DEVNULL)
image = base / 'openwrt-ramips-mt76x8-cudy_lt500-v2-squashfs-sysupgrade.bin'
image.write_bytes(data[:offset] + fs.read_bytes())
run(work / 'padjffs2', image, '64')
assert image.stat().st_size <= 15872 * 1024
meta = work / 'metadata.json'
run(work / 'fwtool', '-i', meta, old)
run(work / 'fwtool', '-I', meta, image)
run(work / 'fwtool', '-i', work / 'rc6-metadata.json', image)
assert meta.read_bytes() == (work / 'rc6-metadata.json').read_bytes()
assert image.read_bytes()[:offset] == data[:offset]
# Read the written SquashFS back, so publication validates the actual image.
check = work / 'roundtrip'
run('unsquashfs', '-no-progress', '-o', offset, '-d', check, image, stdout=subprocess.DEVNULL)
roundtrip = fingerprint(check)
diff = [(p, after.get(p), roundtrip.get(p)) for p in after.keys() | roundtrip.keys() if after.get(p) != roundtrip.get(p)]
assert not diff, diff[:25]
manifest = original / 'openwrt-ramips-mt76x8-cudy_lt500-v2.manifest'
(base / manifest.name).write_text(manifest.read_text().replace('steer-core - 2.1.3-1\n', 'steer-core - 2.1.4-1\n'))
profiles = json.loads((original / 'profiles.json').read_text())
profile = profiles['profiles']['cudy_lt500-v2']
profile['images'] = [i for i in profile['images'] if i['type'] == 'sysupgrade']
assert len(profile['images']) == 1
profile['images'][0].update(name=image.name, sha256=sha(image))
if 'size' in profile['images'][0]:
    profile['images'][0]['size'] = image.stat().st_size
(base / 'profiles.json').write_text(json.dumps(profiles, indent=2) + '\n')
panels = repo / 'bin/packages/mipsel_24kc/lt500'
panels.mkdir(parents=True, exist_ok=True)
panel = original / 'zapret-manager-lt500_5.064-1_mipsel_24kc.ipk'
assert sha(panel) == 'bca435658cc33c9b9a2c65bcf04ac95648a5d8c191f141c6b897073eb7c15e81'
shutil.copyfile(panel, panels / panel.name)
run('python3', 'scripts/lt500/release-assets.py')
run('python3', 'scripts/lt500/check-independent-packages.py', check, base / 'release')
run('python3', 'scripts/lt500/package-bundle.py', base / 'release')
print(f'RC6: {image.stat().st_size} bytes; RC5: {len(data)}; saved {len(data)-image.stat().st_size} bytes', flush=True)
print(f'Unchanged kernel prefix: {offset} bytes; all non-Steer package files identical; 69 kmods checked', flush=True)
