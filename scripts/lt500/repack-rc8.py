#!/usr/bin/env python3
"""Place the complete fixed panel in verified RC7 SquashFS, retaining its kernel."""
import hashlib,io,json,os,pathlib,re,shutil,stat,struct,subprocess,tarfile,urllib.request,zipfile,zlib
repo=pathlib.Path(__file__).resolve().parents[2];os.chdir(repo);assert os.geteuid()==0
work=repo/'tmp/rc8';work.mkdir(parents=True,exist_ok=True)
out=repo/'bin/targets/ramips/mt76x8/release';out.mkdir(parents=True,exist_ok=True)
def run(*a,**kw):return subprocess.run(list(map(str,a)),check=True,**kw)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
archive=work/'RC7.zip'
urllib.request.urlretrieve('https://github.com/MusMat17/openwrt_lt500-v2/releases/download/v2.0-zapret-rc7/LT500v2-OpenWrt-23.05.5-RC7-zapret-bundle.zip',archive)
assert sha(archive)=='7305cf729246b73cdb23c73a9ebf07f2f0cf9fc8bfa95d0d4864f99640a6c780'
original=work/'original'
with zipfile.ZipFile(archive) as z:
 assert all(pathlib.Path(n).name==n for n in z.namelist());z.extractall(original)
for line in (original/'SHA256SUMS').read_text().splitlines():
 digest,name=line.split('  ',1);assert sha(original/name)==digest,name
old=original/'Cudy-LT500v2-OpenWrt-23.05.5-v2.0-zapret-rc7-sysupgrade.bin'
assert sha(old)=='924a8ba5f01369277759a4bb791f2be7856ceca56d08d6382cc38a1cc7a0d244'
data=old.read_bytes();magic,hcrc,timestamp,size,load,entry,dcrc=struct.unpack('>7I',data[:28]);offset=64+size
assert magic==0x27051956 and offset==2303512
assert zlib.crc32(data[:4]+b'\0'*4+data[8:64])==hcrc and zlib.crc32(data[64:offset])==dcrc and data[offset:offset+4]==b'hsqs'
root=work/'root';run('unsquashfs','-no-progress','-o',offset,'-d',root,old,stdout=subprocess.DEVNULL)
def fingerprint(folder):
 result={}
 for p in folder.rglob('*'):
  st=p.lstat()
  if stat.S_ISDIR(st.st_mode):continue
  body=str(p.readlink()) if p.is_symlink() else sha(p) if p.is_file() else str(st.st_rdev)
  result[str(p.relative_to(folder))]=(st.st_mode,st.st_uid,st.st_gid,body)
 return result
before=fingerprint(root)
status_before=(root/'usr/lib/opkg/status').read_text()
panel=out/'zapret-manager-lt500_5.064-3_mipsel_24kc.ipk'
urllib.request.urlretrieve('https://github.com/MusMat17/openwrt_lt500-v2/releases/download/lt500-rc7-warp-state-fix/'+panel.name,panel)
assert sha(panel)=='6d61de8906da7fc5018303563f956a1b4beb0796f20ec712775ecaf8dcc5c724'
conf=work/'opkg.conf';conf.write_text('dest root /\narch all 1\narch noarch 1\narch mipsel_24kc 10\n')
for name in ('var/lock','var/opkg-lists','tmp'):(root/name).mkdir(parents=True,exist_ok=True)
run('qemu-mipsel-static','-cpu','24Kc','-L',root,root/'bin/opkg.real','--offline-root',root,'--conf',conf,'install',panel,env=dict(os.environ,IPKG_NO_SCRIPT='1',IPKG_INSTROOT=str(root)))
assert not any(p.startswith('tmp/') for p in before)
for p in (root/'tmp').iterdir():
 if p.is_dir() and not p.is_symlink():shutil.rmtree(p)
 else:p.unlink()
installer=root/'usr/libexec/zapret-manager-installer'
(work/'installer-fixed.sh').write_bytes(installer.read_bytes())
run('python3','scripts/lt500/check-panel-installer.py',installer)
run('python3','scripts/lt500/check-panel-payloads.py',installer)
run('python3','scripts/lt500/test-warp-rc7.py',installer)
with tarfile.open(original/'zapret-manager-lt500_5.064-2_mipsel_24kc.ipk') as pkg:
 m=next(m for m in pkg if m.name.endswith('data.tar.gz'))
 with tarfile.open(fileobj=io.BytesIO(pkg.extractfile(m).read())) as p:
  m=next(m for m in p if m.name.endswith('zapret-manager-installer'))
  (work/'installer-old.sh').write_bytes(p.extractfile(m).read())
run('python3','scripts/lt500/test-warp-recovery.py',work/'installer-old.sh',installer)
run('python3','scripts/lt500/stage-panel-rom-rc8.py',root)
romhelper=root/'usr/libexec/lt500-panel-rom-ready'
shutil.copyfile(repo/'package/zapret-manager-lt500/files/lt500-panel-rom-ready',romhelper);romhelper.chmod(0o755)
apply=root/'usr/libexec/lt500-panel-apply'
guard='''# A matching ROM installer means all panel code is already in SquashFS.
if [ "${1:-apply}" = apply ] && [ -s /rom/usr/share/lt500/panel-installer.sha256 ] &&
   [ "$(sha256sum "$INSTALLER" | awk '{print $1}')" = "$(cat /rom/usr/share/lt500/panel-installer.sha256)" ]; then
 exec /usr/libexec/lt500-panel-rom-ready
fi
'''
text=apply.read_text();marker='mkdir "$LOCK" 2>/dev/null';assert text.count(marker)==1;apply.write_text(text.replace(marker,guard+'\n'+marker))
defaults=root/'etc/uci-defaults/91-lt500-panel-rom';defaults.write_text('#!/bin/sh\n/usr/libexec/lt500-panel-rom-ready >/tmp/zapret-manager-bootstrap.log 2>&1\n');defaults.chmod(0o755)
status=(root/'usr/lib/opkg/status').read_text()
assert re.search(r'Package: zapret-manager-lt500\nVersion: 5.064-3\n',status)
assert re.search(r'Package: zapret-manager-lt500\n[\s\S]*?Status: install [^\n]* installed\n',status)
(root/'etc/lt500-allinone').write_text('LT500v2 v2.0-zapret-rc8 all-in-one; panel ready in ROM\n')
listing=root/'usr/lib/opkg/info/zapret-manager-lt500.list'
names=listing.read_text().splitlines()
for name in ('/usr/libexec/lt500-panel-rom-ready','/etc/uci-defaults/91-lt500-panel-rom','/usr/share/lt500/panel-rom.files','/usr/share/lt500/panel-installer.sha256','/usr/bin/zms','/usr/bin/zmw'):
 if name not in names:names.append(name)
listing.write_text('\n'.join(names)+'\n')
after=fingerprint(root)
allowed=set(n.lstrip('/') for n in names)
allowed.update(line.split(' ',2)[2] for line in (root/'usr/share/lt500/panel-rom.files').read_text().splitlines())
allowed.update(['www/zm-webui.html','etc/lt500-allinone','usr/lib/opkg/status'])
unexpected=[p for p in before.keys()|after.keys() if before.get(p)!=after.get(p) and p not in allowed and not p.startswith('usr/lib/opkg/info/zapret-manager-lt500.')]
assert not unexpected,unexpected
def versions(s):return {m[1]:m[2] for m in re.finditer(r'^Package: (.+)\nVersion: (.+)$',s,re.M)}
prior=versions(status_before)
current=versions(status)
assert prior.keys()==current.keys()
assert {n for n in prior if prior[n]!=current[n]}=={'zapret-manager-lt500'}
run('python3','scripts/lt500/check-module-abi.py',root)
run('python3','scripts/lt500/test-zapret-rc7.py',root)
run('python3','scripts/lt500/test-panel-rom-rc8.py',root)
fs=work/'rootfs.squashfs'
run('mksquashfs',root,fs,'-nopad','-noappend','-no-sparse','-no-xattrs','-comp','xz','-b','256K','-processors','2','-mkfs-time',timestamp,'-all-time',timestamp,'-no-progress',stdout=subprocess.DEVNULL)
image=out/'Cudy-LT500v2-OpenWrt-23.05.5-v2.0-zapret-rc8-sysupgrade.bin';image.write_bytes(data[:offset]+fs.read_bytes());run(work/'padjffs2',image,'64')
meta=work/'metadata.json';run(work/'fwtool','-i',meta,old);run(work/'fwtool','-I',meta,image);run(work/'fwtool','-i',work/'new-metadata.json',image)
assert meta.read_bytes()==(work/'new-metadata.json').read_bytes() and image.read_bytes()[:offset]==data[:offset]
assert image.stat().st_size<=15872*1024
check=work/'roundtrip';run('unsquashfs','-no-progress','-o',offset,'-d',check,image,stdout=subprocess.DEVNULL)
assert fingerprint(check)==after,'Final SquashFS differs from the tested root'
manifest=''.join(n+' - '+current[n]+'\n' for n in sorted(current));(out/'openwrt-ramips-mt76x8-cudy_lt500-v2.manifest').write_text(manifest)
profiles=json.loads((original/'profiles.json').read_text());prof=profiles['profiles']['cudy_lt500-v2'];prof['images']=[x for x in prof['images'] if x['type']=='sysupgrade'];assert len(prof['images'])==1
prof['images'][0].update(name=image.name,sha256=sha(image))
if 'size' in prof['images'][0]:prof['images'][0]['size']=image.stat().st_size
(out/'profiles.json').write_text(json.dumps(profiles,indent=2)+'\n')
for name in ('steer-core-2.1.4-1_mipsel_24kc.ipk','lt500-bundle-support_1.0-1_mipsel_24kc.ipk'):shutil.copyfile(original/name,out/name)
pm=json.loads((original/'lt500-panel.json').read_text());pm.update(version='5.064-3',file=panel.name,sha256=sha(panel));(out/'lt500-panel.json').write_text(json.dumps(pm,indent=2)+'\n')
info={'release':'v2.0-zapret-rc8','build_commit':os.environ['GITHUB_SHA'],'openwrt':'23.05.5','kernel':current['kernel'],'firmware_sha256':sha(image),'base':{'release':'v2.0-zapret-rc7','firmware_sha256':sha(old),'unchanged_kernel_bytes':offset,'unchanged_kmods':69,'steer':'2.1.4-1 unchanged'},'manager':{'version':'5.064-3','package_sha256':sha(panel),'ready_in_squashfs':True,'firstboot_full_install':False,'rom_manifest_sha256':sha(root/'usr/share/lt500/panel-rom.files'),'radio':False,'themes':False,'animations':False},'tachyon':{'domains':len((root/'opt/zapret/ipset/zapret-hosts-rkn.txt').read_text().splitlines()),'cache_sha256':sha(root/'opt/zapret/ipset/zapret-hosts-rkn.txt')},'validation':{'abi':True,'squashfs_roundtrip':True,'low_space_firstboot':True,'hardware_coldboot':False,'live_warp_traffic':False}}
(out/'BUILD-INFO.json').write_text(json.dumps(info,indent=2)+'\n')
notes=(repo/'docs/LT500v2-RC8-INSTALL-RU.md').read_text().replace('@IMAGE_SHA256@',sha(image)).replace('@IMAGE_BYTES@',str(image.stat().st_size))
for name in ('INSTALL-RC8.md','INSTALL-RC8-RU.md'):(out/name).write_text(notes)
probe=work/'package-probe.py';probe.write_text((repo/'scripts/lt500/check-independent-packages.py').read_text().replace('len(packages) == 2','len(packages) == 3'));run('python3',probe,check,out)
(out/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
pack=work/'package-bundle.py';pack.write_text((repo/'scripts/lt500/package-bundle.py').read_text().replace('RC6','RC8').replace('rc6','rc8'));run('python3',pack,out)
print(json.dumps(info,indent=2));print('RC8 image bytes:',image.stat().st_size,'RC7 image bytes:',len(data),flush=True)
