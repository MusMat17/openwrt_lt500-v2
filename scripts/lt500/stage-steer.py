#!/usr/bin/env python3
"""Stage the official, hash-pinned Steer payload with its matching signed seed."""
import hashlib
import io
import pathlib
import shutil
import tarfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
NAME = 'steer-core-2.1.4-1_mipsel_24kc.ipk'
SHA256 = '2bfcfcec5e20b622e82f875755c9b57169a709b7bac2e9ade10f7a5cf45e9f21'
package = ROOT / 'dl' / NAME
package.parent.mkdir(exist_ok=True)
if not package.exists():
    urllib.request.urlretrieve('https://github.com/splify2/steer/releases/download/v2.1.4/' + NAME, package)
assert hashlib.sha256(package.read_bytes()).hexdigest() == SHA256, 'Official Steer package hash mismatch'
target = ROOT / 'package/steer-core/files'
shutil.rmtree(target, ignore_errors=True)
target.mkdir()
with tarfile.open(package) as outer:
    data = outer.extractfile('./data.tar.gz') if './data.tar.gz' in outer.getnames() else outer.extractfile('data.tar.gz')
    with tarfile.open(fileobj=io.BytesIO(data.read())) as payload:
        # Content is pinned above; reject absolute/traversing members as well.
        for member in payload.getmembers():
            p = pathlib.PurePosixPath(member.name)
            assert not p.is_absolute() and '..' not in p.parts, member.name
        payload.extractall(target)
init = target / 'etc/init.d/steer'
text = init.read_text()
assert text.count('start_service() {\n') == 1
init.write_text(text.replace('start_service() {\n', 'start_service() {\n    /usr/libexec/lt500-steer-migrate || logger -t steer-plugins "LT500 plugin migration failed; see /tmp/lt500-steer-migrate.log"\n'))
helper = target / 'usr/libexec/lt500-steer-migrate'
helper.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(ROOT / 'package/steer-core/lt500-steer-migrate', helper)
helper.chmod(0o755)
assert (target / 'usr/share/steer/seed/index.json.sig').is_file()
assert (target / 'usr/share/nftables.d/chain-pre/input/30-steer.nft').is_file()
print(f'Official Steer 2.1.4: {SHA256}; signed seed and trust keys retained')
