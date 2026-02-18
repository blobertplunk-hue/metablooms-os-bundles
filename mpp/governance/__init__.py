# ECL:
#   id: GVN.PACKAGE.INIT
#   role: library
#   owns: [governance layer package identity]
#   does_not: [execute governance logic on import]
#   inputs: []
#   outputs: [__version__]
#   side_effects: none
#   failure_modes: [import error if sub-modules are missing]
#   invariants: [version tracks MPP version it wraps]
#   evidence: [importable as 'import mpp.governance']
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18

__version__ = "1.0.0"
__all__ = ["gov_pipeline"]
