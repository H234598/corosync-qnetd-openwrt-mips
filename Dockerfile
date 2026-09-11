FROM ubuntu:22.04

ARG SDK_VERSION=25.12.5
ARG SDK_SHA256=bc4307ae2065c0c0b7c84627356e9f3d368a5a803c81552fcb77aa034a843f5a

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    autoconf automake bison build-essential ca-certificates clang file flex g++ gawk \
    gettext git libncurses-dev libssl-dev libtool patchelf pkg-config python3 python3-distutils rsync \
    unzip wget zlib1g-dev zstd \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

RUN wget -O sdk.tar.zst "https://downloads.openwrt.org/releases/${SDK_VERSION}/targets/ath79/generic/openwrt-sdk-${SDK_VERSION}-ath79-generic_gcc-14.3.0_musl.Linux-x86_64.tar.zst" \
 && echo "${SDK_SHA256}  sdk.tar.zst" | sha256sum -c - \
 && tar --use-compress-program=unzstd -xf sdk.tar.zst \
 && rm sdk.tar.zst \
 && mv openwrt-sdk-* sdk

WORKDIR /opt/sdk

COPY build.sh /build/build.sh
CMD ["/bin/bash", "/build/build.sh"]
