FROM nginx:alpine

# nginx 설정 파일 복사
COPY chat_client/nginx.conf /etc/nginx/templates/default.conf.template

# 정적 파일 복사
COPY chat_client/index.html /usr/share/nginx/html/
COPY chat_client/chat.js /usr/share/nginx/html/
COPY chat_client/config.js /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
