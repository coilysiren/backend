DEFAULT_GOAL := help

# Any command that has the same name as a file or folder needs to be marked as phony
.PHONY: deploy

# Everything at the top level runs every time you do anything.
# So only put fast commands up here.

dns-name ?= $(shell cat config.yml | yq e '.dns-name')
email ?= $(shell cat config.yml | yq e '.email')
name ?= $(shell cat config.yml | yq e '.name')
name-dashed ?= $(subst /,-,$(name))
git-hash ?= $(shell git rev-parse HEAD)
image-url ?= ghcr.io/$(name)/$(name-dashed):$(git-hash)

echo:
	echo $(image-url)

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
		-t $(name):$(git-hash) \
		-t $(name):latest \
		.

## build project inside of a docker container
#  see also: build-native
build-docker: .build .build-docker

.publish:
	docker tag $(name):$(git-hash) $(image-url)
	docker push $(image-url)

## publish the docker image to the registry
publish: build-docker .publish

## deploy the namespace for the application
deploy-namespace:
	kubectl create namespace $(name-dashed)

## deploy the cert secrets utilized by the application
deploy-secrets-cert:
	env \
		NAME=$(name-dashed) \
		envsubst < deploy/secrets-cert.yml | kubectl apply -f -

## deploy the docker registry secret utilized by the application
deploy-secrets-docker-repo:
	$(eval github-token := $(shell aws ssm get-parameter --name "/github/pat" --with-decryption --query "Parameter.Value" --output text))
	# test the token
	echo $(github-token) | docker login ghcr.io -u $(name) --password-stdin
	# create the secret
	kubectl create secret docker-registry docker-registry \
		--namespace="$(name-dashed)" \
		--docker-server=ghcr.io/$(name) \
		--docker-username=$(name) \
		--docker-password=$(github-token) \
		--dry-run=client -o yaml | kubectl apply -f -


# deploy-secrets-bsky:
# 	kubectl create secret generic "$(name-dashed)"-bsky \
# 		--namespace="$(name-dashed)" \
# 		--from-literal=BSKY_USERNAME="$(shell gcloud secrets versions access latest --secret=bsky-username)" \
# 		--from-literal=BSKY_PASSWORD="$(shell gcloud secrets versions access latest --secret=bsky-password)" \
# 		--dry-run=client -o yml | kubectl apply -f -

# deploy-secrets-honeycomb:
# \	kubectl create secret generic "$(name-dashed)"-honeycomb \
# 		--namespace="$(name-dashed)" \
# 		--from-literal=HONEYCOMB_API_KEY="$(shell gcloud secrets versions access latest --secret=honeycomb-api-key)" \
# 		--dry-run=client -o yml | kubectl apply -f -

.deploy:
	env \
		NAME=$(name-dashed) \
		DNS_NAME=$(dns-name) \
		IMAGE=$(image-url) \
		envsubst < deploy/main.yml | kubectl apply -f -

## deploy the application to the cluster
deploy: publish .deploy

## run project on your plain old machine
#  see also: run-docker
run-native:
	poetry run uvicorn src.main:app --reload --port 4000 --host 0.0.0.0

## run project inside of a docker container
#  see also: run-native
run-docker:
	docker run --expose 4000 -it --rm $(name):latest
