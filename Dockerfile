# Go bot based on giddygiddyboy's MIT-licensed Mech Royale bot (see LICENSE-giddygiddyboy).
FROM golang:1.26.1-bookworm@sha256:ab3d6955bbc813a0f3fdf220c1d817dd89c0b3f283777db8ece4a32fe7858edd AS build
WORKDIR /src
COPY go.mod main.go brain.go types.go world.go export.go ./
RUN mkdir -p mech cmd/bot && mv brain.go types.go world.go export.go mech/ && mv main.go cmd/bot/ \
 && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags="-s -w" -o /mechbot ./cmd/bot

FROM scratch
COPY --from=build /mechbot /mechbot
USER 65534:65534
ENTRYPOINT ["/mechbot"]
