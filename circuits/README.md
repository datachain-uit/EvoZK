# Circuits

Every file is one circuit as measured in the paper. All circuits prove membership of a leaf in the issuer's
registry along a Merkle path, and a circuit with a statement also proves a range predicate on one field.

| Prefix | Design | Parameter | Statement | Public inputs |
|---|---|---|---|---|
| `A0_K<k>_d<d>` | A0-tight / A0-pad | `k` encoded slots | membership (S1) | `root` |
| `A1_d<d>` | A1 (opaque commitment) | none | membership (S1) | `root` |
| `S_A0_K<k>_range1` | A0-tight / A0-pad | `k` encoded slots | range predicate (S3) | `root`, `t` |
| `S_PX_m<m>_range1` | PX | `m` statement-field slots | range predicate (S3) | `root`, `t` |
| `S_MR_h<h>_range1` | MR | sparse Merkle tree depth `h` | range predicate (S3) on a queried key | `root`, `t`, `key` |
| `H_<hash>_<design><param>_d11` | the design with Poseidon, MiMC or SHA-256 hashing | as above | S3 (A0, PX, MR), S1 (A1) | as above |

`d` is the registry depth: 6, 11 or 16 for the membership circuits, and 11 for the statement circuits unless the name ends in `_d6` or `_d16`. A0-pad is the A0 circuit at a padded capacity `k`, so both
schema-bound designs share the `A0` files. The circuits include circomlib from `../node_modules/circomlib/`.
