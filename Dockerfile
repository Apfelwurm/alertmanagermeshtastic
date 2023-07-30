FROM python:3.9-slim

WORKDIR /app

# Don't run as root.
RUN useradd --create-home user
USER user
ENV PATH /home/user/.local/bin:$PATH

RUN pip install --no-cache-dir alertmanagermeshtastic==0.01-dev

EXPOSE 8080

CMD ["alertmanagermeshtastic", "config.toml"]
