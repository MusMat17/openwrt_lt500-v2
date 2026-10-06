include $(TOPDIR)/rules.mk

PKG_NAME:=steer-core
PKG_VERSION:=2.0.3
PKG_RELEASE:=1

PKG_LICENSE:=GPL-3.0-only
PKG_MAINTAINER:=splify2
PKGARCH:=mipsel_24kc

include $(INCLUDE_DIR)/package.mk

define Package/steer-core
  SECTION:=net
  CATEGORY:=Network
  TITLE:=Steer 2.0.3 policy routing core
  URL:=https://github.com/splify2/steer
  DEPENDS:=+nftables +ip-full +conntrack +kmod-nft-queue
  PROVIDES:=steer
  CONFLICTS:=steer libsteer libsteer-wolfssl
endef

define Package/steer-core/description
  Steer policy-routing core built from the pinned upstream 2.0.3 source.
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

$(eval $(call BuildPackage,steer-core))
