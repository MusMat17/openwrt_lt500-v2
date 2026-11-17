#!/usr/bin/env python3
"""Run RC8 first boot and old 3200 KiB guard bypass with the image's real UCI."""
import hashlib,os,pathlib,re,shlex,shutil,subprocess,sys,tempfile
root=pathlib.Path(sys.argv[1]).resolve();shell=shlex.split(os.environ.get('LT500_TEST_SHELL','sh'))
entries=[line.split(' ',2) for line in (root/'usr/share/lt500/panel-rom.files').read_text().splitlines()]
assert len(entries)==59
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for sha,mode,name in entries:
 assert digest(root/name)==sha and root.joinpath(name).stat().st_mode&0o777==int(mode,8),name
assert '__ZMW_BUILD__' not in (root/'www/zm/app.js').read_text()
assert '1794873608' in (root/'www/zm-webui.html').read_text()
assert (root/'usr/libexec/rpcd/zapret-manager').read_text().startswith('#!/bin/sh')
with tempfile.TemporaryDirectory() as td:
 fixture=pathlib.Path(td);rom=fixture/'rom';cfg=fixture/'etc/config';cfg.mkdir(parents=True);delta=fixture/'uci-delta';delta.mkdir();bin=fixture/'bin';bin.mkdir()
 def put(name,text,mode=0o644):
  p=fixture/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);p.chmod(mode);return p
 def copy(name,dest):
  target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,target)
 for sha,mode,name in entries:copy(name,fixture);copy(name,rom)
 for name in ('www/zm-webui.html','usr/share/lt500/panel-installer.sha256','usr/share/lt500/panel-rom.files'):copy(name,fixture);copy(name,rom)
 copy('usr/libexec/zapret-manager-installer',fixture)
 put('etc/lt500-allinone','RC8\n');put('tmp/sysinfo/board_name','cudy,lt500-v2\n')
 put('etc/config/uhttpd',"config uhttpd 'main'\n list listen_http '0.0.0.0:80'\n")
 put('etc/config/network','preserved-WARP-keys-and-WAN\n');put('etc/config/firewall','preserved-rules\n')
 put('etc/lt500-panel/installed.sha256','old-rc7-hash\n');put('etc/lt500-panel/rollback.sha256','old-rollback\n')
 put('etc/crontabs/root','13 2 * * * /usr/bin/custom-user-job\n')
 put('usr/libexec/lt500-zapret-example','')
 uci=root/'sbin/uci'
 put('bin/uci','#!/bin/sh\nexec '+shlex.join(['qemu-mipsel-static','-cpu','24Kc','-L',str(root),str(uci),'-c',str(cfg),'-t',str(delta)])+' "$@"\n',0o755)
 # Fail a full installer/network action. Report exactly the user's 1.5 MiB free.
 put('bin/df','#!/bin/sh\necho touched >> '+shlex.quote(str(fixture/'free-check'))+'\necho "Filesystem Blocks Used Available Use% Mounted on"\necho "overlay 5632 4096 1536 72% /overlay"\n',0o755)
 for command in ('opkg','curl'):
  put('bin/'+command,'#!/bin/sh\necho '+command+' >> '+shlex.quote(str(fixture/'unexpected-network'))+'\nexit 111\n',0o755)
 put('etc/init.d/cron','#!/bin/sh\nexit 0\n',0o755)
 put('bin/schedule-only','#!/bin/sh\ncase "$*" in versions_cron_sync|"steer_action lists_cron x") exit 0 ;; *) exit 1 ;; esac\n',0o755)
 env=dict(os.environ,PATH=str(bin)+':'+os.environ['PATH'])
 code=(root/'usr/libexec/lt500-panel-rom-ready').read_text()
 # Only scheduling calls are mocked: never execute the full backend against host /etc.
 code=code.replace('"$PANEL/backend.sh" versions_cron_sync',str(bin/'schedule-only')+' versions_cron_sync').replace('"$PANEL/backend.sh" steer_action lists_cron x',str(bin/'schedule-only')+' steer_action lists_cron x')
 code=code.replace('ROM=/rom','ROM='+str(rom))
 paths=['/etc/lt500-panel','/opt/zapret-manager-luci','/tmp/lt500-panel-apply.lock','/usr/libexec/zapret-manager-installer','/tmp/sysinfo/board_name','/etc/crontabs','/etc/init.d/cron','/www/zm-webui.html']
 for path in paths:code=code.replace(path,str(fixture/path.lstrip('/')))
 code=code.replace('"/$name"','"'+str(fixture)+'/$name"').replace('"/$name.rom-new"','"'+str(fixture)+'/$name.rom-new"').replace('"/$(dirname "$name")"','"'+str(fixture)+'/$(dirname "$name")"')
 # Avoid rewriting the "$ROM/www/..." source path a second time.
 code=code.replace('$ROM'+str(fixture)+'/', '$ROM/')
 if len(shell)>1 and shell[-1]=='sh':code=code.replace('#!/bin/sh','#!'+str(shutil.which(shell[0]))+' sh',1)
 helper=put('usr/libexec/lt500-panel-rom-ready',code,0o755)
 apply=(root/'usr/libexec/lt500-panel-apply').read_text()
 for path in ('/etc/lt500-allinone','/tmp/sysinfo/board_name','/rom/usr/share/lt500/panel-installer.sha256','/usr/libexec/zapret-manager-installer','/usr/libexec/lt500-panel-rom-ready'):
  apply=apply.replace(path,str(fixture/path.lstrip('/')))
 applyfile=put('apply.sh',apply,0o755)
 def run(script):
  p=subprocess.run([*shell,str(script)],env=env,text=True,capture_output=True)
  assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
  return p.stdout
 def uciget(name):return subprocess.check_output([str(bin/'uci'),'-q','get',name],env=env,text=True).strip()
 first=run(helper);assert 'restored: 0' in first,first
 assert uciget('uhttpd.zmweb.listen_http')=='0.0.0.0:7788 [::]:7788'
 assert uciget('uhttpd.main.listen_http')=='0.0.0.0:80'
 assert not (fixture/'etc/lt500-panel/rollback.sha256').exists()
 assert (fixture/'etc/lt500-panel/installed.sha256').read_text()==(root/'usr/share/lt500/panel-installer.sha256').read_text()
 assert 'restored: 0' in run(applyfile),'Normal bootstrap must bypass the full installer'
 assert not (fixture/'free-check').exists() and not (fixture/'unexpected-network').exists()
 for sha,mode,name in entries:assert digest(fixture/name)==sha,name
 assert (fixture/'etc/crontabs/root').read_text().count('# zm-rpcd-watch')==1
 assert '/usr/bin/custom-user-job' in (fixture/'etc/crontabs/root').read_text()
 # Simulate code preserved by a custom sysupgrade backup: restore only those files.
 put('opt/zapret-manager-luci/backend.sh','old backend\n',0o755);put('www/zm/app.js','old UI\n')
 assert 'restored: 2' in run(helper)
 for sha,mode,name in entries:assert digest(fixture/name)==sha,name
 # Keep an existing custom Web UI port on migration.
 (fixture/'etc/lt500-panel/rom-rc8-configured').unlink()
 subprocess.run([str(bin/'uci'),'set','uhttpd.zmweb.listen_http=0.0.0.0:7777'],env=env,check=True);subprocess.run([str(bin/'uci'),'commit','uhttpd'],env=env,check=True)
 run(helper);assert uciget('uhttpd.zmweb.listen_http')=='0.0.0.0:7777'
 # Honor the saved disabled Web UI setting without a repeated ROM repair loop.
 (fixture/'etc/lt500-panel/rom-rc8-configured').unlink();put('opt/zapret-manager-luci/state/webui','on=0\nport=7788\n')
 run(helper);assert not (fixture/'www/zm-webui.html').exists();run(helper)
 assert not (fixture/'www/zm-webui.html').exists()
 assert (fixture/'etc/config/network').read_text()=='preserved-WARP-keys-and-WAN\n'
 assert (fixture/'etc/config/firewall').read_text()=='preserved-rules\n'
 assert not (fixture/'root/lt500-panel-backup').exists()
print('ROM panel RC8 passed: all 57 payloads/modes, native UCI, first boot at 1.5 MiB free, no installer/network/large backup, stale-code repair, preserved port/WAN/keys/firewall, disabled UI and idempotent boot')
