# MetaBlooms Repo Delta Backup — CLEAN-EXPORT-1

Created: 2026-05-21T01:23:50Z

## Status

- Clean export/cold restore proof: PASS
- Public/external release: NOT performed
- Repo backup type: pointer manifest + checksums + restore instructions
- Large binary upload through connector: not attempted because the available GitHub connector path is not suitable for 151MB/391MB binary artifacts.

## Target repository

`blobertplunk-hue/metablooms-os-bundles`

## Artifacts
- `METABLOOMS_OS_CLEAN_EXPORT_1_FINAL_PATCHED_20260521T010420Z.zip.zst` — 157535864 bytes — SHA-256 `a239bed870a413a9a5a61d2f010d6dff9d0823fd88423dacf87afacf7afa45da`
- `METABLOOMS_OS_CLEAN_EXPORT_1_FINAL_PATCHED_20260521T010420Z.zip.zst.sha256` — 144 bytes — SHA-256 `d7d9cecf7f09851ab1de13ef23e0f55b42aaf23ad35b93e850dc193eb9737209`
- `METABLOOMS_OS_CLEAN_EXPORT_1_FINAL_PATCHED_20260521T010420Z.zip.zst.provenance.json` — 610 bytes — SHA-256 `b323dcaf2e0f0e3fd7641d4a19a43f01826fac837fab7fa09c4684c94db0b3d3`
- `METABLOOMS_OS_CLEAN_EXPORT_1_FINAL_PATCHED_20260521T010420Z.zip` — 409858548 bytes — SHA-256 `4c5bd706a37ec9b1cea528bb8f4d74980731025c73ef1b41718892b587a3c03c`
- `METABLOOMS_OS_CLEAN_EXPORT_1_FINAL_PATCHED_20260521T010420Z.zip.sha256` — 130 bytes — SHA-256 `d20ef9eb6c8719fb6e785d53666fa07c15f357863854b1454157fb6ed70c8106`
- `METABLOOMS_OS_CLEAN_EXPORT_1_FINAL_PATCHED_20260521T010420Z.zip.provenance.json` — 657 bytes — SHA-256 `c18842816288eb599e08c27c7c85c2591102fe248750002a2e4a4500799ddbb2`
- `CLEAN_EXPORT_1_20260521T010420Z_RECEIPTS.zip` — 100839 bytes — SHA-256 `93ece81cf25192430a2b24a1ac16029d9672e6e8bfedf0b0f0b6682ae3e04824`
- `CLEAN_EXPORT_1_20260521T010420Z_RECEIPTS.zip.sha256` — 121 bytes — SHA-256 `58ba804858916c6d5d993859f1b0fa0bc055674a95cbbfcf6b6ba34b4a793baa`
- `CLEAN_EXPORT_1_20260521T010420Z_RECEIPTS.zip.provenance.json` — 353 bytes — SHA-256 `2bdffbd3fd983446463f6fa54e9fbe6b6f35cb97c0514f01846fb3a0ca76820a`

## Restore instructions

1. Download the ZST artifact `METABLOOMS_OS_CLEAN_EXPORT_1_FINAL_PATCHED_20260521T010420Z.zip.zst` and its `.sha256` sidecar.
2. Verify SHA-256 against `SHA256SUMS.txt`.
3. Decompress the ZST to ZIP with `zstd -d -c <file>.zip.zst > restore.zip`.
4. Verify the restored ZIP SHA against the ZIP SHA in this manifest.
5. Extract to staging and run `bash scripts/mpp/mpp.sh turn-boot --task "cold restore repo backup" --operation validate --print-summary` from `Metablooms_OS`.
6. Run sidecar/path gates as in the CLEAN-EXPORT-1 receipt bundle.

## Explicit non-claims

- This repo delta does not prove GitHub-hosted binary availability.
- This repo delta does not claim public release.
- It records exact clean-export hashes and local/ChatGPT artifact availability for restore.
