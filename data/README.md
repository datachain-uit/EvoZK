# Data

All tables are UTF-8, comma- (`.csv`) or tab-separated (`.tsv`). Times are in milliseconds. A *cell* is one circuit
on one backend; cell names follow `circuits/README.md`. Backends: `groth16`, `plonk`, `fflonk` (snarkjs) and
`rapidsnark` (Groth16 with the native prover).

## rq1_proving/

Proving campaign of RQ1 (Section 6.3 of the paper and Section S5 of its Supplementary Material). The measurement
blocks are C (confirmatory claims), X (crossover sizes), B1, B23 and B4 (replications and setups), HASH (hash
families) and L (lifecycle cells on PLONK and FFLONK).

| File | Content |
|---|---|
| `cells.csv` | Per-cell median proving time over all measured samples, with the 95 % interval of its logarithm |
| `contrasts.csv` | Pre-specified contrasts: ratio of two cells, `theta` = ln ratio with 90 % and 95 % intervals, precision gate and outcome class (Rule 1) |
| `crossover_contrasts.csv`, `crossover_bracket.csv` | Contrasts of A0-tight against MR across record sizes, and the sizes that bracket the crossover |
| `sensitivity_contrasts.csv` | Replication and sensitivity contrasts (registry depth, MR depth, padding) |
| `hash_family_ratios.csv` | Cost ratios with MiMC and SHA-256 relative to Poseidon |
| `setup.csv` | Circuit-specific setup times per cell and backend |
| `claims.json` | Outcome of each pre-specified claim, per backend |
| `circuit_sizes.tsv` | R1CS constraints, variables, public inputs and evaluation-domain powers of every circuit |
| `lifecycle_cells.csv`, `lifecycle_setup.csv` | Proving and setup times of the lifecycle cells (block L) |
| `iden3_crosscheck.tsv` | Constraint counts of MR against the credential-query circuit deployed by iden3/Privado ID |
| `sizes_O1.tsv`, `sizes_O1_vs_O2.tsv`, `crossover_fits.tsv` | Circuit sizes at circom's default level and the fitted crossover coefficients |

## gas/

On-chain cost on a local EVM node (anvil 1.5.1, Osaka), with keys from the Hermez powers-of-tau file of power 22.

| File | Content |
|---|---|
| `gas_by_cell.tsv` | Deployment and verification gas per cell, with calldata and code size |
| `gas_all_proofs.tsv` | Verification gas of every proof sent |
| `gas_public_inputs_sweep.tsv` | Verification gas and code size as the number of public inputs grows |

## rq2_evolution/

Replay of the published version histories of RQ2 (Section 6.5): Open Badges, HL7 FHIR Observation, UK Open Banking
transactions, xBRL-JSON, GS1 EPCIS and the DataCite control.

| File | Content |
|---|---|
| `versions/<standard>/<version>.json` | Path inventory of one version: every leaf path with its type, array bounds, constraints and source locator |
| `versions/<standard>/sources.json` | The official specifications each inventory was read from |
| `statement_policies/<standard>.json` | Statement fields and their path in each version |
| `renames_epcis.json` | Declared path renames between EPCIS versions |
| `derived_versions.tsv`, `derived_transitions.tsv`, `derived.json` | Encoded size per version and the change of every release |
| `transitions_replay.tsv` | Every release: version labels, size change, path and statement-field changes, regeneration per design |
| `regen_by_history.tsv` | Regeneration counts per history and design |
| `label_breakage.tsv` | Version labels against regeneration, per label step and design |
| `readings.tsv` | Regeneration counts under the replay triggers, the data contract and the B = 4 sensitivity |

## analyser_tests/

| File | Content |
|---|---|
| `synthetic_suite.json` | Synthetic release pairs with the expected output of the impact analyser |
| `real_release_outputs.tsv` | The analyser's output on every real release |
| `real_release_agreement.tsv` | Agreement of these outputs with the replay |

## rq3_llm/

Ingestion experiment of RQ3 (Section 6.7) on synthetic documents in three domains, each under two schema versions.

| File | Content |
|---|---|
| `results.json` | Parameters, confirmatory test per cell (paired counts, McNemar test, effect with interval) and descriptive results |
| `runs/<adapter>_<domain>.json` | Per adapter and domain: outcome counts per error class (E1-E4), stability over repeated runs, latency and mapping changes |
