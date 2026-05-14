# Dockerfile — Frontend (Nginx)
# Sert le fichier index.html via Nginx sur le port 80

FROM nginx:alpine

# Copier le fichier HTML dans nginx
COPY index.html /usr/share/nginx/html/index.html

# Config nginx minimale pour SPA / single file
RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { try_files $uri $uri/ /index.html; } \
    add_header Access-Control-Allow-Origin *; \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80