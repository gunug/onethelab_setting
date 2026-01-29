FROM nginx:alpine
COPY index.html /usr/share/nginx/html/
COPY chat.js /usr/share/nginx/html/
COPY config.js /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
