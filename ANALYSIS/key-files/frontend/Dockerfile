# Frontend builder. Produces the static Vite bundle. In compose this runs at
# container start and writes to the ./frontend/dist bind mount, which Caddy
# serves from /srv. It builds once and exits (a one-shot build service).
#
# Runs as the image's non-root `node` user (uid 1000) so the files written into
# the bind-mounted dist are owned by the typical host user, not root.
FROM node:22-alpine

WORKDIR /app
RUN chown node:node /app
USER node

COPY --chown=node:node package.json package-lock.json* ./
RUN npm install

COPY --chown=node:node . .

# Default: build into /app/dist (bind-mounted to host ./frontend/dist).
CMD ["npm", "run", "build"]
