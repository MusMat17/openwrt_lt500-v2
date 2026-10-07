include $(TOPDIR)/rules.mk

PKG_NAME:=steer-modules
PKG_VERSION:=2.0.3
PKG_RELEASE:=1
PKG_LICENSE:=GPL-3.0-only
PKG_MAINTAINER:=splify2
PKGARCH:=mipsel_24kc

include $(INCLUDE_DIR)/package.mk

define Build/Compile
endef

define SteerModule
  define Package/steer-$(1)
    SECTION:=net
    CATEGORY:=Network
    TITLE:=Steer $(1) module
    URL:=https://github.com/splify2/steer
    DEPENDS:=+steer-core $(2)
    EXTRA_DEPENDS:=steer-core (=2.0.3-1)
  endef
  define Package/steer-$(1)/install
	[ -x ./files/$(1)/usr/sbin/steer-$(1) ] || { echo "Missing staged Steer $(1)" >&2; exit 1; }
	$$(CP) ./files/$(1)/* $$(1)/
  endef
  $$(eval $$(call BuildPackage,steer-$(1)))
endef

$(eval $(call SteerModule,vless,+kmod-tun))
$(eval $(call SteerModule,hysteria2,+kmod-tun))
$(eval $(call SteerModule,proxy,+kmod-tun))
$(eval $(call SteerModule,xsteer,+kmod-tun))
$(eval $(call SteerModule,obfs))
$(eval $(call SteerModule,tgws))
