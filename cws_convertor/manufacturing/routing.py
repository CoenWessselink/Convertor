"""Compatibility route for the dependency-light machine routing authority."""
from cws_convertor.machine_routing import (
    MachineAssignment,
    MachineRouteDecision,
    MachineRoutingService,
    MachineRoutingSnapshot,
    ROUTING_SCHEMA_VERSION,
)

__all__ = [
    "MachineAssignment",
    "MachineRouteDecision",
    "MachineRoutingService",
    "MachineRoutingSnapshot",
    "ROUTING_SCHEMA_VERSION",
]
