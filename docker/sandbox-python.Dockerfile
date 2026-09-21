# Sentinel Sandbox Image - Python
# Minimal Python environment for sandboxed code execution

FROM python:3.11-slim

# Install common data science libraries
RUN pip install --no-cache-dir \
    numpy \
    pandas \
    matplotlib \
    requests

# Create non-root user for execution
RUN useradd -m -u 1000 -s /bin/bash sandbox

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER sandbox

# Default command (will be overridden)
CMD ["python", "--version"]
