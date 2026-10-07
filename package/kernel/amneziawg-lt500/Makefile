include $(TOPDIR)/rules.mk
include $(INCLUDE_DIR)/kernel.mk

PKG_NAME:=amneziawg-lt500
PKG_VERSION:=2.0.20260725
PKG_RELEASE:=1
PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/amnezia-vpn/amneziawg-linux-kernel-module.git
PKG_SOURCE_VERSION:=ae0924ca700520ca34c5bdbcfd05b2f683ea9353
PKG_SOURCE_DATE:=2026-07-25
PKG_MIRROR_HASH:=skip
PKG_LICENSE:=GPL-2.0
PKG_LICENSE_FILES:=COPYING
PKG_BUILD_PARALLEL:=1

include $(INCLUDE_DIR)/package.mk

define KernelPackage/amneziawg
  SUBMENU:=Network Support
  TITLE:=AmneziaWG 2.0 with I1-I5 support for LT500
  URL:=https://github.com/amnezia-vpn/amneziawg-linux-kernel-module
  DEPENDS:=+kmod-udptunnel4 +kmod-udptunnel6 +kmod-crypto-lib-chacha20poly1305 +kmod-crypto-lib-curve25519
  FILES:=$(PKG_BUILD_DIR)/src/amneziawg.ko
  AUTOLOAD:=$(call AutoLoad,30,amneziawg)
endef

define Build/Compile
	$(KERNEL_MAKE) M="$(PKG_BUILD_DIR)/src" WIREGUARD_VERSION="$(PKG_VERSION)" modules
endef

$(eval $(call KernelPackage,amneziawg))
