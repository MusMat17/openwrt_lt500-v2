#!/usr/bin/env python3
"""Publish the checked RC5 files, verify remote bytes, preserving earlier releases."""
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile

REPO = 'MusMat17/openwrt_lt500-v2'
TAG = 'v2.0-zapret-rc5'
CHANNEL = 'lt500-panel-steer213-noradio'
ROOT = pathlib.Path('bin/targets/ramips/mt76x8/release').resolve()

def gh(*args):
    return subprocess.check_output(['gh', *map(str, args)], text=True)

class ReleaseMissing(Exception):
    pass

def release(tag):
    # The tag endpoint omits drafts. The release collection includes writable drafts.
    for item in json.loads(gh('api', f'repos/{REPO}/releases?per_page=100')):
        if item['tag_name'] == tag:
            return item
    raise ReleaseMissing(tag)

build_sha = json.loads((ROOT / 'BUILD-INFO.json').read_text())['build_commit']
assert build_sha == os.environ.get('LT500_BUILD_COMMIT', os.environ['GITHUB_SHA']), 'Publication commit must match the actual build commit'
files = sorted(p for p in ROOT.iterdir() if p.is_file())
assert len(files) == 12, [p.name for p in files]
try:
    current = release(TAG)
except ReleaseMissing:
    gh('release', 'create', TAG, '--target', build_sha,
       '--title', 'Cudy LT500v2 — OpenWrt 23.05.5 — v2.0-zapret-rc5',
       '--notes-file', ROOT / 'INSTALL-RC5.md', '--draft', '--prerelease', *files)
    current = release(TAG)
assert current['tag_name'] == TAG
# Verify every published asset, including the independent packages and ZIP.
def verify_remote():
    remote = release(TAG)
    assets = {a['name']: a for a in remote['assets']}
    assert set(assets) == {p.name for p in files}, set(assets)
    for p in files:
        asset = assets[p.name]
        # Fetch by asset ID: this works before the draft has a published tag.
        downloaded = subprocess.check_output(['gh', 'api',
            f"repos/{REPO}/releases/assets/{asset['id']}",
            '-H', 'Accept: application/octet-stream'])
        assert len(downloaded) == p.stat().st_size == asset['size'], p.name
        checksum = hashlib.sha256(p.read_bytes()).hexdigest()
        assert hashlib.sha256(downloaded).hexdigest() == checksum, p.name
        if asset.get('digest'):
            assert asset['digest'] == 'sha256:' + checksum, p.name
    print(f'All {len(files)} remote RC5 assets match the checked build byte-for-byte', flush=True)

verify_remote()
if current['draft']:
    gh('api', '--method', 'PATCH', f"repos/{REPO}/releases/{current['id']}",
       '-F', 'draft=false', '-F', 'prerelease=true', '-f', 'make_latest=false')
assert not release(TAG)['draft']
verify_remote()
# Do not change earlier panel channels: their installed updaters rely on them.
try:
    release(CHANNEL)
except ReleaseMissing:
    gh('release', 'create', CHANNEL, '--target', TAG,
       '--title', 'Compatible LT500 panel 5.x updates (no radio)', '--prerelease', '--latest=false',
       '--notes', 'Reviewed panel-only packages for LT500 RC5 with Steer 2.1.3. Kernel modules update with firmware.')
gh('release', 'upload', CHANNEL, '--clobber', ROOT / 'lt500-panel.json',
   ROOT / 'zapret-manager-lt500_5.064-1_mipsel_24kc.ipk')
with tempfile.TemporaryDirectory(prefix='lt500-rc5-channel-') as d:
    gh('release', 'download', CHANNEL, '--dir', d)
    for name in ('lt500-panel.json', 'zapret-manager-lt500_5.064-1_mipsel_24kc.ipk'):
        assert (pathlib.Path(d) / name).read_bytes() == (ROOT / name).read_bytes(), name
print('RC5 published and compatible panel channel verified', flush=True)
print(f'https://github.com/{REPO}/releases/tag/{TAG}', flush=True)
