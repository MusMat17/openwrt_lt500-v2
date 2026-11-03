# Cudy LT500v2 (R25) — OpenWrt 23.05.5

This branch is intentionally based on OpenWrt commit:

`10cc5fcd00c648b1a3b4043734c49c18f294041f`

which matches the OpenWrt 23.05.5 revision currently installed by Cudy's
official intermediary firmware (`r24106-10cc5fcd00`).

## v2.0-zapret-rc4 All-in-One

RC4 updates Zapret Manager to **4.996-1** and includes the latest published
stable Steer core and all six modules at **2.0.5-1**, retaining the RC2 hardware, Linux 5.15.167, TUN and AmneziaWG
2.0 I1-I5 support. WAN/4G switching remains manual; no mwan3 is included.

Pinned source revisions:

- Zapret Manager: `171791b26e3959de50b800a7c80365fc2b7f3fce`.
- Steer 2.0.5: `239c2897a726bc66dbe1900a3f4595d4d9b5f62d`.
- AmneziaWG kernel: `ae0924ca700520ca34c5bdbcfd05b2f683ea9353`.
- AmneziaWG tools: `61e741780e8465a67a7d7fb6cffe14a8a15d624a`.
- Zapret remains 72.20260307 from its pinned feed revision.

### Independent panel updates

The panel package retains settings, keeps one compressed previous-panel backup,
and restores the previous dashboard and immediate settings on installation
failure. A later manual rollback preserves current tunnel settings and pins
the previous panel until a different installer is installed. Updates need
3200 KiB free overlay. Bootstrap detects an older retained dashboard after
sysupgrade and applies the packaged version without downloading an installer.

RC4 uses capability `awg2-i1-tun-steer205-panel4` and channel `lt500-panel-steer205-v4`.
The old RC2 and RC3 panel channels are untouched. The updater validates the board, capability,
version, fixed package filename and SHA256 before ordinary opkg installation.
New upstream panels must be reviewed and published as compatible LT500 packages.
Features needing new kernel modules require a matching firmware update.

The actual 4.996 installer is patched to retain the LT500 update action and
block external AWG installation and Zapret/AWG replacement. Direct worker and selective-purge paths are protected as well; page restoration
uses the packaged installer, and every self-update path uses the compatible channel.
Protected firmware packages are also retained when a historical owned-package list is cleaned up.

### Validation and installation

CI checks update/rollback behavior and executes firmware guards from the actual
patched panel backend before compiling the toolchain. Publication requires
all six Steer modules at the core version, the expected panel version, metadata
for the correct board, valid image size, all kmods matching the built kernel ABI,
and TUN/AWG/UDP prerequisites. The checked ZIP and its external SHA256 are
published together with the image, panel/Steer IPKs and Russian instructions.

RC4 is a release candidate and needs its own on-router acceptance test.
The standalone RC1 TUN/VLESS and AWG I1 fixes were tested by the owner.
See [RC4 install instructions](docs/LT500v2-RC4-INSTALL-RU.md) for upgrade,
backup, panel rollback and post-boot checks. Published instructions include the
actual image size, SHA256 and kernel package version.

Do not install RC1 kmods on RC4. The original RC1 TUN package needed a distinct
version because opkg can merge same-version local and feed candidates carrying
different kernel ABI dependencies. RC4 builds TUN and the kernel together.

## Confirmed hardware

- SoC: MediaTek MT7628AN
- RAM: 128 MiB DDR2
- SPI NOR: 16 MiB
- Board ID / uImage name: R25
- 2.4 GHz: MT7628 WMAC
- 5 GHz: MT7663E
- LTE modem: Quectel EC200A
- USB ID: 2c7c:6005
- LTE data mode used by Cudy stock firmware: CDC-ECM
- LTE network device: usb0
- AT control port: /dev/ttyUSB1

## Flash layout

- 0x000000-0x030000 u-boot
- 0x030000-0x040000 u-boot-env
- 0x040000-0x050000 factory
- 0x050000-0xfd0000 firmware (15872 KiB)
- 0xfd0000-0xfe0000 debug
- 0xfe0000-0xff0000 backup
- 0xff0000-0x1000000 bdinfo

## Important change vs draft upstream PR

The draft upstream PR assumes QMI/ModemManager for LTE. The actual LT500v2
tested here contains a Quectel EC200A whose stock Cudy configuration is
CDC-ECM:

- driver: kmod-usb-net-cdc-ether
- data interface: usb0
- protocol: DHCP
- AT port: /dev/ttyUSB1

This branch therefore uses CDC-ECM instead of QMI.

## Package-manager safety guard

This image deliberately blocks the normal `opkg upgrade` command.

A full package upgrade is unsafe on this custom firmware because the public
OpenWrt 23.05.5 repositories contain packages built for the official target
and kernel ABI. Mixing them with this custom LT500v2 image can break kernel
modules or make the router unbootable.

Normal package-management operations remain available:

```sh
opkg update
opkg install <package>
opkg remove <package>
```

Install individual **userspace** packages only. Do not install `kmod-*`
packages from the official OpenWrt feeds unless they were built for the exact
kernel ABI used by this image.

The guard is intended to prevent accidental damage; it is not a security
boundary. A root user can still deliberately bypass it by invoking the real
binary directly as `/bin/opkg.real`.

## LTE validation history

The LT500v2 port has been validated on real hardware, including a full cold-power boot. The Quectel EC200A restores its saved LTE/ECM session itself, so no board-specific AT startup daemon is required. `chat` remains available for diagnostics.

After flashing and confirming that `usb0` exists, use the following only
for a controlled LTE test (replace APN as required):

```sh
DEV=/dev/ttyUSB1

chat -t 5 -E -V ABORT ERROR '' AT OK < "$DEV" > "$DEV"
chat -t 5 -E -V ABORT ERROR '' 'AT+CGACT=0,1' OK < "$DEV" > "$DEV"
chat -t 5 -E -V ABORT ERROR '' 'AT+QICSGP=1,1,"internet.mts.ru","","",0' OK < "$DEV" > "$DEV"
chat -t 10 -E -V ABORT ERROR '' 'AT+CGACT=1,1' OK < "$DEV" > "$DEV"
chat -t 5 -E -V ABORT ERROR '' 'AT+QNETDEVCTL=0,1,0' OK < "$DEV" > "$DEV"
chat -t 10 -E -V ABORT ERROR '' 'AT+QNETDEVCTL=3,1,1' OK < "$DEV" > "$DEV"

ip link show usb0
ifup wwan
ubus call network.interface.wwan status
```

Do not use third-party kernel modules built for another kernel ABI.

## Installation path

Stock Cudy firmware -> official Cudy intermediary firmware -> this branch's
sysupgrade image.

Before flashing a newly built image:

```sh
sysupgrade -T /tmp/openwrt-ramips-mt76x8-cudy_lt500-v2-squashfs-sysupgrade.bin
```

Only proceed to an actual sysupgrade after the image check passes.
