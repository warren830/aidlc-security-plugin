# Static sample Dockerfile: base image is the moving `latest` tag and the
# container keeps the default root user. Both are common lint findings for
# container workloads.
FROM node:latest

WORKDIR /app
COPY package.json ./
RUN npm install --production
COPY . .

USER root
EXPOSE 8080
CMD ["node", "server.js"]
