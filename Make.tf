TERRAFORM := docker run
TERRAFORM += --interactive
TERRAFORM += --rm
TERRAFORM += --tty
TERRAFORM += --env AWS_PROFILE=$(AWS_PROFILE)
TERRAFORM += --volume $(HOME)/.aws/credentials:/root/.aws/credentials:ro
TERRAFORM += --volume $(PWD)/terraform:/terraform
TERRAFORM += --workdir /terraform
TERRAFORM += hashicorp/terraform

.PHONY: apply
apply: pull
	$(TERRAFORM) apply .plan.tf

.PHONY: fmt
fmt:
	$(TERRAFORM) fmt

.PHONY: destroy
destroy:
	$(TERRAFORM) plan -destroy -out=.plan.tf
	$(TERRAFORM) apply -destroy .plan.tf

.PHONY: get
get: pull
	$(TERRAFORM) get -update

.PHONY: init
init: pull
	$(TERRAFORM) init -reconfigure

.PHONY: plan
plan: pull get
	$(TERRAFORM) plan -out=.plan.tf

.PHONY: pull
pull:
	docker pull hashicorp/terraform
