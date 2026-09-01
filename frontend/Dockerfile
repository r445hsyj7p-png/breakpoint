FROM node:22-alpine AS base
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

# Lokale Entwicklung (infra/docker-compose.yml, target: dev) — Vite-Dev-Server
# mit Hot-Reload gegen bind-gemountete Quellen.
FROM base AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

# Produktions-Build der statischen Assets (infra/docker-compose.prod.yml).
FROM base AS build
COPY . .
RUN npm run build

# Produktions-Image: nginx liefert die gebauten Assets aus und reverse-proxied
# /api/ an den Backend-Service — kein Node-Runtime-Overhead, kein Dev-Server im
# produktiven Betrieb (siehe docs/projektauftrag.md Abschnitt 10h).
FROM nginx:1.27-alpine AS production
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
