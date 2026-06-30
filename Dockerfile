FROM python:3.12-slim

# Bring in the uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy the project and install dependencies from the lockfile
COPY . .
RUN uv sync --frozen --no-dev

# Pre-download the local models (Silero VAD + turn detector) so they're baked into the image
RUN uv run agent.py download-files

# Run the agent worker in production mode
CMD ["uv", "run", "agent.py", "start"]
