# users service

HTTP API for user records. Data is kept in memory for the life of the process.

- `POST /v1/users` with `{"name","email"}`
- `GET /v1/users`
- `GET /v1/users/{id}`
- `GET /health/startup`, `GET /health/ready`, `GET /health/live`
- `GET /metrics`

```bash
python3 -m services.users
docker build -f services/users/Dockerfile -t users:dev .
```

Deployment is configured by `deploy/dev/users.yaml`, `deploy/staging/users.yaml`, and
`deploy/production/users.yaml`, using the shared chart at
`platform/helm/standard-microservice`.

The process listens on `PORT` (default 8080), handles SIGTERM by failing readiness and draining, runs as uid 10001, and logs JSON to stdout.
