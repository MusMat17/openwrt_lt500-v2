#!/usr/bin/env python3
"""Exercise RC7 migration using image UCI and the actual upstream config generator."""
import os,pathlib,shlex,shutil,subprocess,sys,tempfile
root=pathlib.Path(sys.argv[1]).resolve()
repo=pathlib.Path(__file__).resolve().parents[2]
src=repo/'package/lt500-bundle-support/files'
def checked(*args,**kw):return subprocess.run(args,check=True,**kw)
with tempfile.TemporaryDirectory() as td:
 fixture=pathlib.Path(td);cfg=fixture/'etc/config';cfg.mkdir(parents=True);delta=fixture/'delta';delta.mkdir()
 bindir=fixture/'bin';bindir.mkdir();os.environ['PATH']=str(bindir)+':'+os.environ['PATH']
 uci_binary=root/'sbin/uci'
 if not uci_binary.exists():uci_binary=root/'bin/uci'
 assert uci_binary.exists()
 wrapper=bindir/'uci'
 wrapper.write_text('#!/bin/sh\nexec '+shlex.join(['qemu-mipsel-static','-cpu','24Kc','-L',str(root),str(uci_binary),'-c',str(cfg),'-P',str(delta)])+' "$@"\n');wrapper.chmod(0o755)
 def uci(*args):return subprocess.check_output(['uci',*args],text=True).strip()
 zp=fixture/'opt/zapret';zp.mkdir(parents=True)
 for n in ('comfunc.sh','def-cfg.sh','sync_config.sh','config.default'):
  p=root/'opt/zapret'/n
  if p.exists():(zp/n).write_text(p.read_text() if n=='def-cfg.sh' else p.read_text().replace('/opt/zapret',str(zp)))
 (zp/'config').write_text((root/'opt/zapret/config').read_text())
 defaults=fixture/'defaults'
 defaults.write_text('#!/bin/bash\nset -e\ntouch '+shlex.quote(str(cfg/'zapret'))+'\nuci set zapret.config=main\nZAPRET_CFG_NAME=zapret\n. '+shlex.quote(str(zp/'def-cfg.sh'))+'\nset_cfg_reset_values\nset_cfg_nfqws_strat v6_by_StressOzz\n')
 defaults.chmod(0o755)
 init=fixture/'zapret-init';init.write_text('#!/bin/sh\ncase "$1" in enable) touch "'+str(fixture/'enabled')+'";; enabled) test -f "'+str(fixture/'enabled')+'";; start) echo start >> "'+str(fixture/'starts')+'";; esac\n');init.chmod(0o755)
 # Rewrite absolute paths only in a fixture copy of the exact shipped helper.
 helper=(src/'lt500-zapret-configure').read_text()
 helper=helper.replace('/opt/zapret/uci-def-cfg.sh',str(defaults)).replace('/opt/zapret/sync_config.sh','bash '+str(zp/'sync_config.sh')).replace('/etc/init.d/zapret',str(init))
 for path in ('/etc/lt500-bundle','/etc/config/zapret','/opt/zapret-manager-luci/state','/etc/crontabs','/tmp/lt500-zapret-start'):
  helper=helper.replace(path,str(fixture/path.lstrip('/')))
 hp=fixture/'configure';hp.write_text(helper)
 checked('sh',str(hp))
 assert uci('get','zapret.config.run_on_boot')=='1'
 opts=uci('get','zapret.config.NFQWS_OPT')
 assert '--hostlist=/opt/zapret/ipset/zapret-hosts-rkn.txt' in opts
 assert '--hostlist=/opt/zapret/ipset/zapret-hosts-google.txt' in opts
 assert 'host=rzd.ru' in opts and '<HOSTLIST' not in opts
 assert (fixture/'enabled').exists()
 cron=fixture/'etc/crontabs/root';assert cron.read_text().count('lt500-rkn-update')==2 # command and log filename
 # Runtime config is syntactically valid after actual upstream sync.
 checked('sh','-n',str(zp/'config'))
 # Cold boot's late hook starts once, subsequent calls are harmless.
 once=(src/'lt500-zapret-once').read_text().split('start() {',1)[1]
 once='start() {'+once
 once=once.replace('/etc/init.d/zapret',str(init)).replace('/tmp/lt500-zapret-start',str(fixture/'tmp/lt500-zapret-start')).replace('/tmp/lt500-zapret-boot.log',str(fixture/'boot.log'))
 checked('sh','-c',once+'\nstart\nstart\n')
 assert (fixture/'starts').read_text()=='start\n'
 # A deliberate disable is retained after one-time migration.
 uci('set','zapret.config.run_on_boot=0');uci('commit','zapret')
 checked('sh',str(hp));assert uci('get','zapret.config.run_on_boot')=='0'
 # Upgrade custom strategy: keep all parameters, only replace existing placeholders.
 (fixture/'etc/lt500-bundle/rc7-zapret').unlink()
 custom='--filter-tcp=443 <HOSTLIST> --dpi-desync=fake --dpi-desync-repeats=3'
 uci('set','zapret.config.NFQWS_OPT='+custom);uci('set','zapret.config.WS_USER=customuser');uci('commit','zapret')
 checked('sh',str(hp))
 opts=uci('get','zapret.config.NFQWS_OPT')
 assert '--dpi-desync-repeats=3' in opts and uci('get','zapret.config.WS_USER')=='customuser'
 assert cron.read_text().splitlines().__len__()==1
 # A strategy without generic hostlists is left byte-for-byte intact.
 (fixture/'etc/lt500-bundle/rc7-zapret').unlink()
 custom='--filter-tcp=443 --hostlist-domains=example.org --dpi-desync=fake'
 uci('set','zapret.config.NFQWS_OPT='+custom);uci('commit','zapret')
 checked('sh',str(hp));assert uci('get','zapret.config.NFQWS_OPT')==custom
 # Updater's actual validator accepts domains, excludes YouTube and rejects HTML.
 google=fixture/'google';google.write_text('youtube.com\n')
 raw=fixture/'domains';raw.write_text('example.org\nx.youtube.com\nEXAMPLE.NET\n')
 p=subprocess.run(['awk','-f',str(src/'rkn-filter.awk'),str(google),str(raw)],text=True,capture_output=True)
 assert p.returncode==0 and p.stdout=='example.org\nexample.net\n',(p.returncode,p.stdout)
 raw.write_text('<html>blocked</html>\n')
 p=subprocess.run(['awk','-f',str(src/'rkn-filter.awk'),str(google),str(raw)],capture_output=True)
 assert p.returncode!=0
 # Invalid fetches must not replace the existing cached list.
 updater=(src/'lt500-rkn-update').read_text()
 for path in ('/opt/zapret/ipset/zapret-hosts-rkn.txt','/opt/zapret/ipset/zapret-hosts-google.txt','/opt/zapret-manager-luci/state','/usr/share/lt500/rkn-filter.awk','/tmp/lt500-rkn-update.lock'):
  target=fixture/path.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True)
  updater=updater.replace(path,str(target))
 shutil.copyfile(src/'rkn-filter.awk',fixture/'usr/share/lt500/rkn-filter.awk')
 cache=fixture/'opt/zapret/ipset/zapret-hosts-rkn.txt';cache.write_text('keep.example\n')
 shutil.copyfile(google,fixture/'opt/zapret/ipset/zapret-hosts-google.txt')
 state=fixture/'opt/zapret-manager-luci/state';state.mkdir(parents=True,exist_ok=True);(state/'zapret_rkn_src').write_text('tachyon\n');(state/'zapret_rkn').touch()
 curl=bindir/'curl';curl.write_text('#!/bin/sh\nwhile [ "$#" -gt 0 ]; do if [ "$1" = -o ]; then shift; echo "<html>failure</html>" > "$1"; exit 0; fi; shift; done\nexit 1\n');curl.chmod(0o755)
 up=fixture/'update';up.write_text(updater)
 p=subprocess.run(['sh',str(up)],capture_output=True);assert p.returncode!=0
 assert cache.read_text()=='keep.example\n'
print('Zapret RC7: real MIPS UCI, upstream defaults and sync; first-boot enable; one-shot start; user disable/custom strategy retained; validated atomic list updates')
