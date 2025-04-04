hash := $(shell git rev-parse --short HEAD)
name := $(shell git config --get remote.origin.url | sd '^.*:(.*)\..*' '$$1')

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

## run project on your plain old machine
#  see also: run-docker
run-native:
	poetry run uvicorn src.main:app --reload --port 4000 --host 0.0.0.0

## run project inside of a docker container
#  see also: run-native
run-docker:
	docker run --expose 4000 -it --rm $(name):latest
