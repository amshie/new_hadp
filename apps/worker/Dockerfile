# Worker image (the Redis-backed job loop; a labeled skeleton today — see hadp_worker/main.py).
#
#   docker build -f apps/worker/Dockerfile -t hadp-worker:local .   (build context: repository root)

FROM ghcr.io/astral-sh/uv:0.10.11 AS uv

FROM python:3.12.15-slim-trixie AS deps
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /srv/hadp/apps/worker
COPY apps/worker/pyproject.toml apps/worker/uv.lock ./
# Exactly the locked dependencies, without the dev group. The project itself is not installed:
# its source is copied into the final stage and put on PYTHONPATH.
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12.15-slim-trixie
# The base image's own pip is not used here (the dependencies come from the stage above) and
# is what an image scan reports first: it is taken out of the container's file system.
RUN groupadd --system --gid 10001 hadp \
    && useradd --system --uid 10001 --gid hadp --no-create-home --home-dir /nonexistent \
        --shell /usr/sbin/nologin hadp \
    && rm -rf /usr/local/lib/python3.12/site-packages/pip \
        /usr/local/lib/python3.12/site-packages/pip-*.dist-info \
        /usr/local/lib/python3.12/ensurepip /usr/local/bin/pip*
WORKDIR /srv/hadp/apps/worker
COPY --from=deps /srv/hadp/apps/worker/.venv ./.venv
COPY apps/worker/src ./src
ENV PATH="/srv/hadp/apps/worker/.venv/bin:${PATH}" \
    PYTHONPATH=/srv/hadp/apps/worker/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
# Numeric, so an orchestrator can verify "not root" without reading /etc/passwd.
USER 10001:10001
CMD ["python", "-m", "hadp_worker.main"]
