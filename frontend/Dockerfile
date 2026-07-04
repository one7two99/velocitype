# Frontend builder. Produces the static Vite bundle. In compose this runs at
# container start and writes to the ./frontend/dist bind mount, which Caddy
# serves from /srv. It builds once and exits (a one-shot build service).
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Default: build into /app/dist (bind-mounted to host ./frontend/dist).
CMD ["npm", "run", "build"]
