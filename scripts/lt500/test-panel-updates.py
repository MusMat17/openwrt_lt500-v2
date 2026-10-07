#!/usr/bin/env python3
"""Exercise panel installation, failure rollback, settings retention and retry."""
import os,pathlib,subprocess,tempfile
repo=pathlib.Path(__file__).resolve().parents[2]
import shlex
source=(repo/'package/zapret-manager-lt500/files/lt500-panel-apply').read_text()
with tempfile.TemporaryDirectory(prefix='lt500-panel-test-') as d:
    root=pathlib.Path(d)
    def put(name,text,mode=0o600):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);p.chmod(mode);return p
    for name in ('network','firewall','uhttpd','zapret'):
        put('etc/config/'+name,'saved-'+name+'\n')
    put('etc/lt500-allinone','LT500\n');put('tmp/sysinfo/board_name','cudy,lt500-v2\n')
    put('opt/zapret-manager-luci/backend.sh','#!/bin/sh\n# old dashboard\n',0o755)
    put('usr/libexec/rpcd/zapret-manager','#!/bin/sh\nexit 0\n',0o755)
    put('opt/zapret-manager-luci/state/ui.theme','dark\n')
    for svc in ('rpcd','uhttpd'):put('etc/init.d/'+svc,'#!/bin/sh\nexit 0\n',0o755)
    bindir=root/'mockbin';put('mockbin/df','#!/bin/sh\necho "Filesystem 1K-blocks Used Available Use% Mounted on"\necho "test 8000 1000 7000 13% /overlay"\n',0o755)
    if os.environ.get('LT500_TEST_BUSYBOX'):
        qemu=os.environ['LT500_TEST_QEMU'];busybox=os.environ['LT500_TEST_BUSYBOX'];sysroot=os.environ['LT500_TEST_SYSROOT']
        put('mockbin/tar', '#!/bin/sh\nexec '+shlex.quote(qemu)+' -L '+shlex.quote(sysroot)+' '+shlex.quote(busybox)+' tar "$@"\n', 0o755)
    env=dict(os.environ,PATH=str(bindir)+':'+os.environ['PATH'])
    # Redirect all absolute runtime paths into the fixture; archive paths
    # remain root-relative so the same backup/restore code is exercised.
    test=source
    import re
    test=re.sub(r'(?<![A-Za-z0-9])/(usr|etc|root|tmp|opt|www|overlay)(?=/|\s|\"|$)',lambda m:str(root)+m.group(),test)
    test=test.replace('"/$p"','"'+str(root)+'/$p"').replace('-C /','-C '+str(root))
    runner=put('apply.sh',test,0o755)
    def install(version,broken=False):
        text=f'''#!/bin/sh
# lt500-panel-update: adapted installer fixture {version}
mkdir -p '{root}/opt/zapret-manager-luci' '{root}/usr/libexec/rpcd'
printf '#!/bin/sh\\nexit 0\\n' > '{root}/usr/libexec/rpcd/zapret-manager'
chmod +x '{root}/usr/libexec/rpcd/zapret-manager'
printf '#!/bin/sh\\n# lt500-panel-update {version}\\n' > '{root}/opt/zapret-manager-luci/backend.sh'
mkdir -p '{root}/www/zm'
echo '{version}' > '{root}/www/zm/app.js'
echo '{version}' >> '{root}/calls'
'''
        if broken:text+=f"echo changed > '{root}/etc/config/network'\nexit 1\n"
        put('usr/libexec/zapret-manager-installer',text,0o755)
    def run(*args,ok=True):
        result=subprocess.run(['sh',str(runner),*args],env=env,capture_output=True,text=True)
        assert (result.returncode==0)==ok,(result.stdout,result.stderr)
        return result
    import shutil
    shutil.rmtree(root/'opt/zapret-manager-luci')
    (root/'usr/libexec/rpcd/zapret-manager').unlink()
    install('v1');run();assert (root/'etc/config/network').read_text()=='saved-network\n'
    put('opt/zapret-manager-luci/state/ui.theme','dark\n')
    before=(root/'calls').read_text();run();assert (root/'calls').read_text()==before
    old=(root/'opt/zapret-manager-luci/backend.sh').read_bytes()
    install('broken',True);run(ok=False)
    assert (root/'opt/zapret-manager-luci/backend.sh').read_bytes()==old
    assert (root/'etc/config/network').read_text()=='saved-network\n'
    install('v2');run()
    assert (root/'opt/zapret-manager-luci/state/ui.theme').read_text()=='dark\n'
    put('etc/config/network','new-current-settings\n')
    run('rollback');assert (root/'opt/zapret-manager-luci/backend.sh').read_bytes()==old
    assert (root/'etc/config/network').read_text()=='new-current-settings\n'
    before=(root/'calls').read_text();run();assert (root/'calls').read_text()==before
    install('v3');run();assert 'v3' in (root/'opt/zapret-manager-luci/backend.sh').read_text()
    put('tmp/sysinfo/board_name','incorrect-device\n');run(ok=False)
print('Panel update: settings retention, idempotence, failure recovery, manual rollback and board guard passed')
