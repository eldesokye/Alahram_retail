# ========================================================
# Odoo 20 Enterprise - Development Container
# Base: Ubuntu 24.04 LTS (Noble)
# ========================================================
FROM ubuntu:24.04

# Non-interactive frontend and UTF-8 locale
ENV DEBIAN_FRONTEND=noninteractive \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# Prevent daemons from starting automatically during package install
RUN echo '#!/bin/sh\nexit 101' > /usr/sbin/policy-rc.d && chmod +x /usr/sbin/policy-rc.d

# Single optimized layer with bind-mount of deb package
# Avoids duplicating 392MB deb into layers, and cleans all caches immediately
RUN --mount=type=bind,source=odoo_20.0+e.20261003_all/odoo_20.0+e.20261003_all.deb,target=/mnt/pkg/odoo.deb \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        postgresql-client \
        wkhtmltopdf \
    && apt-get install -y --no-install-recommends /mnt/pkg/odoo.deb \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* \
    && rm -f /usr/sbin/policy-rc.d

# Set up runtime directories and ownership for odoo user
RUN mkdir -p /var/lib/odoo /mnt/extra-addons /mnt/enterprise /etc/odoo /var/log/odoo \
    && chown -R odoo:odoo /var/lib/odoo /mnt/extra-addons /mnt/enterprise /etc/odoo /var/log/odoo

# Copy entrypoint script
COPY scripts/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# Mount volumes
VOLUME ["/var/lib/odoo", "/mnt/extra-addons", "/mnt/enterprise"]

# Expose HTTP port
EXPOSE 8069

# Non-root application user
USER odoo

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/bin/odoo", "-c", "/etc/odoo/odoo.conf"]
