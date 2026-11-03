#!/usr/bin/env python3
"""Publish the checked RC4 files, verify remote bytes, then retire only RC3's release."""
import hashlib
import json
import pathlib
import subprocess
import tempfile

REPO = 'MusMat17/openwrt_lt500-v2'
TAG = 'v2.0-zapret-rc4'
CHANNEL = 'lt500-panel-steer205-v4'
ROOT = pathlib.Path('bin/targets/ramips/mt76x8/release').resolve()

def gh(*args):
    return subprocess.check_output(['gh', *map(str, args)], text=True)

def release(tag):
    return json.loads(gh('api', f'repos/{REPO}/releases/tags/{tag}'))

files = sorted(p for p in ROOT.iterdir() if p.is_file())
assert len(files) == 18, [p.name for p in files]
try:
    current = release(TAG)
except subprocess.CalledProcessError:
    gh('release', 'create', TAG, '--target', gh('api', f'repos/{REPO}/git/ref/heads/{TAG}', '--jq', '.object.sha').strip(),
       '--title', 'Cudy LT500v2 — OpenWrt 23.05.5 — v2.0-zapret-rc4',
       '--notes-file', ROOT / 'INSTALL-RC4.md', '--draft', '--prerelease', *files)
    current = release(TAG)
assert current['tag_name'] == TAG
# Verify every published asset, including the independent packages and ZIP.
def verify_remote():
    remote = release(TAG)
    assets = {a['name']: a for a in remote['assets']}
    assert set(assets) == {p.name for p in files}, set(assets)
    with tempfile.TemporaryDirectory(prefix='lt500-rc4-published-') as d:
        gh('release', 'download', TAG, '--dir', d)
        for p in files:
            downloaded = pathlib.Path(d) / p.name
            assert downloaded.stat().st_size == p.stat().st_size == assets[p.name]['size'], p.name
            checksum = hashlib.sha256(p.read_bytes()).hexdigest()
            assert hashlib.sha256(downloaded.read_bytes()).hexdigest() == checksum, p.name
            if assets[p.name].get('digest'):
                assert assets[p.name]['digest'] == 'sha256:' + checksum, p.name
    print(f'All {len(files)} remote RC4 assets match the checked build byte-for-byte', flush=True)

verify_remote()
if current['draft']:
    gh('release', 'edit', TAG, '--draft=false', '--prerelease', '--latest=false')
assert not release(TAG)['draft']
verify_remote()
# Do not change RC2/RC3 panel channels: their installed updaters rely on them.
try:
    release(CHANNEL)
except subprocess.CalledProcessError:
    gh('release', 'create', CHANNEL, '--target', TAG,
       '--title', 'Compatible LT500 panel 4.x updates', '--prerelease', '--latest=false',
       '--notes', 'Reviewed panel-only packages for LT500 RC4 with Steer 2.0.5. Kernel modules update with firmware.')
gh('release', 'upload', CHANNEL, '--clobber', ROOT / 'lt500-panel.json',
   ROOT / 'zapret-manager-lt500_4.996-1_mipsel_24kc.ipk')
with tempfile.TemporaryDirectory(prefix='lt500-rc4-channel-') as d:
    gh('release', 'download', CHANNEL, '--dir', d)
    for name in ('lt500-panel.json', 'zapret-manager-lt500_4.996-1_mipsel_24kc.ipk'):
        assert (pathlib.Path(d) / name).read_bytes() == (ROOT / name).read_bytes(), name
print('RC4 published and compatible panel channel verified', flush=True)
# Explicit user instruction: remove RC3 only after successful RC4 publication.
try:
    previous = release('v2.0-zapret-rc3')
except subprocess.CalledProcessError:
    print('RC3 release is already absent; no other release is touched', flush=True)
else:
    assert previous['id'] == 416393647 and previous['tag_name'] == 'v2.0-zapret-rc3' and previous['prerelease']
    gh('release', 'delete', 'v2.0-zapret-rc3', '--yes')
    print('RC3 release removed after verification; source tag and older stable releases retained', flush=True)
print(f'https://github.com/{REPO}/releases/tag/{TAG}', flush=True)
