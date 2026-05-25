FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update     && apt-get install -y --no-install-recommends         bash         build-essential         ca-certificates         curl         git         git-lfs         gnupg         jq         openssh-client         python3         unzip         xz-utils     && rm -rf /var/lib/apt/lists/*

RUN mkdir -p -m 755 /etc/apt/keyrings     && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg         -o /etc/apt/keyrings/githubcli-archive-keyring.gpg     && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg     && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main"         > /etc/apt/sources.list.d/github-cli.list     && apt-get update     && apt-get install -y --no-install-recommends gh     && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash -     && apt-get update     && apt-get install -y --no-install-recommends nodejs     && corepack enable     && corepack prepare pnpm@latest --activate     && rm -rf /var/lib/apt/lists/*

ENV BUN_INSTALL="/usr/local/bun"
RUN mkdir -p "${BUN_INSTALL}" \
    && curl -fsSL https://bun.sh/install | bash

ENV PATH="${BUN_INSTALL}/bin:${PATH}"
ENV DEV_REPOS_ROOT="/workspace"
ENV DEV_REPOS_GIT_PROTOCOL="ssh"

WORKDIR /opt/cursor-dev-environment

COPY config ./config
COPY scripts ./scripts

RUN chmod +x ./scripts/dev-repos     && ln -s /opt/cursor-dev-environment/scripts/dev-repos /usr/local/bin/dev-repos     && git lfs install --system

CMD ["bash"]
