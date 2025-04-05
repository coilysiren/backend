DEFAULT_GOAL := help
.PHONY: deploy

# Put static variables up here.
# These would be nice inside of a config file or something.
dns-zone := coilysiren.me
dns-name := api.coilysiren.me
email := coilysiren@gmail.com

# Everything at the top level runs every time you do anything.
# So only put fast commands up here.
hash := $(shell git rev-parse --short HEAD)
name := $(shell git config --get remote.origin.url | sd '^.*:(.*)\..*' '$$1')
name-dashed := $(subst /,-,$(name))

help:
	@awk '/^## / \
		{ if (c) {print c}; c=substr($$0, 4); next } \
			c && /(^[[:alpha:]][[:alnum:]_-]+:)/ \
		{print $$1, "\t", c; c=0} \
			END { print c }' $(MAKEFILE_LIST)

# rebuild requirements.txt whenever pyproject.toml changes
.build: pyproject.toml
	poetry lock
	poetry self add poetry-plugin-export
	poetry export -f requirements.txt --output requirements.txt --without-hashes
	touch .build

## build project on your plain old machine
#  see also: build-docker
build-native: .build
	poetry config virtualenvs.in-project true
	poetry sync

## build project inside of a docker container
#  see also: build-native
build-docker: .build
	docker build \
		--progress plain \
		-t $(name):$(hash) \
		-t $(name):latest \
		.

## publish the docker image to the registry
publish:
	$(eval repo := $(shell pulumi stack output repo | jq -r .name))
	$(eval account := $(shell pulumi stack output account | jq .email))
	$(eval project := $(shell gcloud config get-value project))
	$(eval image-url := us-west2-docker.pkg.dev/$(project)/$(repo)/$(repo):$(hash))
	docker tag $(name):$(hash) $(image-url)
	gcloud auth print-access-token \
		--impersonate-service-account $(account) | docker login \
		-u oauth2accesstoken \
		--password-stdin https://us-west2-docker.pkg.dev
	docker push $(image-url)

## deploy the infrastructure required to host this repository
deploy-infra:
	pulumi config set DNS_ZONE $(dns-zone)
	pulumi config set DNS_NAME $(dns-name)
	pulumi up

## deploy the cert secrets utilized by the application
deploy-secrets-cert:
	$(eval cluster := $(shell gcloud container clusters list --filter='name:coilysiren-deploy*' --format='value(name)'))
	gcloud container clusters get-credentials $(cluster) \
			--region us-west2-a
	env \
		NAME=$(name-dashed) \
		envsubst < deploy/secrets-cert.yaml | kubectl apply -f -

## deploy the application to the cluster
deploy:
	$(eval repo := $(shell pulumi stack output repo | jq -r .name))
	$(eval ip := $(shell pulumi stack output ip | jq -r .address))
	$(eval project := $(shell gcloud config get-value project))
	$(eval image-url := us-west2-docker.pkg.dev/$(project)/$(repo)/$(repo):$(hash))
	$(eval cluster := $(shell gcloud container clusters list --filter='name:coilysiren-deploy*' --format='value(name)'))
	gcloud container clusters get-credentials $(cluster) \
			--region us-west2-a
	env \
		NAME=$(name-dashed) \
		DNS_NAME=$(dns-name) \
		EMAIL=$(email) \
		IMAGE_URL=$(image-url) \
		IP_ADDRESS=$(ip) \
		envsubst < deploy/main.yaml | kubectl apply -f -

## run project on your plain old machine
#  see also: run-docker
run-native:
	poetry run uvicorn src.main:app --reload --port 4000 --host 0.0.0.0

## run project inside of a docker container
#  see also: run-native
run-docker:
	docker run --expose 4000 -it --rm $(name):latest
