# Cudy LT500v2 (R25) — OpenWrt 23.05.5

This branch is intentionally based on OpenWrt commit:

`10cc5fcd00c648b1a3b4043734c49c18f294041f`

which matches the OpenWrt 23.05.5 revision currently installed by Cudy's
official intermediary firmware (`r24106-10cc5fcd00`).

## v2.0-zapret-rc5 All-in-One

RC5 includes Zapret Manager **5.064-1** without the radio feature and official
Steer **2.1.3-1** with its matching signed protocol seed and trust keys, including
net1 **1.4.3**. It retains the tested RC2 hardware configuration, Linux 5.15.167,
TUN and AmneziaWG 2.0 I1-I5. WAN/4G switching remains manual.

Pinned sources:

- Manager: `be2baf3db38dcefafc104a5460fe5829315ab514`.
- Steer: `9e05393b9747f4f85cd1ede38e34d03c6583b187`.
- Official Steer IPK SHA256: `81a290efe633fc09a96bbb0d3808473c581290d61a28faac0ac22ad3c7297a3e`.
- AWG kernel: `ae0924ca700520ca34c5bdbcfd05b2f683ea9353`.
- AWG tools: `61e741780e8465a67a7d7fb6cffe14a8a15d624a`.
- Zapret: 72.20260307 from the retained pinned feed.

### Protocols and migration

Steer 2.1 uses signed `.s2p` plugins rather than six separate protocol IPKs.
The official core binary, libraries, seed and trust keys are kept together.
The firmware adds one first-start migration hook before steerd: an existing
spec selects required plugins, with the signed offline seed as fallback.
Fresh installs without a spec defer optional plugin installation to the panel.
TGWS is outside the upstream seed and needs an online signed plugin install.
The standalone release asset is the original official IPK, byte-for-byte.

### Panel updates and validation

Radio code, backend methods, station catalog, audio player and CSS are physically
removed (about 58 KB uncompressed). Wi-Fi is unaffected. The panel uses capability
`awg2-i1-tun-steer213-panel5-noradio` and channel `lt500-panel-steer213-noradio`.
Earlier channels and firmware releases remain untouched. Panel updates retain
settings and one compressed previous-panel backup, restore on installation
failure and support `/usr/libexec/lt500-panel-apply rollback`. They require
3200 KiB free overlay. Future panels need LT500 review and radio removal before
publication to the compatible channel; new kernel dependencies need firmware.

CI checks all 57 generated panel payloads, firmware-owned package protections,
update/rollback, official plugin signatures and dependencies under MIPS emulation
on RC4 userspace before compilation. Final checks cover image metadata and size,
all kernel-module ABIs, TUN/AWG/UDP symbols, package versions and standalone IPKs
using the image's own opkg. Published assets are downloaded and hash-verified.
RC5 still needs on-router acceptance for boot, LTE, VLESS and WARP.
See [RC5 installation instructions](docs/LT500v2-RC5-INSTALL-RU.md).

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
