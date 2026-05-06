FROM bluenviron/mediamtx:1 AS mediamtx

FROM alpine:3.20

RUN apk add --no-cache ca-certificates curl

COPY --from=mediamtx /mediamtx /mediamtx
COPY --from=mediamtx /mediamtx.yml /mediamtx.yml

EXPOSE 8554 8888 9997

ENTRYPOINT ["/mediamtx"]
