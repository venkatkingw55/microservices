# orders service

HTTP API for order records. Data is kept in memory for the life of the process.

- `POST /v1/orders` with `{"userId","sku","quantity"}`
- `GET /v1/orders`
- `GET /v1/orders/{id}`
- `GET /health/startup`, `GET /health/ready`, `GET /health/live`
- `GET /metrics`

```bash
python3 -m services.orders
docker build -f services/orders/Dockerfile -t orders:dev .
```

Deployment is configured by `deploy/dev/orders.yaml`, `deploy/staging/orders.yaml`, and
`deploy/production/orders.yaml`, using the shared chart at
`platform/helm/standard-microservice`.

The process listens on `PORT` (default 8080), handles SIGTERM by failing readiness and draining, runs as uid 10001, and logs JSON to stdout.
