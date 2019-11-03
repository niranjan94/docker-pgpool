FROM python:3 AS builder

RUN pip install cx_Freeze

WORKDIR /build
COPY initialize.py .
RUN cxfreeze initialize.py

#
#
#

FROM centos:8

ENV PG_POOL_VERSION=4.1

RUN yum install https://www.pgpool.net/yum/rpms/${PG_POOL_VERSION}/redhat/rhel-8Server-x86_64/pgpool-II-release-${PG_POOL_VERSION}-1.noarch.rpm -y && \
    yum install pgpool-II-pg11 pgpool-II-pg11-debuginfo -y && \
    yum clean all && \
    rm -rf /var/cache/yum && \
    mkdir -p /var/run/pgpool /var/log/pgpool && \
    chmod -R +rw /var/run/pgpool /var/log/pgpool

EXPOSE 9999
EXPOSE 9000

WORKDIR /staging
COPY conf conf
COPY --from=builder /build/dist .
COPY docker-entrypoint.sh /usr/local/bin
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["pgpool", "-n", "-D", "-f", "/opt/config.ini", "-m", "fast"]
