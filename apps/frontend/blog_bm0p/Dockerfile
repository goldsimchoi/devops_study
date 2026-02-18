FROM node:20-alpine

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

COPY . .

RUN chown -R node:node /app
USER node

EXPOSE 4321

CMD ["pnpm", "dev", "--host", "0.0.0.0", "--port", "4321"]
