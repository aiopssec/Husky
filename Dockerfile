FROM python:3.12.4-alpine3.20

RUN apk update \
  && apk add --no-cache tzdata nginx git openssh docker openjdk8 maven nodejs npm make g++ postgresql-dev \
  && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
  && pip install --upgrade pip \
  && pip install Flask psycopg2-binary pyjwt \
  && apk del tzdata \
  && rm -rf /var/lib/apt/lists/* \
  && rm /var/cache/apk/*

WORKDIR /husky
HEALTHCHECK CMD netstat -tlnp | grep 5000 || exit 1
EXPOSE 443

ADD ssl /etc/ssl/husky
ADD ssh /root/.ssh
ADD script /script
ADD nginx.conf /etc/nginx/nginx.conf
ADD default.conf /etc/nginx/conf.d/default.conf
ADD html /usr/share/nginx/html
ADD app.py /app.py
ADD dockerfiles /dockerfiles

RUN chmod +x /script/* \
    && chmod 600 /root/.ssh/*

ENTRYPOINT ["sh", "-c", "nohup python /app.py > /var/log/nginx/app.log 2>&1 & nginx -g 'daemon off;'"]