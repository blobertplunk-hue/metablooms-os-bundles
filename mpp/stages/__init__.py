# ECL:
#   id: MPP.STAGES.INIT
#   role: library
#   owns: [stage contract types shared across all MPP stages]
#   does_not: [execute any stage logic, touch the filesystem directly]
#   inputs: []
#   outputs: [StageResult, Issue, Severity, StageID dataclasses]
#   side_effects: none
#   failure_modes: [import error if dataclasses unavailable]
#   invariants: [all stage results are immutable after construction]
#   evidence: [imported cleanly by mpp_pipeline.py]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


class StageID(str, Enum):
    PRVE       = "S1_PRVE"
    SEE        = "S2_SEE"
    MMD        = "S3_MMD"
    CDR        = "S4_CDR"
    ECL        = "S5_ECL"
    TEST       = "S6_TEST"
    RECURSION  = "S7_GOVERNED_RECURSION"


@dataclass(frozen=True)
class Issue:
    severity:    Severity
    location:    str           # file path or artifact name
    description: str
    remediation: str


@dataclass
class StageResult:
    stage:        StageID
    passed:       bool
    artifacts:    List[str]          = field(default_factory=list)
    issues:       List[Issue]        = field(default_factory=list)
    notes:        str                = ""
    timestamp:    str                = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

    @property
    def blocking_issues(self) -> List[Issue]:
        return [i for i in self.issues if i.severity in (Severity.CRITICAL, Severity.HIGH)]

    def as_dict(self) -> dict:
        return {
            "stage":     self.stage.value,
            "passed":    self.passed,
            "artifacts": self.artifacts,
            "issues":    [{"severity": i.severity.value, "location": i.location,
                           "description": i.description, "remediation": i.remediation}
                          for i in self.issues],
            "notes":     self.notes,
            "timestamp": self.timestamp,
        }
