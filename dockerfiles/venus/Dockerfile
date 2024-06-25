FROM nginx:stable-alpine

RUN rm -f /etc/nginx/conf.d/default.conf \
  && rm -rf /usr/share/nginx/html/*

ADD dist /usr/share/nginx/html
ADD web.conf /etc/nginx/conf.d/web.conf

EXPOSE 80 443

ENTRYPOINT ["sh", "-c", "nginx -g 'daemon off;'"]