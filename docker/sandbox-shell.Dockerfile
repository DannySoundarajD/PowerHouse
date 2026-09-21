# Sentinel Sandbox Image - Shell/Bash
# Minimal shell environment for sandboxed script execution

FROM ubuntu:22.04

# Install basic utilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    bash \
    coreutils \
    grep \
    sed \
    awk \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash sandbox

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER sandbox

# Default command
CMD ["bash", "--version"]
