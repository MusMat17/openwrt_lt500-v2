#!/usr/bin/env python3
"""Build RC7 from checked RC6, retaining kernel, modules and Steer byte-for-byte."""
import hashlib,io,json,os,pathlib,re,shutil,stat,struct,subprocess,tarfile,urllib.request,zipfile,zlib
repo=pathlib.Path(__file__).resolve().parents[2];os.chdir(repo)
assert os.geteuid()==0
work=repo/'tmp/rc7';work.mkdir(parents=True,exist_ok=True)
out=repo/'bin/targets/ramips/mt76x8/release';out.mkdir(parents=True,exist_ok=True)
def run(*args,**kw): return subprocess.run(list(map(str,args)),check=True,**kw)
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
archive=repo/'tmp/rc7-audit/RC6.zip'
assert sha(archive)=='5a3d3a8e69cfe16bebf44fbf548e145396bf83b4bda7ac1ec2649f2f443154ce'
oldfiles=work/'original'
with zipfile.ZipFile(archive) as z:
 assert all(pathlib.Path(n).name==n for n in z.namelist())
 z.extractall(oldfiles)
for line in (oldfiles/'SHA256SUMS').read_text().splitlines():
 digest,name=line.split('  ',1);assert sha(oldfiles/name)==digest,name
old=oldfiles/'Cudy-LT500v2-OpenWrt-23.05.5-v2.0-zapret-rc6-sysupgrade.bin'
assert sha(old)=='66e03aa9f6881c9befb2f9ad562d66e7708931ba37f67247fb39ffe7496a97aa'
data=old.read_bytes()
magic,hcrc,timestamp,size,load,entry,dcrc=struct.unpack('>7I',data[:28])
assert magic==0x27051956 and zlib.crc32(data[:4]+b'\0'*4+data[8:64])==hcrc
offset=64+size
assert offset==2303512 and zlib.crc32(data[64:offset])==dcrc and data[offset:offset+4]==b'hsqs'
root=work/'root'
run('unsquashfs','-no-progress','-o',offset,'-d',root,old,stdout=subprocess.DEVNULL)
def fingerprint(root):
 result={}
 for p in root.rglob('*'):
  s=p.lstat()
  if stat.S_ISDIR(s.st_mode):continue
  body=str(p.readlink()) if p.is_symlink() else sha(p) if p.is_file() else str(s.st_rdev)
  result[str(p.relative_to(root))]=(s.st_mode,s.st_uid,s.st_gid,body)
 return result
before=fingerprint(root)
prior_status=(root/'usr/lib/opkg/status').read_text()
# Reuse the original opkg control, dependency declarations and package scripts.
panelold=oldfiles/'zapret-manager-lt500_5.064-1_mipsel_24kc.ipk'
def unpack_bytes(blob,destination):
 with tarfile.open(fileobj=io.BytesIO(blob)) as t:
  assert all(not m.name.startswith('/') and '..' not in pathlib.PurePosixPath(m.name).parts for m in t)
  t.extractall(destination)
panelwork=work/'panel';panelwork.mkdir()
with tarfile.open(panelold) as t:
 for kind in ('control','data'):
  m=next(m for m in t if m.name.endswith(kind+'.tar.gz'))
  unpack_bytes(t.extractfile(m).read(),panelwork/kind)
installer=repo/'tmp/rc7-audit/installer-lite.sh'
pdata=panelwork/'data'
(pdata/'usr/libexec/zapret-manager-installer').write_bytes(installer.read_bytes())
updater=pdata/'usr/libexec/lt500-panel-update'
updater.write_text(updater.read_text().replace('lt500-panel-steer213-noradio','lt500-panel-lite').replace('awg2-i1-tun-steer213-panel5-noradio','awg2-i1-tun-steer214-panel5-lite'))
control=panelwork/'control/control'
control.write_text(control.read_text().replace('Version: 5.064-1\n','Version: 5.064-2\n'))
assert 'Version: 5.064-2\n' in control.read_text()
def tar_bytes(directory):
 b=io.BytesIO()
 with tarfile.open(fileobj=b,mode='w:gz',format=tarfile.GNU_FORMAT) as t:
  for p in sorted(directory.rglob('*')):
   # Stable order, ownership, and build timestamp.
   info=t.gettarinfo(str(p),arcname='./'+str(p.relative_to(directory)))
   info.uid=info.gid=0;info.uname=info.gname='root';info.mtime=timestamp
   if p.is_file(): 
    with p.open('rb') as f:t.addfile(info,f)
   else:t.addfile(info)
 return b.getvalue()
def ipk(control_dir,data_dir,target):
 md5=control_dir/'md5sums'
 if md5.exists():
  md5.write_text(''.join(hashlib.md5(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(data_dir))+'\n' for p in sorted(data_dir.rglob('*')) if p.is_file()))
 with tarfile.open(target,'w:gz',format=tarfile.GNU_FORMAT) as t:
  for name,body in [('debian-binary',b'2.0\n'),('control.tar.gz',tar_bytes(control_dir)),('data.tar.gz',tar_bytes(data_dir))]:
   info=tarfile.TarInfo('./'+name);info.size=len(body);info.mode=0o644;info.uid=info.gid=0;info.mtime=timestamp;t.addfile(info,io.BytesIO(body))
panel=out/'zapret-manager-lt500_5.064-2_mipsel_24kc.ipk';ipk(panelwork/'control',pdata,panel)
# Cache one cleaned domain list; do not install IP lists or resolve all domains.
tachyon_commit='d7469734ac1f5f631523d75c1de439985dc62859'
raw=work/'tachyon-ru-blocked.lst'
urllib.request.urlretrieve('https://raw.githubusercontent.com/Dushnilin/tachyon-lists/'+tachyon_commit+'/release/domains/ru_blocked.lst',raw)
assert raw.stat().st_size<5000000
sdir=repo/'package/lt500-bundle-support/files'
supportwork=work/'support';cdir=supportwork/'control';sdata=supportwork/'data';cdir.mkdir(parents=True);sdata.mkdir()
def put(src,dest,mode=0o755):
 p=sdata/dest;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,p);p.chmod(mode)
put(sdir/'lt500-zapret-configure','usr/libexec/lt500-zapret-configure')
put(sdir/'lt500-rkn-update','usr/libexec/lt500-rkn-update')
put(sdir/'rkn-filter.awk','usr/share/lt500/rkn-filter.awk',0o644)
put(sdir/'92-lt500-zapret','etc/uci-defaults/92-lt500-zapret')
put(sdir/'lt500-zapret-once','etc/init.d/lt500-zapret-once')
cached=sdata/'opt/zapret/ipset/zapret-hosts-rkn.txt';cached.parent.mkdir(parents=True)
with cached.open('w') as f:run('awk','-f',sdir/'rkn-filter.awk',root/'opt/zapret/ipset/zapret-hosts-google.txt',raw,stdout=f)
domains=len(cached.read_text().splitlines());assert 100<=domains<=200000
cached.chmod(0o644)
keep=sdata/'lib/upgrade/keep.d/lt500-support';keep.parent.mkdir(parents=True)
keep.write_text('/etc/lt500-bundle/\n/opt/zapret/ipset/zapret-hosts-rkn.txt\n');keep.chmod(0o644)
cdir.joinpath('control').write_text('Package: lt500-bundle-support\nVersion: 1.0-1\nArchitecture: mipsel_24kc\nDepends: zapret, curl\nSection: net\nDescription: LT500 RC7 cached Tachyon list and one-time Zapret startup migration\n')
cdir.joinpath('postinst').write_text('#!/bin/sh\n[ -n "$IPKG_INSTROOT" ] && exit 0\n/etc/init.d/lt500-zapret-once enable\n/usr/libexec/lt500-zapret-configure || exit 1\n/etc/init.d/lt500-zapret-once start\n')
cdir.joinpath('postinst').chmod(0o755)
support=out/'lt500-bundle-support_1.0-1_mipsel_24kc.ipk';ipk(cdir,sdata,support)
allowed=set()
for folder in (pdata,sdata):
 allowed.update(str(p.relative_to(folder)) for p in folder.rglob('*') if not p.is_dir())
for p in (root/'usr/lib/opkg/info/zapret-manager-lt500.list').read_text().splitlines():allowed.add(p.lstrip('/'))
conf=work/'opkg.conf';conf.write_text('dest root /\narch all 1\narch noarch 1\narch mipsel_24kc 10\n')
for p in ('var/lock','var/opkg-lists','tmp'):(root/p).mkdir(parents=True,exist_ok=True)
run('qemu-mipsel-static','-cpu','24Kc','-L',root,root/'bin/opkg.real','--offline-root',root,'--conf',conf,'install',panel,support,env=dict(os.environ,IPKG_NO_SCRIPT='1',IPKG_INSTROOT=str(root)))
assert not any(p.startswith('tmp/') for p in before)
for p in (root/'tmp').iterdir():
 if p.is_dir() and not p.is_symlink():shutil.rmtree(p)
 else:p.unlink()
# rc.common sees these fixed bootstrap hooks in the first boot's initial glob.
for name,target in [('S98lt500-zapret-once','../init.d/lt500-zapret-once'),('S21zapret','../init.d/zapret')]:
 p=root/'etc/rc.d'/name
 if p.is_symlink():p.unlink()
 p.symlink_to(target);allowed.add('etc/rc.d/'+name)
(root/'etc/lt500-allinone').write_text('LT500v2 v2.0-zapret-rc7 all-in-one\n')
caps=root/'etc/lt500-capabilities'
caps.write_text(caps.read_text().replace('awg2-i1-tun-steer213-panel5-noradio','awg2-i1-tun-steer214-panel5-lite'))
allowed.update(['etc/lt500-allinone','etc/lt500-capabilities'])
# Generated pages normally appear on first boot, but upgrade any preinstalled ones.
source=installer.read_text()
for m in re.finditer(r"cat > ['\"]([^'\"]+)['\"] << 'ZM_INSTALLER_EOF'\n([\s\S]*?)\nZM_INSTALLER_EOF",source):
 name=m[1].replace('$_zmi_st/','/opt/zapret-manager-luci/').lstrip('/')
 p=root/name
 if p.is_file():p.write_text(m[2]+'\n');allowed.add(name)
after=fingerprint(root)
def package_meta(p):return p=='usr/lib/opkg/status' or p.startswith(('usr/lib/opkg/info/zapret-manager-lt500.','usr/lib/opkg/info/lt500-bundle-support.'))
diff=[p for p in before.keys()|after.keys() if before.get(p)!=after.get(p) and p not in allowed and not package_meta(p)]
assert not diff,diff
def versions(text):
 return {m.group(1):m.group(2) for m in re.finditer(r'^Package: (.+)\nVersion: (.+)$',text,re.M)}
prior=versions(prior_status);current=versions((root/'usr/lib/opkg/status').read_text())
assert current['steer-core']==prior['steer-core']=='2.1.4-1'
assert {p for p in prior if prior[p]!=current[p]}=={'zapret-manager-lt500'}
assert set(current)-set(prior)=={'lt500-bundle-support'}
run('python3','scripts/lt500/check-module-abi.py',root)
run('python3','scripts/lt500/test-zapret-rc7.py',root)
run('qemu-mipsel-static','-cpu','24Kc','-L',root,root/'usr/sbin/steerd','--version')
fs=work/'rootfs.squashfs'
run('mksquashfs',root,fs,'-nopad','-noappend','-no-sparse','-no-xattrs','-comp','xz','-b','256K','-processors','2','-mkfs-time',timestamp,'-all-time',timestamp,'-no-progress',stdout=subprocess.DEVNULL)
image=out/'Cudy-LT500v2-OpenWrt-23.05.5-v2.0-zapret-rc7-sysupgrade.bin';image.write_bytes(data[:offset]+fs.read_bytes())
run(work/'padjffs2',image,'64');assert image.stat().st_size<=15872*1024
meta=work/'metadata.json';run(work/'fwtool','-i',meta,old);run(work/'fwtool','-I',meta,image);run(work/'fwtool','-i',work/'metadata-new.json',image)
assert meta.read_bytes()==(work/'metadata-new.json').read_bytes()
assert image.read_bytes()[:offset]==data[:offset]
check=work/'roundtrip';run('unsquashfs','-no-progress','-o',offset,'-d',check,image,stdout=subprocess.DEVNULL)
assert fingerprint(check)==after,'SquashFS roundtrip changed bytes, owners, modes or symlinks'
manifest=oldfiles/'openwrt-ramips-mt76x8-cudy_lt500-v2.manifest'
(out/manifest.name).write_text(manifest.read_text().replace('zapret-manager-lt500 - 5.064-1','zapret-manager-lt500 - 5.064-2')+'lt500-bundle-support - 1.0-1\n')
profiles=json.loads((oldfiles/'profiles.json').read_text());prof=profiles['profiles']['cudy_lt500-v2'];prof['images']=[i for i in prof['images'] if i['type']=='sysupgrade'];assert len(prof['images'])==1
prof['images'][0].update(name=image.name,sha256=sha(image))
if 'size' in prof['images'][0]:prof['images'][0]['size']=image.stat().st_size
(out/'profiles.json').write_text(json.dumps(profiles,indent=2)+'\n')
steer=oldfiles/'steer-core-2.1.4-1_mipsel_24kc.ipk';assert sha(steer)=='2bfcfcec5e20b622e82f875755c9b57169a709b7bac2e9ade10f7a5cf45e9f21';shutil.copyfile(steer,out/steer.name)
pm={'format':1,'board':'cudy,lt500-v2','capability':'awg2-i1-tun-steer214-panel5-lite','version':'5.064-2','file':panel.name,'sha256':sha(panel)}
(out/'lt500-panel.json').write_text(json.dumps(pm,indent=2)+'\n')
info={'release':'v2.0-zapret-rc7','build_commit':os.environ['GITHUB_SHA'],'openwrt':'23.05.5','kernel':current['kernel'],'firmware_sha256':sha(image),
'base':{'release':'v2.0-zapret-rc6','image_sha256':sha(old),'kernel_prefix_bytes':offset,'unchanged_kernel_modules':69,'steer':'2.1.4-1 unchanged'},
'manager':{'version':'5.064-2','upstream_source':'be2baf3db38dcefafc104a5460fe5829315ab514','radio':False,'themes':False,'animations':False,'warp_state_recovery':True},
'tachyon':{'source_commit':tachyon_commit,'raw_sha256':sha(raw),'filtered_sha256':sha(cached),'domains':domains},
'validation':{'abi':True,'squashfs_roundtrip':True,'hardware_coldboot':False,'live_warp_traffic':False}}
(out/'BUILD-INFO.json').write_text(json.dumps(info,indent=2)+'\n')
notes=(repo/'docs/LT500v2-RC7-INSTALL-RU.md').read_text().replace('@IMAGE_SHA256@',sha(image)).replace('@IMAGE_BYTES@',str(image.stat().st_size))
for name in ('INSTALL-RC7.md','INSTALL-RC7-RU.md'):(out/name).write_text(notes)
# Independent package validation uses this image's own MIPS opkg and empty feeds.
script=(repo/'scripts/lt500/check-independent-packages.py').read_text().replace('len(packages) == 2','len(packages) == 3')
probe=work/'check-independent.py';probe.write_text(script);run('python3',probe,check,out)
(out/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
bundle=(repo/'scripts/lt500/package-bundle.py').read_text().replace('rc6','rc7').replace('RC6','RC7')
pack=work/'package-bundle.py';pack.write_text(bundle);run('python3',pack,out)
print(json.dumps(info,ensure_ascii=False,indent=2))
print('RC7 bytes:',image.stat().st_size,'RC6 bytes:',len(data),'panel bytes:',panel.stat().st_size,'cached domains:',domains,flush=True)
