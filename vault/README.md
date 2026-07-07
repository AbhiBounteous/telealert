# TeleAlert Vault Secrets Management

## Vault Setup
Version: 2.0.3
Mode: Dev server + Kubernetes deployment
Address: http://127.0.0.1:8200

## Secrets Structure
telealert/database:
  host, name, user, password

telealert/api:
  anthropic_api_key, slack_webhook

## Policy: telealert-app
  Read access to telealert/database
  Read access to telealert/api

## Kubernetes
Vault deployed to namespace: vault
Agent injector: running
Token TTL: 24h
