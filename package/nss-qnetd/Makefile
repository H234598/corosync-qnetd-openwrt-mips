include $(TOPDIR)/rules.mk

PKG_NAME:=nss-qnetd
PKG_VERSION:=3.112
PKG_RELEASE:=1
PKG_SOURCE:=nss-$(PKG_VERSION).tar.gz
PKG_SOURCE_URL:=https://download.cdn.mozilla.net/pub/security/nss/releases/NSS_$(subst .,_,$(PKG_VERSION))_RTM/src https://archive.mozilla.org/pub/security/nss/releases/NSS_$(subst .,_,$(PKG_VERSION))_RTM/src
PKG_HASH:=33ae72d43b275957252adc8639e84229d3ae692a57b6191b059d9456b8568a68
PKG_BUILD_DIR:=$(BUILD_DIR)/nss-qnetd-$(PKG_VERSION)
PKG_UNPACK:=mkdir -p $(PKG_BUILD_DIR); $(STAGING_DIR_HOST)/bin/libdeflate-gzip -dc $(DL_DIR)/$(PKG_SOURCE) | tar -C $(PKG_BUILD_DIR) --strip-components=1 -xf -
PKG_BUILD_DEPENDS:=nspr
PKG_LICENSE:=MPL-2.0
PKG_LICENSE_FILES:=nss/COPYING

include $(INCLUDE_DIR)/package.mk

define Package/libnss-qnetd
  SECTION:=libs
  CATEGORY:=Libraries
  TITLE:=Minimal Mozilla NSS build dependency for corosync-qnetd
  DEPENDS:=+nspr
endef

define Build/Configure
endef

define Build/Compile
	echo >> $(PKG_BUILD_DIR)/nss/cmd/manifest.mn
	echo 'SOFTOKEN_SRCDIRS =' >> $(PKG_BUILD_DIR)/nss/cmd/manifest.mn
	echo 'NSS_SRCDIRS = lib' >> $(PKG_BUILD_DIR)/nss/cmd/manifest.mn
	$(MAKE) $(PKG_JOBS) -C $(PKG_BUILD_DIR)/nss/coreconf/nsinstall CC="$(HOSTCC)" CPU_ARCH=x86_64 USE_64=1 OBJDIR_NAME=host BUILD_OPT=1
	mkdir -p $(PKG_BUILD_DIR)/dist/target.OBJ/include $(PKG_BUILD_DIR)/dist/public/nspr $(PKG_BUILD_DIR)/dist/target.OBJ/lib
	cp -fpRL $(STAGING_DIR)/usr/include/nspr/. $(PKG_BUILD_DIR)/dist/target.OBJ/include/
	cp -fpRL $(STAGING_DIR)/usr/include/nspr/. $(PKG_BUILD_DIR)/dist/public/nspr/
	cp -fpL $(STAGING_DIR)/usr/lib/libnspr4.so $(PKG_BUILD_DIR)/dist/target.OBJ/lib/
	cp -fpL $(STAGING_DIR)/usr/lib/libplc4.so $(PKG_BUILD_DIR)/dist/target.OBJ/lib/
	cp -fpL $(STAGING_DIR)/usr/lib/libplds4.so $(PKG_BUILD_DIR)/dist/target.OBJ/lib/
	$(MAKE) $(PKG_JOBS) -C $(PKG_BUILD_DIR)/nss \
		BUILD_OPT=1 CROSS_COMPILE=1 NATIVE_CC="$(HOSTCC)" \
		OS_TARGET=Linux OS_ARCH=Linux OS_TEST=mips CPU_ARCH=mips KERNEL=Linux \
		OBJDIR_NAME=target.OBJ FREEBL_LOWHASH=1 FREEBL_NO_DEPEND=1 NSS_USE_64=0 \
		NSINSTALL="$(PKG_BUILD_DIR)/nss/coreconf/nsinstall/host/nsinstall" \
		CC="$(TARGET_CC)" CCC="$(TARGET_CXX)" AR="$(TARGET_CROSS)ar" RANLIB="$(TARGET_CROSS)ranlib" RC= \
		NSS_DISABLE_DBM=1 NSS_DISABLE_LIBPKIX=1 NSS_DISABLE_GTESTS=1 USE_SYSTEM_NSPR=1 \
		NSPR_INCLUDE_DIR="$(PKG_BUILD_DIR)/dist/target.OBJ/include" NSPR_LIB_DIR="$(PKG_BUILD_DIR)/dist/target.OBJ/lib" \
		OS_REL_CFLAGS="" ARCHFLAG="" DSO_LDOPTS="-shared" LDFLAGS="$(TARGET_LDFLAGS) -L$(STAGING_DIR)/usr/lib" NSS_ENABLE_TESTS=0 \
		XCFLAGS="$(filter-out -Wl%,$(TARGET_CFLAGS)) $(TARGET_CPPFLAGS) -I$(STAGING_DIR)/usr/include -I$(STAGING_DIR)/usr/include/nspr -I$(PKG_BUILD_DIR)/dist/public/nspr -D_GNU_SOURCE -fno-lto -Wno-error" \
		DANGEROUS_CRT_PATH_OK=1
endef

define Build/InstallDev
	$(INSTALL_DIR) $(1)/usr/include/nss-qnetd $(1)/usr/lib/nss-qnetd
	cp -fpRL $(PKG_BUILD_DIR)/dist/public/nss/. $(1)/usr/include/nss-qnetd/
	cp -fpL $(PKG_BUILD_DIR)/dist/target.OBJ/lib/libnss3.so $(1)/usr/lib/nss-qnetd/
	cp -fpL $(PKG_BUILD_DIR)/dist/target.OBJ/lib/libssl3.so $(1)/usr/lib/nss-qnetd/
	cp -fpL $(PKG_BUILD_DIR)/dist/target.OBJ/lib/libsmime3.so $(1)/usr/lib/nss-qnetd/
	cp -fpL $(PKG_BUILD_DIR)/dist/target.OBJ/lib/libnssutil3.so $(1)/usr/lib/nss-qnetd/
	cp -fpL $(PKG_BUILD_DIR)/dist/target.OBJ/lib/libsoftokn3.so $(1)/usr/lib/nss-qnetd/
	cp -fpL $(PKG_BUILD_DIR)/dist/target.OBJ/lib/libfreebl3.so $(1)/usr/lib/nss-qnetd/
endef

define Package/libnss-qnetd/install
	true
endef

$(eval $(call BuildPackage,libnss-qnetd))
