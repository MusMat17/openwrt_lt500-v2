#!/usr/bin/env python3
"""Run the actual delta installer against old RC7 pages and injected I/O failure."""
import hashlib, os, pathlib, re, shlex, subprocess, sys, tempfile
repo=pathlib.Path(__file__).resolve().parents[2]
old=pathlib.Path(sys.argv[1]).read_text();new=pathlib.Path(sys.argv[2]).read_text()
def payloads(source):
    blocks={}; target=None;buf=[]
    for line in source.splitlines():
        if target is not None:
            if line=='ZM_INSTALLER_EOF':blocks[target]='\n'.join(buf).replace('@ZM_VERSION@','5.064')+'\n';target=None;buf=[]
            else:buf.append(line)
        elif "<< 'ZM_INSTALLER_EOF'" in line:
            if line.startswith('sed '):target='backend.sh'
            else:
                m=re.search(r'''cat > ['"]\$_zmi_st/([^'"]+)['"]''',line)
                if m:target=m[1]
    return blocks
before=payloads(old);after=payloads(new);names=['backend.sh','mod/steer1.sh','mod/steer2.sh']
with tempfile.TemporaryDirectory() as td:
    r=pathlib.Path(td)
    def put(path,text,mode=0o644):
        p=r/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);p.chmod(mode);return p
    panel=r/'opt/zapret-manager-luci';state=r/'etc/lt500-panel';state.mkdir(parents=True)
    for name in names:put('opt/zapret-manager-luci/'+name,before[name],0o755)
    put('etc/lt500-allinone','RC7\n');put('tmp/sysinfo/board_name','cudy,lt500-v2\n')
    put('etc/config/network','retain keys and endpoints\n');put('www/zm/app.js','retain UI\n')
    put('root/placeholder','');put('usr/libexec/zapret-manager-installer',new,0o755)
    put('bin/df','#!/bin/sh\necho "Filesystem 1K-blocks Used Available Use% Mounted on"\necho "overlay 5000 3000 2000 60% /overlay"\n',0o755)
    put('usr/libexec/lt500-panel-apply','#!/bin/sh\nexit 99\n',0o755)
    env=dict(os.environ,PATH=str(r/'bin')+':'+os.environ['PATH'])
    source=(repo/'package/zapret-manager-lt500/files/lt500-warp-state-apply').read_text()
    for path in ('/usr/libexec/zapret-manager-installer','/opt/zapret-manager-luci','/etc/lt500-panel','/root/lt500-warp-state-backup.tar.gz','/tmp/lt500-panel-apply.lock','/etc/lt500-allinone','/tmp/sysinfo/board_name','/tmp/zapret-manager-luci','/usr/libexec/lt500-panel-apply'):
        source=source.replace(path,str(r/path.lstrip('/')))
    script=put('apply.sh',source,0o755)
    def run(ok=True):
        p=subprocess.run(['sh',str(script)],env=env,text=True,capture_output=True)
        assert (p.returncode==0)==ok,(p.stdout,p.stderr,p.returncode)
        return p.stdout
    run()
    for name in names:assert (panel/name).read_text()==after[name],name
    assert (r/'etc/config/network').read_text()=='retain keys and endpoints\n'
    assert (r/'www/zm/app.js').read_text()=='retain UI\n'
    backup=r/'root/lt500-warp-state-backup.tar.gz';digest=hashlib.sha256(backup.read_bytes()).hexdigest()
    run();assert hashlib.sha256(backup.read_bytes()).hexdigest()==digest,'Idempotent apply must retain the original backup'
    # Restore baseline, force the second copy to fail, require all three old files back.
    for name in names:put('opt/zapret-manager-luci/'+name,before[name],0o755)
    (state/'installed.sha256').unlink()
    put('bin/cp','#!/bin/sh\ncase "$2" in */mod/steer1.sh.new) exit 1 ;; esac\nexec /bin/cp "$@"\n',0o755)
    run(False)
    for name in names:assert (panel/name).read_text()==before[name],name
    assert not (state/'installed.sha256').exists()
    (r/'bin/cp').unlink()
    put('tmp/sysinfo/board_name','another-router\n');run(False)
print('Delta updater passed: actual three payloads, 2 MiB free, settings retained, bounded backup, idempotence, failed-copy rollback and board guard')
