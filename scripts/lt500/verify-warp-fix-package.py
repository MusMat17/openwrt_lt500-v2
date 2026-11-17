#!/usr/bin/env python3
"""Use the published RC7 router opkg to install the new panel, without scripts."""
import hashlib,os,pathlib,subprocess,sys,urllib.request
root=pathlib.Path(sys.argv[1]).resolve();ipk=pathlib.Path(sys.argv[2]).resolve();root.parent.mkdir(parents=True,exist_ok=True)
image=root.parent/'rc7.bin'
urllib.request.urlretrieve('https://github.com/MusMat17/openwrt_lt500-v2/releases/download/v2.0-zapret-rc7/Cudy-LT500v2-OpenWrt-23.05.5-v2.0-zapret-rc7-sysupgrade.bin',image)
assert hashlib.sha256(image.read_bytes()).hexdigest()=='924a8ba5f01369277759a4bb791f2be7856ceca56d08d6382cc38a1cc7a0d244'
subprocess.run(['unsquashfs','-no-progress','-o','2303512','-d',str(root),str(image)],check=True,stdout=subprocess.DEVNULL)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protected={str(p.relative_to(root)):digest(p) for p in (root/'lib/modules').rglob('*') if p.is_file()}
protected['usr/sbin/steerd']=digest(root/'usr/sbin/steerd')
for d in ('var/lock','var/opkg-lists','tmp'):(root/d).mkdir(parents=True,exist_ok=True)
conf=root.parent/'opkg.conf';conf.write_text('dest root /\narch all 1\narch noarch 1\narch mipsel_24kc 10\n')
p=subprocess.run(['qemu-mipsel-static','-cpu','24Kc','-L',str(root),str(root/'bin/opkg.real'),'--offline-root',str(root),'--conf',str(conf),'install',str(ipk)],env=dict(os.environ,IPKG_NO_SCRIPT='1',IPKG_INSTROOT=str(root)),capture_output=True,text=True)
assert p.returncode==0 and 'Collected errors:' not in p.stderr,(p.stdout,p.stderr)
assert all(digest(root/k)==v for k,v in protected.items())
assert 'Version: 5.064-3\n' in (root/'usr/lib/opkg/info/zapret-manager-lt500.control').read_text()
assert (root/'usr/libexec/lt500-warp-state-apply').stat().st_mode&0o777==0o755
subprocess.run(['python3','scripts/lt500/check-module-abi.py',str(root)],check=True)
print('Router MIPS opkg installed 5.064-3 with empty feeds and normal dependencies; Steer and all kernel modules unchanged')
