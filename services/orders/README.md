# orders service

Place the application source code, tests, Dockerfile, and service-specific build configuration here.

Deployment is configured by `deploy/dev/orders.yaml`, `deploy/staging/orders.yaml`, and
`deploy/production/orders.yaml`, using the shared chart at
`platform/helm/standard-microservice`.

Ensure the application:
- listens on the configured container port;
- implements the configured startup, readiness, and liveness endpoints, or update the paths;
- handles SIGTERM and graceful shutdown;
- runs as a non-root user and supports a read-only root filesystem, or document a justified override;
- logs to stdout/stderr and exposes application metrics through your chosen monitoring setup.
