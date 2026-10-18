# Interfaz compilada y servida por nginx. nginx reenvía /api a la API, de modo
# que el navegador usa un solo origen y el cliente no cambia.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# API_UPSTREAM es la URL https de la API y API_HOST su nombre; los fija la Container App.
ENV API_UPSTREAM=http://127.0.0.1:8000 \
    API_HOST=127.0.0.1
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
