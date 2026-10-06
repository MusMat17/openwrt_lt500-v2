# Cudy LT500 v2 (R25) — OpenWrt 23.05.5 test port

This branch is intentionally based on OpenWrt commit:

`10cc5fcd00c648b1a3b4043734c49c18f294041f`

which matches the OpenWrt 23.05.5 revision currently installed by Cudy's
official intermediary firmware (`r24106-10cc5fcd00`).

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

The draft upstream PR assumes QMI/ModemManager for LTE. The actual LT500 v2
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
and kernel ABI. Mixing them with this custom LT500 v2 image can break kernel
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

## First test image

The first image intentionally does **not** automate modem AT initialization.
It includes `chat` so modem initialization can be verified interactively
before making it persistent.

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
