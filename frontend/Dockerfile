# The website: Next.js, built once and run as a small standalone server.
FROM node:24-slim AS build
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# Where /api requests are passed on to. It is fixed when the site is built.
ARG API_URL=http://api:8453
ENV API_URL=$API_URL NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

FROM node:24-slim
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
