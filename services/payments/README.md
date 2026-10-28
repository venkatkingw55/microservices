# payments service

HTTP API that records an in-memory payment authorization. It does not call a payment processor and does not store card or bank details.

- `POST /v1/payments` with `{"orderId","amountCents","currency"}`
- `GET /v1/payments/{id}`
- `GET /health/startup`, `GET /health/ready`, `GET /health/live`
- `GET /metrics`

```bash
python3 -m services.payments
docker build -f services/payments/Dockerfile -t payments:dev .
```

Deployment is configured by `deploy/dev/payments.yaml`, `deploy/staging/payments.yaml`, and
`deploy/production/payments.yaml`, using the shared chart at
`platform/helm/standard-microservice`.

The process listens on `PORT` (default 8080), handles SIGTERM by failing readiness and draining, runs as uid 10001, and logs JSON to stdout.
