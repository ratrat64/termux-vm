FROM tvm-eval-dhlrhsji:foundation
USER root
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       openvpn git curl iproute2 iptables dnsutils tcpdump python3 ca-certificates openssl \
    && groupadd --system nm-openvpn \
    && useradd --system --gid nm-openvpn --no-create-home --shell /usr/sbin/nologin nm-openvpn \
    && rm -rf /var/lib/apt/lists/*
USER 1001:1001
