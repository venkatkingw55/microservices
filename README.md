
# Company Platform — Production-Oriented Helm Microservices Example

This repository is a reference implementation for deploying multiple backend microservices with one reusable Helm chart.

It includes:
- One shared `standard-microservice` chart.
- Separate configuration for `users`, `orders`, `payments`, and `notifications`.
- `dev`, `staging`, and `production` values.
- Deployment, Service, optional Ingress, HPA, PDB, ServiceAccount, NetworkPolicy, ConfigMap, and optional PVC templates.
- Values schema validation, chart tests, lint/render commands, and deployment examples.
- GitHub Actions example for chart validation.
- Argo CD ApplicationSet example for GitOps.
- Bitbucket Pipelines example for direct Helm delivery.

## Important production notes

This is a strong starter/reference, not a substitute for organization-specific security review and testing.

1. Replace all example image registries, domains, and image tags with your actual values.
2. Use immutable image tags (for example, a Git SHA) in staging/production. Avoid `latest`.
3. Do not put passwords, API tokens, private keys, or other secrets in Helm values or Git. Use Google Secret Manager + External Secrets Operator, a secrets CSI driver, or another approved secret manager.
4. NetworkPolicy enforcement requires a CNI/plugin that supports NetworkPolicy.
5. HPA requires metrics-server or an equivalent metrics API. CPU-based HPA requires CPU requests.
6. PDBs protect against some voluntary disruptions; they do not guarantee availability during all failures.
7. Ingress requires a compatible Ingress controller. For new GKE deployments, evaluate Gateway API/GKE Gateway where appropriate.
8. Configure TLS, workload identity, image scanning/signing, RBAC, admission policy, monitoring, alerting, and backup/recovery according to your platform standards.
9. Review the default security context and resource settings against the actual application. Some applications need writable paths or additional capabilities; do not weaken security without a reason.
10. The chart intentionally does not create Kubernetes Secret objects from arbitrary values.

## Repository layout

```text
company-platform/
├── services/
│   ├── platformhttp/          # shared HTTP server, health, JSON logs
│   ├── users/
│   ├── orders/
│   ├── payments/
│   └── notifications/
├── platform/
│   └── helm/
│       └── standard-microservice/
│           ├── Chart.yaml
│           ├── values.yaml
│           ├── values.schema.json
│           ├── templates/
│           └── tests/
├── deploy/
│   ├── dev/
│   ├── staging/
│   └── production/
├── argocd/
├── .github/workflows/
├── bitbucket-pipelines.yml
└── Makefile
```

## Application services

`users`, `orders`, `payments`, and `notifications` are small Python services. They listen on port 8080, serve `/health/startup`, `/health/ready`, and `/health/live`, log JSON to stdout, and drain on SIGTERM. Records stay in memory for the life of the process.

```bash
python3 -m unittest discover -s services -t . -p 'test_*.py'
python3 -m services.users
```

Build an image from the repository root, for example:

```bash
docker build -f services/users/Dockerfile -t users:dev .
```

The image runs as uid/gid 10001 and does not write to the filesystem, matching the chart security context.

## Prerequisites

- Helm 3
- kubectl
- A Kubernetes cluster/context for deployment
- Container images already built and pushed to a registry
- Optional: `kind` or `minikube` for local tests

## Validate the chart locally

From repository root:

```bash
helm lint platform/helm/standard-microservice \
  -f deploy/dev/users.yaml

helm template users platform/helm/standard-microservice \
  --namespace users-dev \
  -f deploy/dev/users.yaml

helm template payments platform/helm/standard-microservice \
  --namespace payments-prod \
  -f deploy/production/payments.yaml \
  --set-string image.tag=REPLACE_WITH_GIT_SHA

```

Render all services/environments and inspect the output before applying changes.

## Install or upgrade a release

```bash
helm upgrade --install users platform/helm/standard-microservice \
  --namespace users-dev \
  --create-namespace \
  -f deploy/dev/users.yaml \
  --wait \
  --timeout 5m
```

Production example:

```bash
helm upgrade --install payments platform/helm/standard-microservice \
  --namespace payments-prod \
  --create-namespace \
  -f deploy/production/payments.yaml \
  --set-string image.tag="$GIT_SHA" \
  --wait \
  --timeout 10m
```

Use a release and namespace convention that matches your organization. This example uses one namespace per service/environment to demonstrate isolation; many companies instead use one namespace per environment or domain/team. Neither is universally correct.

## Rollout checks and troubleshooting

```bash
helm status payments -n payments-prod
helm history payments -n payments-prod
kubectl get deploy,rs,pods,svc -n payments-prod
kubectl rollout status deployment/payments -n payments-prod
kubectl describe deployment payments -n payments-prod
kubectl logs deployment/payments -n payments-prod --all-containers=true
```

Rollback to a known Helm revision after reviewing history:

```bash
helm history payments -n payments-prod
helm rollback payments 3 -n payments-prod --wait --timeout 10m
```

Rollback is not a substitute for backward-compatible database migrations or external side-effect recovery. Verify the application and data state after rollback.

## Environment configuration

Values files are complete per service/environment so each release can be deployed independently. Example:

```bash
helm upgrade --install users platform/helm/standard-microservice \
  -n users-prod --create-namespace \
  -f deploy/production/users.yaml \
  --set-string image.tag="$GIT_SHA" \
  --wait --timeout 10m
```

For stronger separation, keep production deployment permissions and production values in a protected GitOps repository with review gates.

## GitOps

`argocd/applicationset.yaml` is a template showing one Application per service/environment directory. Adapt the generator and repository URL to your actual Git repository. Do not apply it until the repository URL, destination cluster, namespace policy, and sync policy have been reviewed.

## CI examples

- `.github/workflows/helm-validate.yml` validates chart syntax and renders all values files.
- `.github/workflows/services.yml` runs the service unit tests and builds each image. It does not push images.
- `bitbucket-pipelines.yml` is an example of direct Helm delivery. It intentionally leaves cloud authentication and production approvals to your secured pipeline configuration.
- Do not store long-lived kubeconfigs or cloud keys as plain repository variables. Prefer OIDC/workload identity or your organization’s approved short-lived credentials flow.

## Chart upgrade policy

- Pin chart versions in GitOps.
- Test every chart change with representative services.
- Roll out chart changes to dev, then staging, then production.
- Treat a shared chart change as a platform change that can affect all consuming services.
