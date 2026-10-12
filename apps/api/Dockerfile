# API image. The same image runs the migrate step (Alembic + catalog seeding), so it carries
# alembic.ini and the migrations beside the application.
#
#   docker build -f apps/api/Dockerfile -t hadp-api:local .     (build context: repository root)
#
# The image keeps the repository's layout under /srv/hadp. hadp_api/config.py looks for an
# optional `.env.local` five directories above itself — the repository root in a checkout,
# /srv/hadp here. No such file exists in the image (.dockerignore lets no `.env*` into the build
# context), so configuration comes from the environment alone. A shallower layout would make
# that lookup fail at import.

FROM ghcr.io/astral-sh/uv:0.10.11 AS uv

FROM python:3.12.15-slim-trixie AS deps
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /srv/hadp/apps/api
COPY apps/api/pyproject.toml apps/api/uv.lock ./
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
WORKDIR /srv/hadp/apps/api
COPY --from=deps /srv/hadp/apps/api/.venv ./.venv
COPY apps/api/alembic.ini ./
COPY apps/api/alembic ./alembic
COPY apps/api/src ./src
ENV PATH="/srv/hadp/apps/api/.venv/bin:${PATH}" \
    PYTHONPATH=/srv/hadp/apps/api/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
# Numeric, so an orchestrator can verify "not root" without reading /etc/passwd.
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "hadp_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
