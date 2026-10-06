# Cudy LT500v2 (R25) — OpenWrt 23.05.5

This branch is intentionally based on OpenWrt commit:

`10cc5fcd00c648b1a3b4043734c49c18f294041f`

which matches the OpenWrt 23.05.5 revision currently installed by Cudy's
official intermediary firmware (`r24106-10cc5fcd00`).

## v2.0-zapret-rc1 All-in-One

The `v2.0-zapret-rc1` branch adds the bypass stack directly to the firmware while
keeping the proven OpenWrt 23.05.5 / Linux 5.15.167 LT500 hardware base.

Included in the image:

- `curl` and `unzip`
- Zapret Manager 2.48 dashboard, pinned to commit
  `d528728e0351b9fc2ae72997dfcd9d2c74425b6b`
- Zapret 72.20260307 built from source inside this OpenWrt 23.05.5 build
- `kmod-nft-queue`, `kmod-nft-nat`, `kmod-nft-offload`
- Steer Core 2.0.3 for `mipsel_24kc`, pinned to commit
  `81a78be4c26f1a8369a92813fbfbf13f225382ab`
- AmneziaWG kernel module, tools and LuCI protocol built together with the
  firmware from commit `56bf9fed93df48d2b747edd6e7a7c5fbe2b01afe`
- WARP/AWG management through Zapret Manager and Steer

Zapret Manager creates the WARP interfaces (`zmwarp`, `zmwarp2`,
`zmwarp3`, or a custom `zmwarp4`) and Steer routes selected services
through those interfaces. The base Steer core is sufficient for WARP/AWG
interface routing, so optional VLESS/Hysteria/proxy modules are deliberately
not embedded to conserve the LT500's 16 MiB flash.

### ABI safety

Zapret and AmneziaWG are firmware-owned components in this build. Zapret
Manager is patched so that it cannot replace them with externally downloaded
packages. In particular, an external `kmod-amneziawg` must never replace
the module compiled for this exact kernel ABI.

Update these components by installing a newer LT500 firmware release, not by
installing foreign kernel packages.

The Zapret Manager dashboard itself is pinned to version 2.48 for this release
so a dashboard self-update cannot silently remove these LT500-specific safety
guards. Lists, strategies, WARP keys and normal runtime configuration remain
updatable.

### Build validation

CI refuses to publish the artifact unless:

- the sysupgrade image fits the 15872 KiB firmware partition;
- the manifest contains Zapret, NFQUEUE, AmneziaWG, Steer, curl/unzip and the
  Zapret Manager bootstrap;
- the built root filesystem contains `nfqws`, `awg`, `steer` and the
  dashboard installer.

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
