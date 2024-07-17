FROM python:3.12-slim AS builder
ARG VERSION=0.01-dev1
WORKDIR /workdir

RUN useradd --create-home user
RUN chown -R user:user /workdir
USER user
ENV PATH /home/user/.local/bin:$PATH
COPY --chown=user:user . /workdir/
RUN sed -i "s|0.01-dev1|$VERSION|g" src/alertmanagermeshtastic/__init__.py
RUN python3 -m pip install --upgrade build && python3 -m build


FROM python:3.12-slim

WORKDIR /app

# Don't run as root.
RUN useradd --create-home user
RUN usermod -a -G dialout user
USER user
ENV PATH /home/user/.local/bin:$PATH
ENV SOCAT_ENABLE=FALSE
ENV SOCAT_CONNECTION=""

COPY --chown=user:user --from=builder /workdir/dist/alertmanagermeshtastic*.whl /app/

RUN pip install alertmanagermeshtastic*.whl
USER root
COPY /docker_dist/docker_runscript.sh /app/runscript.sh
COPY /docker_dist/socat_runscript.sh /app/socat_runscript.sh
COPY /docker_dist/supervisord.conf /app/supervisord.conf
COPY /docker_dist/supervisord_socat.conf /app/supervisord_socat.conf
RUN chmod +x /app/runscript.sh
RUN pip install toml-cli
RUN apt-get update && apt-get install -y \
    supervisor  \
    socat  \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

EXPOSE 9119

CMD ["/app/runscript.sh"]
