FROM python:3.11-slim AS builder
ARG VERSION=0.01-dev1
WORKDIR /workdir

# Don't run as root.
RUN useradd --create-home user
RUN chown -R user:user /workdir
USER user
ENV PATH /home/user/.local/bin:$PATH
COPY --chown=user:user . /workdir/
RUN sed -i "s|0.01-dev1|$VERSION|g" src/alertmanagermeshtastic/__init__.py
RUN python3 -m pip install --upgrade build && python3 -m build

RUN find

FROM python:3.11-slim

WORKDIR /app

# Don't run as root.
RUN useradd --create-home user
RUN usermod -a -G dialout user
USER user
ENV PATH /home/user/.local/bin:$PATH

COPY --chown=user:user --from=builder /workdir/dist/alertmanagermeshtastic*.whl /app/

RUN pip install alertmanagermeshtastic*.whl

EXPOSE 9119

CMD ["alertmanagermeshtastic", "config.toml"]
