# ECL:
#   id: MPP.PACKAGE.INIT
#   role: library
#   owns: [package identity and public API surface]
#   does_not: [execute anything on import]
#   inputs: []
#   outputs: [__version__, __all__]
#   side_effects: none
#   failure_modes: [import error if sub-packages are missing]
#   invariants: [version string is always a valid semver]
#   evidence: [importable as 'import mpp']
#   aesthetic: cdr/AESTHETIC_CONTRACT.json
#   last_reviewed: 2026-02-18

__version__ = "1.0.0"
__all__ = ["mpp_pipeline"]
