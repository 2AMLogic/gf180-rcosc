# sim/iq - quiescent-current (Iq) sweep

New manifests written by `iq_sweep.py` carry `pdk`, `pdk_revision` (a real
open_pdks commit or `"unknown"` plus `pdk_revision_reason`) and a
root-relative `model_dir`, and no absolute install paths. Schema and
detection rules: [`../README.md`](../README.md) (section "PDK revision
provenance") and [`../pdk_provenance.py`](../pdk_provenance.py).

Historical runs under `results/` predate this field. Their PDK revision is
**unknown** (manifests record family and install path only) and has not been
back-filled; results are append-only evidence.
