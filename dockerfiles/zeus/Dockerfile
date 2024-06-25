FROM openjdk:8u212-jdk-alpine3.9

RUN apk update \
  && apk add --no-cache fontconfig ttf-dejavu \
  && rm -rf /var/lib/apt/lists/* \
  && rm /var/cache/apk/*

EXPOSE 8080

ADD app.jar /app.jar

ENTRYPOINT ["sh", "-c", "java -javaagent:/agent/skywalking-agent.jar -Dskywalking.agent.service_name=$HOSTNAME -Dskywalking.collector.backend_service=$SK_IP -jar $JAVA_OPTS /app.jar --spring.cloud.nacos.discovery.ip=$IP --spring.cloud.nacos.discovery.port=$PORT"]
