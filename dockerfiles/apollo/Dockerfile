FROM openjdk:8u212-jdk-alpine3.9

RUN apk update \
  && apk add --no-cache fontconfig ttf-dejavu \
  && rm -rf /var/lib/apt/lists/* \
  && rm /var/cache/apk/*

ADD app.jar /app.jar

ENTRYPOINT ["sh", "-c", "java -jar $JAVA_OPTS /app.jar"]
