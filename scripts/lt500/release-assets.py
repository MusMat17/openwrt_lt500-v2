#!/usr/bin/env python3
import hashlib,json,pathlib,shutil
base=pathlib.Path('bin/targets/ramips/mt76x8'); out=base/'release';out.mkdir(exist_ok=True)
image='Cudy-LT500v2-OpenWrt-23.05.5-v2.0-zapret-rc2-sysupgrade.bin'
shutil.copy2(base/'openwrt-ramips-mt76x8-cudy_lt500-v2-squashfs-sysupgrade.bin',out/image)
for f in ('openwrt-ramips-mt76x8-cudy_lt500-v2.manifest','profiles.json'):
    shutil.copy2(base/f,out/f)
pkgs=list(pathlib.Path('bin/packages').glob('mipsel_24kc/*/zapret-manager-lt500_2.48-2_mipsel_24kc.ipk'))
assert len(pkgs)==1, pkgs
pkg=pkgs[0];shutil.copy2(pkg,out/pkg.name)
manifest={'format':1,'board':'cudy,lt500-v2','capability':'awg2-i1-tun-steer203','version':'2.48-2','file':pkg.name,'sha256':hashlib.sha256(pkg.read_bytes()).hexdigest()}
(out/'lt500-panel.json').write_text(json.dumps(manifest,indent=2)+'\n')
notes='''# Cudy LT500v2 / R25 — OpenWrt 23.05.5 — RC2

Only for Cudy LT500 v2 (`cudy,lt500-v2`), 16 MiB flash / MT7628AN.

Includes LTE CDC-ECM, LuCI, Zapret, Zapret Manager 2.48-2, Steer 2.0.3
and all six modules (VLESS, Hysteria2, Proxy, XSteer, Obfs, TGWS), TUN,
and AmneziaWG 2.0 with I1–I5 support. AmneziaWG uses the same source
revisions as the hardware-tested RC1 I1 fix. All kernel modules are built
against the RC2 kernel ABI; do not install the old RC1 module archives.

## Upgrade from RC1

Save the backup to your computer before flashing:

```sh
umask 077
# RC1 did not yet register these dashboard settings for sysupgrade.
for p in /etc/zm-steer/ /etc/zm-awg/ /etc/zm-warp-own.conf /etc/steer/ /opt/zapret-manager-luci/state/; do
    grep -qxF "$p" /etc/sysupgrade.conf 2>/dev/null || echo "$p" >> /etc/sysupgrade.conf
done
sysupgrade -b /tmp/LT500v2-before-RC2.tar.gz
```

Copy the sysupgrade image to `/tmp`, verify SHA256 against SHA256SUMS,
and run the image test. Flash only if the test returns success:

```sh
IMG=/tmp/Cudy-LT500v2-OpenWrt-23.05.5-v2.0-zapret-rc2-sysupgrade.bin
sha256sum "$IMG"
sysupgrade -T "$IMG" && sysupgrade "$IMG"
```

This keeps the normal sysupgrade configuration backup. Do not use `-F`.
The router reboots; allow about two minutes for dashboard installation.
Existing `/etc/config` settings are retained. The RC2 bootstrap detects
and replaces a preserved RC1 dashboard while retaining panel state.
For a clean installation, save your backup and use `sysupgrade -n`.

## Independent dashboard updates

The dashboard update button uses only the reviewed LT500 package channel
in this repository. Original upstream installers cannot replace the panel
through that button. A future compatible panel release can add features
without reflashing. Features requiring a different kernel/module still
need a matching firmware release.

For a manual update, copy the compatible `zapret-manager-lt500_*.ipk`
to `/tmp` and install it with `opkg install /tmp/<package>.ipk`.
Its post-install script preserves settings and backs up the previous panel
to `/root/lt500-panel-backup/previous.tar.gz` (root-only access). An install
failure restores the previous dashboard and immediate pre-update settings.
If a later manual rollback is needed:

```sh
/usr/libexec/lt500-panel-apply rollback
```

Manual rollback preserves the current tunnel settings. It stops automatic
re-application until you remove `/etc/lt500-panel/rollback.sha256` or install
a panel package with a different installer checksum. Only one previous panel
backup is kept. Updating the panel needs at least 2300 KiB free in `/overlay`.

## Checks after boot

```sh
ubus call system board
df -h /overlay
modprobe tun
modprobe amneziawg
ls -l /dev/net/tun
opkg list-installed | grep -E '^(steer-[^ ]+|kmod-tun|kmod-amneziawg|amneziawg-tools|zapret-manager-lt500) '
tail -n 30 /tmp/zapret-manager-bootstrap.log
```

Then test your saved VLESS subscription and WARP in the panel.

This is a release candidate. RC1 standalone TUN/VLESS and the AmneziaWG I1
fix have been confirmed on the router; the combined RC2 image still needs
its own hardware acceptance test.
'''
(out/'INSTALL-RC2.md').write_text(notes)
sha=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS')
(out/'SHA256SUMS').write_text(sha)
print(sha)
