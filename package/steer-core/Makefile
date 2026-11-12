include $(TOPDIR)/rules.mk

PKG_NAME:=steer-core
PKG_VERSION:=2.1.3
PKG_RELEASE:=1

PKG_LICENSE:=GPL-3.0-only
PKG_MAINTAINER:=splify2
PKGARCH:=mipsel_24kc

include $(INCLUDE_DIR)/package.mk

define Package/steer-core
  SECTION:=net
  CATEGORY:=Network
  TITLE:=Steer 2.1.3 policy routing core
  URL:=https://github.com/splify2/steer
  DEPENDS:=+nftables +ip-full +conntrack +kmod-nft-queue +kmod-tun
  PROVIDES:=steer libsteer libsteer-wolfssl steer-vless steer-hysteria2 steer-proxy steer-xsteer steer-obfs steer-warpbox steer-tgws steer-extended
  CONFLICTS:=steer libsteer libsteer-wolfssl steer-vless steer-hysteria2 steer-proxy steer-xsteer steer-obfs steer-warpbox steer-tgws steer-extended
endef

define Package/steer-core/description
  Steer policy-routing core from the hash-pinned official 2.1.3 package.
  Includes the matching trusted keys and signed offline protocol seed.
  Used by Zapret Manager to route selected services through WARP/AWG interfaces.
endef

define Build/Compile
endef

define Package/steer-core/conffiles
/etc/steer/
endef

define Package/steer-core/install
	[ -d ./files/usr ] || { echo "steer-core payload was not staged by CI" >&2; exit 1; }
	$(CP) ./files/* $(1)/
endef

define Package/steer-core/postinst
#!/bin/sh
[ -n "$$IPKG_INSTROOT" ] && exit 0
/etc/init.d/steer enable
/etc/init.d/steer restart
endef

$(eval $(call BuildPackage,steer-core))
