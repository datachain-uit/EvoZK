# EvoZK

EvoZK is a framework that makes schema evolution an input to the design of blockchain zero-knowledge (ZK) verifiers.
Its impact analyser derives, from two versions of a data standard, what each verifier design must regenerate
(circuit, keys and verifier contract). Its design planner prices that choice over a standard's lifecycle and
recommends a design for an expected proof volume.

This repository holds the code of EvoZK and the data behind the results of the paper:

> K. T. Vo and T.-A. Nguyen-Hoang. *EvoZK: A lifecycle-cost framework for zero-knowledge verification of evolving
> data standards on blockchain.* Manuscript under review, 2026.

## Contents

| Folder | What it holds | Paper |
|---|---|---|
| `circuits/` | Circom circuits of the five designs (A0-tight, A0-pad, PX, MR, A1) as measured | Sections 4.4, 5.3, 6.2 |
| `evozk/analyser/` | Impact analyser (Algorithm 1) | Section 5.1 |
| `evozk/planner/` | Design planner and lifecycle model (Algorithm 2) | Section 5.2 |
| `data/rq1_proving/` | Per-cell proving and setup times, contrasts and claim outcomes, circuit sizes | RQ1, Section 7.1 |
| `data/gas/` | Deployment and verification gas per design and backend | Section 7.1 |
| `data/rq2_evolution/` | Path inventories of every standard version, statement policies, replay results | RQ2, Section 7.2 |
| `data/analyser_tests/` | Synthetic test suite of the analyser and its agreement on real releases | Section 7.2 |
| `data/rq3_llm/` | Extraction outcomes of the deterministic and LLM adapters | RQ3, Section 7.3 |

`circuits/README.md` and `data/README.md` describe the files in detail.

## Requirements

The circuits use [circomlib](https://github.com/iden3/circomlib) and were compiled with circom 2 at `--O2`.
The analyser and the planner are Python 3 packages; the lifecycle model also uses NumPy.

## License

Code (`circuits/`, `evozk/`): MIT, see `LICENSE`.
Data (`data/`): CC BY 4.0, see `LICENSE-DATA.md`.
