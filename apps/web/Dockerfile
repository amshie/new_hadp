# Web image (Next.js, `next start`).
#
#   docker build -f apps/web/Dockerfile -t hadp-web:local .     (build context: repository root)
#
# next.config.mjs is used as it is (no `output: "standalone"`), so the runtime stage carries the
# production dependencies and the `.next` build output, laid out as in the workspace.

FROM node:22.23.3-trixie-slim AS workspace
# pnpm comes from corepack in the version package.json names (`packageManager`).
ENV CI=true \
    COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    NEXT_TELEMETRY_DISABLED=1
RUN corepack enable
WORKDIR /srv/hadp
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/
COPY packages/api-client/package.json packages/api-client/
COPY packages/config/package.json packages/config/

FROM workspace AS build
RUN pnpm install --frozen-lockfile
COPY packages packages
COPY apps/web apps/web
# The typed API client is generated here from the committed openapi.json (offline); the
# generated file is not in the build context.
RUN pnpm gen:client \
    && pnpm --filter @hadp/web build \
    && rm -rf apps/web/.next/cache

FROM workspace AS prod-deps
# What `next start` needs, and no more. Optional dependencies are left out: in this workspace
# they are next's compiler binaries (used by `next build` only; pnpm installs both libc
# variants, ~260 MB) and sharp (image optimization — the app uses no next/image; an app that
# does must drop `--no-optional`).
RUN pnpm install --frozen-lockfile --prod --no-optional

FROM node:22.23.3-trixie-slim
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1
# `next start` needs node and nothing else of the base image. npm, corepack and yarn — with
# their own dependency trees, which is where an image scan finds its HIGH findings — are taken
# out of the container's file system. (They remain in the base image's layer underneath.)
RUN rm -rf /usr/local/lib/node_modules /opt/yarn-* \
        /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
        /usr/local/bin/yarn /usr/local/bin/yarnpkg
WORKDIR /srv/hadp/apps/web
# pnpm links apps/web/node_modules into the store at /srv/hadp/node_modules/.pnpm with relative
# symlinks, so both trees keep their workspace paths.
COPY --from=prod-deps /srv/hadp/node_modules /srv/hadp/node_modules
COPY --from=prod-deps /srv/hadp/apps/web/node_modules ./node_modules
COPY --from=build /srv/hadp/apps/web/.next ./.next
COPY apps/web/package.json apps/web/next.config.mjs ./
# The image's `node` user, by number, so an orchestrator can verify "not root".
USER 1000:1000
EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start", "-p", "3000"]
