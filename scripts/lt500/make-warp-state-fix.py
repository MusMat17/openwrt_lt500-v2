#!/usr/bin/env python3
"""Patch the immutable RC7 panel IPK without changing firmware or kernel files."""
import hashlib, io, pathlib, re, subprocess, sys, tarfile

repo = pathlib.Path(__file__).resolve().parents[2]
old = pathlib.Path(sys.argv[1]).resolve()
out = pathlib.Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
assert hashlib.sha256(old.read_bytes()).hexdigest() == 'f9e0dd55179b09254230252be78313cce7537d2737945b93d12ae079ea0c2267'
work = out / 'work'
work.mkdir(exist_ok=True)
with tarfile.open(old) as outer:
    for kind in ('control', 'data'):
        m = next(m for m in outer if m.name.endswith(kind + '.tar.gz'))
        with tarfile.open(fileobj=io.BytesIO(outer.extractfile(m).read())) as t:
            assert all(not m.name.startswith('/') and '..' not in pathlib.PurePosixPath(m.name).parts for m in t)
            t.extractall(work / kind)

installer = work / 'data/usr/libexec/zapret-manager-installer'
s = installer.read_text()
def once(a, b):
    global s
    assert s.count(a) == 1, a[:100]
    s = s.replace(a, b)

helper = (repo / 'scripts/lt500/warp-state-recovery.sh').read_text()
once('_st_warp_on() {\n', helper + '\n_st_warp_on() {\n')
once('\t[ -s "$ST_WARP_CONF" ] || return 1\n\t_st_owns "net $ST_WARP_IF" && return 0',
     '\t_st_warp_recover_if "$ST_WARP_IF" "$ST_WARP_CONF" && return 0\n\t[ -s "$ST_WARP_CONF" ] || return 1\n\t_st_owns "net $ST_WARP_IF" && return 0')
once('\t_st_warp_own && { _st_warp_own_up; return; }\n\t_st_install_awg || return 1',
     '\t_st_warp_own && { _st_warp_own_up; return; }\n\t_st_warp_recover_all\n\t_st_install_awg || return 1')
# Both removal paths must reconcile before consulting the ownership registry.
needle='\tfor wi in $(_st_wifs_every); do\n\t\t_st_owns "net $wi" || continue'
assert s.count(needle) == 2
s = s.replace(needle, '\t_st_warp_recover_all\n' + needle)
once('\t\t"$ST_WARP_UP" "$ST_WARP_UP_AUTO" "$ST_WARP_GEO" "$ST_DIR/warp.colo" "$ST_DIR/warp.ports" "$ST_WARP_PICK" "$ST_WARP_ORDER" "$ST_TGWS_WARP"\n\t_st_mode_vars',
     '\t\t"$ST_WARP_UP" "$ST_WARP_UP_AUTO" "$ST_WARP_GEO" "$ST_DIR/warp.colo" "$ST_DIR/warp.ports" "$ST_WARP_PICK" "$ST_WARP_ORDER" "$ST_TGWS_WARP"\n\trm -f "$ST_DIR/warp.conf.before-recovery" "$ST_DIR"/warp[23].conf.before-recovery\n\t_st_mode_vars')
# Make first-use recovery run before registering replacement keys, too.
once('\t_st_installed || { echo "ОШИБКА: сначала установите Steer"; return 1; }\n\t[ -n "$(_st_blocker)" ] && { echo "ОШИБКА: ядро steer сейчас настраивает не Zapret Manager"; return 1; }\n\t_ensure_deps\n\t_st_install_awg || return 1\n\t_st_phase tunnel\n\t_st_warp_up || return 1',
     '\t_st_installed || { echo "ОШИБКА: сначала установите Steer"; return 1; }\n\t[ -n "$(_st_blocker)" ] && { echo "ОШИБКА: ядро steer сейчас настраивает не Zapret Manager"; return 1; }\n\t_st_warp_recover_all\n\t_ensure_deps\n\t_st_install_awg || return 1\n\t_st_phase tunnel\n\t_st_warp_up || return 1')
installer.write_text(s)
subprocess.run(['sh', '-n', str(installer)], check=True)
(out / 'installer-fixed.sh').write_text(s)
apply = work / 'data/usr/libexec/lt500-warp-state-apply'
apply.write_bytes((repo / 'package/zapret-manager-lt500/files/lt500-warp-state-apply').read_bytes())
apply.chmod(0o755)
postinst = work / 'control/postinst-pkg'
assert '/usr/libexec/lt500-panel-apply' in postinst.read_text()
postinst.write_text(postinst.read_text().replace('/usr/libexec/lt500-panel-apply', '/usr/libexec/lt500-warp-state-apply'))
control = work / 'control/control'
assert 'Version: 5.064-2\n' in control.read_text()
control.write_text(control.read_text().replace('Version: 5.064-2\n', 'Version: 5.064-3\n'))

def archive(directory):
    b = io.BytesIO()
    with tarfile.open(fileobj=b, mode='w:gz', format=tarfile.GNU_FORMAT) as t:
        for p in sorted(directory.rglob('*')):
            m = t.gettarinfo(str(p), arcname='./' + str(p.relative_to(directory)))
            m.uid = m.gid = 0; m.uname = m.gname = 'root'; m.mtime = 1794873600
            if p.is_file():
                with p.open('rb') as f: t.addfile(m, f)
            else: t.addfile(m)
    return b.getvalue()

md5 = work / 'control/md5sums'
if md5.exists():
    md5.write_text(''.join(hashlib.md5(p.read_bytes()).hexdigest() + '  ' + str(p.relative_to(work/'data')) + '\n' for p in sorted((work/'data').rglob('*')) if p.is_file()))
ipk = out / 'zapret-manager-lt500_5.064-3_mipsel_24kc.ipk'
with tarfile.open(ipk, 'w:gz', format=tarfile.GNU_FORMAT) as t:
    for name, body in [('debian-binary', b'2.0\n'), ('control.tar.gz', archive(work/'control')), ('data.tar.gz', archive(work/'data'))]:
        m=tarfile.TarInfo('./'+name); m.size=len(body); m.mode=0o644; m.uid=m.gid=0; m.mtime=1794873600; t.addfile(m,io.BytesIO(body))
print(ipk.name, ipk.stat().st_size, hashlib.sha256(ipk.read_bytes()).hexdigest())
