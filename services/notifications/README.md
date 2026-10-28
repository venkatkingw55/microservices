# notifications service

HTTP API that queues notification records in memory. Nothing is sent to an external provider.

- `POST /v1/notifications` with `{"userId","channel","message"}` (`channel` is `email` or `sms`)
- `GET /v1/notifications/{id}`
- `GET /health/startup`, `GET /health/ready`, `GET /health/live`
- `GET /metrics`

```bash
python3 -m services.notifications
docker build -f services/notifications/Dockerfile -t notifications:dev .
```

Deployment is configured by `deploy/dev/notifications.yaml`, `deploy/staging/notifications.yaml`, and
`deploy/production/notifications.yaml`, using the shared chart at
`platform/helm/standard-microservice`.

The process listens on `PORT` (default 8080), handles SIGTERM by failing readiness and draining, runs as uid 10001, and logs JSON to stdout.
