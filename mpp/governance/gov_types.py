# ECL:
#   id: GVN.TYPES
#   role: library
#   owns: [governance type contracts shared across all GVN stages]
#   does_not: [execute governance logic, touch the filesystem]
#   inputs: []
#   outputs: [GovIssue, GovSeverity, GovStageID, GovStageResult dataclasses]
#   side_effects: none
#   failure_modes: [import error if dataclasses unavailable]
#   invariants: [all governance results are immutable after construction]
#   evidence: [imported cleanly by all g*.py modules]
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class GovSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


class GovStageID(str, Enum):
    G0 = "G0_CONTEXT_BRIEF"
    G1 = "G1_ADVERSARIAL_MMD"
    G2 = "G2_BEHAVIOR_REVIEW"
    G3 = "G3_GOVERNOR_LOOP"


@dataclass(frozen=True)
class GovIssue:
    severity:    GovSeverity
    location:    str
    description: str
    remediation: str


@dataclass
class GovStageResult:
    stage:     GovStageID
    passed:    bool
    artifacts: List[str]      = field(default_factory=list)
    issues:    List[GovIssue] = field(default_factory=list)
    notes:     str            = ""
    timestamp: str            = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )

    @property
    def blocking_issues(self) -> List[GovIssue]:
        return [i for i in self.issues if i.severity in (GovSeverity.CRITICAL, GovSeverity.HIGH)]

    def as_dict(self) -> dict:
        return {
            "stage":     self.stage.value,
            "passed":    self.passed,
            "artifacts": self.artifacts,
            "issues":    [
                {"severity": i.severity.value, "location": i.location,
                 "description": i.description, "remediation": i.remediation}
                for i in self.issues
            ],
            "notes":     self.notes,
            "timestamp": self.timestamp,
        }
