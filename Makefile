.DEFAULT_GOAL := help

PYTHON ?= .venv/bin/python
NODE ?= node
FOUNDRY_BIN ?= $(HOME)/.foundry/bin
export PATH := $(FOUNDRY_BIN):$(PATH)
FORGE ?= forge
ANVIL ?= anvil

.PHONY: help run test test-wallet contracts-build test-contracts anvil deploy-anvil deploy-ganache

help:
	@printf '%s\n' \
	  'make run              Iniciar Flask' \
	  'make test             Executar pytest' \
	  'make test-wallet      Executar testes da carteira simulada' \
	  'make contracts-build  Compilar contratos com Forge' \
	  'make test-contracts   Executar testes Solidity' \
	  'make anvil            Iniciar Anvil em 127.0.0.1:8545 (Chain ID 31337)' \
	  'make deploy-anvil     Implantar placar no Anvil em execução' \
	  'make deploy-ganache   Implantar placar no Ganache em execução'

run:
	"$(PYTHON)" app.py

test:
	"$(PYTHON)" -m pytest -q

test-wallet:
	"$(NODE)" tests/test_scoreboard_wallet.cjs

contracts-build:
	"$(FORGE)" build --root contracts

test-contracts:
	"$(FORGE)" test --root contracts -vv

anvil:
	"$(ANVIL)" --host 127.0.0.1 --port 8545 --chain-id 31337

deploy-anvil:
	"$(PYTHON)" scripts/deploy_scoreboard.py --network anvil

deploy-ganache:
	"$(PYTHON)" scripts/deploy_scoreboard.py --network ganache
