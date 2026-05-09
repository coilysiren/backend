DEFAULT_GOAL := help

.PHONY: deploy

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
	uv lock
	uv export --no-hashes --no-dev --no-emit-project --format requirements-txt -o requirements.txt
	touch .build

## build project on your plain old machine
#  see also: build-docker
build-native: .build
	uv sync

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

.deploy:
	env \
		NAME=$(name-dashed) \
		DNS_NAME=$(dns-name) \
		IMAGE=$(image-url) \
		envsubst < deploy/main.yml | kubectl apply -f -
	kubectl rollout status deployment/$(name-dashed)-app -n $(name-dashed) --timeout=5m

## deploy the application to the cluster
deploy: publish .deploy

## run project on your plain old machine
#  see also: run-docker
run-native:
	uv run uvicorn backend.main:app --reload --port 4000 --host 0.0.0.0

## run project inside of a docker container
#  see also: run-native
run-docker:
	docker run --expose 4000 -p 4000:4000 -it --rm $(name):latest

# Dev/debug CLI targets. Each delegates to `backend.cli`. The leading
# `--` separates make-target args from the subcommand args. Pass values
# as variables, e.g. `make bsky-emoji-summary handle=coilysiren.me`.

## clear cache keys with the given suffix
#  vars: suffix (required)
clear-cache:
	uv run python -m backend.cli clear-cache --suffix $(suffix)

## call a bluesky xrpc endpoint with caching
#  vars: path (required), kwargs (optional, space-separated key value pairs)
bsky-cli:
	uv run python -m backend.cli bsky-cli --path "$(path)" --kwargs "$(kwargs)"

## dump an author's feed texts
#  vars: handle (required), pages (default 1)
bsky-get-author-feed-texts:
	uv run python -m backend.cli bsky-get-author-feed-texts \
		--handle $(handle) --pages $(or $(pages),1)

## run the emoji-summary nlp job for a handle
#  vars: handle (required), num_keywords (default 25), num_feed_pages (default 25)
bsky-emoji-summary:
	uv run python -m backend.cli bsky-emoji-summary \
		--handle $(handle) \
		--num-keywords $(or $(num_keywords),25) \
		--num-feed-pages $(or $(num_feed_pages),25)

## stream a local video file in fixed-size chunks
#  vars: path (required), chunk_size (default 1, in KB)
stream-video:
	uv run python -m backend.cli stream-video \
		--path $(path) --chunk-size $(or $(chunk_size),1)
