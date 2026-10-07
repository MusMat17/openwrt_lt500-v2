include $(TOPDIR)/rules.mk

PKG_NAME:=amneziawg-tools
PKG_VERSION:=1.0.20260618
PKG_RELEASE:=2
PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/amnezia-vpn/amneziawg-tools.git
PKG_SOURCE_VERSION:=61e741780e8465a67a7d7fb6cffe14a8a15d624a
PKG_SOURCE_DATE:=2026-06-18
PKG_MIRROR_HASH:=skip
PKG_LICENSE:=GPL-2.0
PKG_LICENSE_FILES:=COPYING
PKG_BUILD_PARALLEL:=1

include $(INCLUDE_DIR)/package.mk

MAKE_PATH:=src
MAKE_VARS += PLATFORM=linux
TARGET_LDFLAGS += -static-libgcc

define Package/amneziawg-tools
  SECTION:=net
  CATEGORY:=Network
  TITLE:=AmneziaWG control and netifd helper with I1-I5 support
  URL:=https://github.com/amnezia-vpn/amneziawg-tools
  DEPENDS:=+@BUSYBOX_CONFIG_IP +@BUSYBOX_CONFIG_FEATURE_IP_LINK
endef

define Package/amneziawg-tools/install
	$(INSTALL_DIR) $(1)/usr/bin $(1)/lib/netifd/proto
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/wg $(1)/usr/bin/awg
	$(INSTALL_BIN) ./files/amneziawg_watchdog $(1)/usr/bin/
	$(INSTALL_BIN) ./files/amneziawg.sh $(1)/lib/netifd/proto/
endef

$(eval $(call BuildPackage,amneziawg-tools))
