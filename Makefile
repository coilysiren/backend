DEFAULT_GOAL := help
.PHONY: deploy

# Put static variables up here.
# These would be nice inside of a config file or something.
dns-zone ?= coilysiren.me
dns-name ?= api.coilysiren.me
email ?= coilysiren@gmail.com

# Everything at the top level runs every time you do anything.
# So only put fast commands up here.
hash ?= $(shell git rev-parse --short HEAD)
name ?= $(shell git config --get remote.origin.url | sed -E 's/^.*:(.*)\..*$$/\1/')
name-dashed ?= $(subst /,-,$(name))

help:
	@awk '/^## / \
		{ if (c) {print c}; c=substr($$0, 4); next } \
			c && /(^[[:alpha:]][[:alnum:]_-]+:)/ \
		{printf "%-30s %s\n", $$1, c; c=0} \
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

.build-docker:
	docker build \
		--progress plain \
		--build-arg BUILDKIT_INLINE_CACHE=1 \
		--cache-from $(name):latest \
		-t $(name):$(hash) \
		-t $(name):latest \
		.

## build project inside of a docker container
#  see also: build-native
build-docker: .build .build-docker

.publish:
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

## publish the docker image to the registry
publish: build-docker .publish

## login to the platforms necessary to deploy the application
login:
	gcloud auth application-default login
	gcloud config set project coilysiren-deploy
	pulumi login
	pulumi stack select build

## deploy the infrastructure required to operate and host this repository, should only be run by humans
deploy-infra:
	pulumi config set aws:region us-west-2
	pulumi config set gcp:project coilysiren-deploy
	pulumi config set gcp:region us-west2
	pulumi config set dns-zone $(dns-zone)
	pulumi config set dns-name $(dns-name)
	pulumi up --yes

## deploy the cert secrets utilized by the application
deploy-secrets-cert:
	$(eval cluster := $(shell gcloud container clusters list --filter='name:coilysiren-deploy*' --format='value(name)'))
	gcloud container clusters get-credentials $(cluster) \
			--region us-west2-a
	env \
		NAME=$(name-dashed) \
		envsubst < deploy/secrets-cert.yaml | kubectl apply -f -

## deploy the BSKY_USERNAME and BSKY_PASSWORD secrets
deploy-secrets-bsky:
	$(eval cluster := $(shell gcloud container clusters list --filter='name:coilysiren-deploy*' --format='value(name)'))
	gcloud container clusters get-credentials $(cluster) \
			--region us-west2-a
	kubectl create secret generic "$(name-dashed)"-bsky \
		--namespace="$(name-dashed)" \
		--from-literal=BSKY_USERNAME="$(shell gcloud secrets versions access latest --secret=bsky-username)" \
		--from-literal=BSKY_PASSWORD="$(shell gcloud secrets versions access latest --secret=bsky-password)" \
		--dry-run=client -o yaml | kubectl apply -f -

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
