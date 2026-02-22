"""
Backend Guards Package

Contains deployment and runtime guards for data integrity.
"""

from guards.deployment_guard import validate_deployment, DeploymentGuardError

__all__ = [
    "validate_deployment",
    "DeploymentGuardError",
]
