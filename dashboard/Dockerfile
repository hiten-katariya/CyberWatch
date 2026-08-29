FROM node:22-alpine

WORKDIR /app

COPY dashboard/package.json ./
RUN npm install

COPY dashboard/ .

EXPOSE 3000

CMD ["npm", "run", "dev"]
