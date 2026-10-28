# Deployment values

Each file is a complete values set for one service in one environment.

- `dev`: fast feedback, typically one replica and debug logging.
- `staging`: production-like validation.
- `production`: higher replica counts, HPA and PDB enabled.

Before production:
- replace image registry/project/repository placeholders;
- replace `REPLACE_WITH_GIT_SHA` with an immutable image digest or tag;
- confirm health endpoints and port;
- configure secrets via a secret manager/External Secrets Operator;
- configure ingress/Gateway and TLS only if needed;
- test autoscaling with metrics-server and realistic load;
- review PDB, topology spread, resource sizing, and network policy;
- protect production changes with required reviews.
