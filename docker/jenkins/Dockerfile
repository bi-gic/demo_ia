FROM jenkins/jenkins:lts

USER root

ENV ACCEPT_EULA=Y

RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    apt-transport-https \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

RUN . /etc/os-release \
    && curl -sSL -O https://packages.microsoft.com/config/debian/${VERSION_ID}/packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER jenkins