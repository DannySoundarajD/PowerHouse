# Sentinel Sandbox Image - Node.js
# Minimal Node.js environment for sandboxed JavaScript execution

FROM node:18-slim

# Install common packages
RUN npm install -g \
    lodash \
    axios \
    moment

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash sandbox

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER sandbox

# Default command
CMD ["node", "--version"]
