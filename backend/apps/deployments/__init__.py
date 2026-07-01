"""
KAVAN v6.0 — Deployments App
============================================================
Layer 6: Deployment & Provisioning Engine

Handles the full lifecycle of product deployment operations:
  - Provisioning new product instances for tenants
  - Upgrading existing deployments to new versions
  - Health monitoring of running deployments
  - Decommissioning cancelled subscriptions

This layer is the bridge between the Marketplace (Layer 5)
and the underlying infrastructure (Docker/K8s).
"""
