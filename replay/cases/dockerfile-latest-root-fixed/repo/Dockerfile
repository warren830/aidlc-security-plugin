# Fixed version: the base image is pinned to a specific major/minor tag and
# the runtime user is a dedicated non-root account. Same application
# surface, but the image build is reproducible and a runtime compromise
# drops to a low-privilege user instead of root.
FROM node:22.11.0-bookworm-slim

WORKDIR /app
COPY package.json ./
RUN npm install --production --ignore-scripts
COPY . .

RUN useradd --system --uid 10001 --home /app appuser && chown -R appuser /app
USER appuser
EXPOSE 8080
CMD ["node", "server.js"]
