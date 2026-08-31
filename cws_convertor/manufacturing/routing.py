"""Deterministic, fail-closed machine routing authority."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Mapping

@dataclass(frozen=True,slots=True)
class MachineRouteDecision:
    part_id:str;machine_id:str;eligible:bool;automatic:bool;blocking_codes:tuple[str,...]=();reason:str=""

class MachineRoutingService:
    @staticmethod
    def _value(report:Any,name:str,default:Any=None):return report.get(name,default) if isinstance(report,Mapping) else getattr(report,name,default)
    def route(self,part_id:str,capabilities:Mapping[str,Any],*,preferred_machine:str=""):
        candidates=[]
        for machine_id,report in capabilities.items():
            blockers=tuple(str(value) for value in (self._value(report,"blocking_codes",()) or ()));explicit=self._value(report,"production_ready",None)
            if explicit is None:explicit=self._value(report,"eligible",None)
            if explicit is None:explicit=self._value(report,"passed",None)
            if explicit is not True or blockers:continue
            decisions=self._value(report,"feature_decisions",()) or ();candidates.append((0 if str(machine_id)==str(preferred_machine) else 1,-len(decisions),str(machine_id),blockers))
        if not candidates:return MachineRouteDecision(str(part_id),"",False,False,("CWS.ROUTING.NO_PROVEN_MACHINE",),"Geen machine heeft expliciet bewezen capaciteit")
        _preferred,_score,machine_id,blockers=min(candidates);return MachineRouteDecision(str(part_id),machine_id,True,not bool(preferred_machine),blockers,"Deterministisch gerouteerd op bewezen machinecapaciteit")
    def route_many(self,parts:Mapping[str,Mapping[str,Any]],*,preferred:Mapping[str,str]|None=None):
        choices=preferred or {};return tuple(self.route(part_id,capabilities,preferred_machine=choices.get(part_id,"")) for part_id,capabilities in sorted(parts.items()))

__all__=["MachineRouteDecision","MachineRoutingService"]
