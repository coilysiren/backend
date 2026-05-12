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

help: ## Print this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "%-30s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# rebuild requirements.txt whenever pyproject.toml changes
.build: pyproject.toml
	uv lock
	uv export --no-hashes --no-dev --no-emit-project --format requirements-txt -o requirements.txt
	touch .build

build-native: .build ## uv lock + uv sync. Rebuilds requirements.txt from pyproject.toml.
	uv sync

.build-docker:
	docker build \
		--progress plain \
		--build-arg BUILDKIT_INLINE_CACHE=1 \
		--cache-from $(name):latest \
		-t $(name):$(git-hash) \
		-t $(name):latest \
		.

build-docker: .build .build-docker ## Build the docker image locally with BuildKit cache.

.publish:
	docker tag $(name):$(git-hash) $(image-url)
	docker push $(image-url)

publish: build-docker .publish ## Tag and push the docker image to ghcr.io.

.deploy:
	env \
		NAME=$(name-dashed) \
		DNS_NAME=$(dns-name) \
		IMAGE=$(image-url) \
		envsubst < deploy/main.yml | kubectl apply -f -
	kubectl rollout status deployment/$(name-dashed)-app -n $(name-dashed) --timeout=5m

deploy: publish .deploy ## Deploy the application to the cluster.

run-native: ## Run the FastAPI server with autoreload on port 4000.
	uv run uvicorn backend.main:app --reload --port 4000 --host 0.0.0.0

run-docker: ## Run the published container locally on port 4000.
	docker run --expose 4000 -p 4000:4000 -it --rm $(name):latest

# Dev/debug CLI targets. Each delegates to `backend.cli`. Pass values as
# variables, e.g. `make bsky-emoji-summary handle=coilysiren.me`.

clear-cache: ## Delete cache keys with the given suffix. Args - suffix=<str>.
	uv run python -m backend.cli clear-cache --suffix $(suffix)

bsky-cli: ## Call a Bluesky XRPC endpoint with caching. Args - path=<str> kwargs=<str>.
	uv run python -m backend.cli bsky-cli --path "$(path)" --kwargs "$(kwargs)"

bsky-get-author-feed-texts: ## Dump an author's feed texts. Args - handle=<str> pages=<int>.
	uv run python -m backend.cli bsky-get-author-feed-texts \
		--handle $(handle) --pages $(or $(pages),1)

bsky-emoji-summary: ## Run the emoji-summary NLP job. Args - handle=<str> num_keywords=<int> num_feed_pages=<int>.
	uv run python -m backend.cli bsky-emoji-summary \
		--handle $(handle) \
		--num-keywords $(or $(num_keywords),25) \
		--num-feed-pages $(or $(num_feed_pages),25)

stream-video: ## Stream a local video file in fixed-size chunks. Args - path=<str> chunk_size=<int>.
	uv run python -m backend.cli stream-video \
		--path $(path) --chunk-size $(or $(chunk_size),1)
