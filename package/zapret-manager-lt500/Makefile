include $(TOPDIR)/rules.mk

PKG_NAME:=zapret-manager-lt500
PKG_VERSION:=2.48
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/StressOzz/Zapret-Manager.git
PKG_SOURCE_VERSION:=d528728e0351b9fc2ae72997dfcd9d2c74425b6b
PKG_SOURCE_DATE:=2026-10-06
PKG_MIRROR_HASH:=skip

PKG_LICENSE:=MIT
PKG_MAINTAINER:=LT500 v2 community build

include $(INCLUDE_DIR)/package.mk

define Package/zapret-manager-lt500
  SECTION:=net
  CATEGORY:=Network
  TITLE:=Zapret Manager 2.48 dashboard bootstrap for Cudy LT500v2
  URL:=https://github.com/StressOzz/Zapret-Manager
  DEPENDS:=+luci +curl +unzip +uhttpd-mod-ubus +rpcd +nftables +ip-full +ca-bundle
endef

define Package/zapret-manager-lt500/description
  Pins Zapret Manager 2.48 and installs its Web/LuCI dashboard on first boot.
  The dashboard then manages Zapret, Steer, WARP and AmneziaWG.
endef

define Build/Compile
endef

define Package/zapret-manager-lt500/install
	$(INSTALL_DIR) $(1)/usr/libexec
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/ZapretManager_LuCI.sh $(1)/usr/libexec/zapret-manager-installer
	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./files/zapret-manager-bootstrap $(1)/etc/init.d/zapret-manager-bootstrap
	$(INSTALL_DIR) $(1)/etc
	printf '%s\n' 'LT500v2 v2.0-zapret-rc1 all-in-one' > $(1)/etc/lt500-allinone
endef

$(eval $(call BuildPackage,zapret-manager-lt500))
