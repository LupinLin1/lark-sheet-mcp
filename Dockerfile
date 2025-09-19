# Multi-stage build for Feishu Spreadsheet MCP Server
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1000 mcp && \
    useradd --uid 1000 --gid mcp --shell /bin/bash --create-home mcp

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/mcp/.local

# Make sure scripts in .local are usable
ENV PATH=/home/mcp/.local/bin:$PATH

# Copy application code
COPY feishu_spreadsheet_mcp/ ./feishu_spreadsheet_mcp/
COPY setup.py .
COPY README.md .

# Install the package
RUN pip install --no-cache-dir -e .

# Switch to non-root user
USER mcp

# Expose port for health checks (if needed)
EXPOSE 8000

# Environment variables for configuration
ENV FEISHU_APP_ID=""
ENV FEISHU_APP_SECRET=""
ENV FEISHU_LOG_LEVEL="INFO"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import feishu_spreadsheet_mcp; print('OK')" || exit 1

# Default command
CMD ["feishu-spreadsheet-mcp"]