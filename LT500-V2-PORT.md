# Cudy LT500v2 (R25) — OpenWrt 23.05.5

This branch is intentionally based on OpenWrt commit:

`10cc5fcd00c648b1a3b4043734c49c18f294041f`

which matches the OpenWrt 23.05.5 revision currently installed by Cudy's
official intermediary firmware (`r24106-10cc5fcd00`).

## v2.0-zapret-rc2 All-in-One

RC2 retains the OpenWrt 23.05.5 / Linux 5.15.167 LT500 hardware base and
integrates the two add-ons confirmed on the router on 2026-10-07.

Included:

- LTE CDC-ECM, LuCI, curl, unzip and opkg upgrade guard.
- Zapret 72.20260307 from pinned source feed.
- Zapret Manager 2.48-2, upstream revision
  `d528728e0351b9fc2ae72997dfcd9d2c74425b6b`, with LT500 component guards.
- Steer Core 2.0.3 and all six modules: VLESS, Hysteria2, Proxy, XSteer,
  Obfs and TGWS. Built together from
  `81a78be4c26f1a8369a92813fbfbf13f225382ab`.
- TUN built against the RC2 kernel ABI, not imported from the RC1 archive.
- AmneziaWG 2.0 kernel source
  `ae0924ca700520ca34c5bdbcfd05b2f683ea9353` and tools source
  `61e741780e8465a67a7d7fb6cffe14a8a15d624a`, matching the tested I1 add-on.
- Netifd and LuCI fields for I1-I5, S3/S4 and range-capable H1-H4.
- Correct OpenWrt 23.05.5 release metadata and available runtime feeds.

### Independent panel updates

`zapret-manager-lt500` is a kernel-independent IPK. Its post-install hook
applies the packaged, patched installer using `/usr/libexec/lt500-panel-apply`.
The dashboard's update action uses `/usr/libexec/lt500-panel-update`, which
reads the reviewed `lt500-panel-stable` release channel in this repository.
It validates board, capability, version, fixed asset name and SHA256, then
installs only the panel package with ordinary opkg dependency checks. It
never fetches an original upstream panel installer for LT500 self-update.
The pinned upstream revision remains reviewed explicitly for each future
panel package. Features requiring a newer kernel need new firmware.

The apply helper keeps one private compressed backup, retains settings,
restores the prior dashboard/settings on installation failure, and supports
manual rollback while preserving current tunnel settings. Manual rollback
pins the prior dashboard until a different installer is installed or the
rollback marker is removed. Panel updates require 2300 KiB free overlay.
A checksum marker skips repeated installation. The enabled bootstrap and
uci-defaults migration also replace a preserved RC1 dashboard after upgrade.
RC2 registers Steer/AWG/panel state in `lib/upgrade/keep.d`; the RC2 release
instructions register the same paths before upgrading from RC1.

Zapret and kernel-owned AmneziaWG remain protected against panel package
replacement/removal. Panel-only updates retain those protections. The
original RC1 self-update URL pin alone was insufficient; use a reviewed
LT500 package or newer firmware.

### Validation

Hardware acceptance: the RC1 standalone TUN/VLESS package and the matching
AmneziaWG I1 fix have both been confirmed working by the user. The combined
RC2 image needs a separate on-router acceptance test after installation.

CI checks panel settings retention, installation idempotence, immediate
failure recovery, manual rollback and board rejection before compilation.
Publication also requires the full package manifest, all six Steer binary
payloads, TUN/AWG/UDP modules, exact kernel dependency for every kmod,
correct board/version metadata, available runtime feeds, and an image below
the 15872 KiB firmware partition limit. All packages build from pinned
sources; foreign RC1 kmods are not reused in RC2.

RC1 kernel package was `5.15.167-1-78d6c8e3a2943133b1f113a51ed060f5`.
Its standalone TUN needed a distinct version because opkg merges matching
local/feed name-version-architecture candidates and could otherwise inherit
the official ABI `81d2030506bf6ad3027d9c549b1e93da`. RC2 resolves this by
building TUN and its kernel together. Never install RC1 add-on kmods on RC2.

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
