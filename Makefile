CHART := platform/helm/standard-microservice
SERVICES := users orders payments notifications
ENVS := dev staging production

.PHONY: lint render validate
lint:
	@for svc in $(SERVICES); do \
	  for env in $(ENVS); do \
	    echo "Linting $$svc / $$env"; \
	    helm lint $(CHART) -f deploy/$$env/$$svc.yaml || exit 1; \
	  done; \
	done

render:
	helm template users $(CHART) -n users-dev -f deploy/dev/users.yaml

validate: lint
	@for svc in $(SERVICES); do \
	  for env in $(ENVS); do \
	    echo "Rendering $$svc / $$env"; \
	    helm template $$svc $(CHART) -n $$svc-$$env -f deploy/$$env/$$svc.yaml >/dev/null || exit 1; \
	  done; \
	done
