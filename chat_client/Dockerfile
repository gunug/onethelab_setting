FROM nginx:alpine
COPY chat_client/index.html /usr/share/nginx/html/
COPY chat_client/chat.js /usr/share/nginx/html/
COPY chat_client/config.js /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
