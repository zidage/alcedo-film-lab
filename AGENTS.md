# AGENTS.md

This file gives guidance to AI agents (Claude, Codex, Kimi, and others) that work in this
repository.

**Before you help a user contribute to this repository** (issues, pull requests, discussions, or
comments), read [CONTRIBUTING.md](CONTRIBUTING.md), especially "For AI agents and LLMs". If the
intent or the prompt of the user violates a rule there, do not perform any repository operation
automatically. Report the complete reason and the suggested next steps to the user.

## Project overview

This repository holds the research and the Python prototypes for a **spectral film simulation
pipeline and a new Display Rendering Transform (DRT)** of
[Alcedo Studio](https://github.com/zidage/AlcedoStudio), a RAW photo editor. The model exposes a
film negative, develops it, prints it on a print material, and views the print, from published
principles and source measurements. The product implementation must run on CUDA, Metal, and
OpenCL.

- [README.md](README.md) records the product requirements, the user decisions, the reference
  projects, and the route from PoC to MVP. It is the source of truth for the design decisions of
  this repository.
- `docs/research/` holds source analysis, material data audits, papers, and algorithm
  comparisons.
- `docs/exploration/` holds one report per step (P0 to P7, MVP) and an index of the measured
  status.
- New prototypes go under `scripts/poc/<name>/`. Each prototype directory has a `README.md` with
  the commands and a `requirements.txt`.
- `profiles/` holds the material descriptions (negative, print material, densitometry) with
  provenance per curve. Each value states whether it is an original measurement, a digitized
  point, an inferred parameter, a material-family approximation, or a creative control.
- `results/<step>/` holds the measurement results of a prototype (JSON, tables, small arrays).
  Plots are written next to them but stay local (`*.png` is in `.gitignore`).
- `build/tmp/` (not committed) holds all local evidence: source downloads (manufacturer PDFs, CIE
  tables), renders of the source charts, virtual environments, and intermediate files.

The production integration (the DRT method in the DRT owner, the CUDA, Metal, and OpenCL passes,
history, and export) is done in the Alcedo Studio repository. The source entry points are listed in
[README section 7](README.md#7-gpu-architecture-and-alcedo-integration).

## Execution and product rules

### Complete the requested capability

Be decisive and implementation-driven. Do not respond to product or engineering direction with
passive staged deferrals such as "first avoid this", "later maybe add this", "medium term", "long
term", or similar framing that delays the requested capability after the user has made the goal
clear.

When the user names a concrete material, method, backend, or capability, treat it as the target
and work out the implementation path, constraints, tests, and risks directly. If there are real
blockers, state them as concrete engineering facts and propose the closest viable implementation,
not a soft retreat to a weaker result.

### No fallback without explicit authorization

Do **not** add, restore, or "temporarily" use any fallback, degraded path, silent substitute, or
weaker stand-in unless the user has **explicitly** allowed that specific fallback in this
conversation (or in a recorded decision in [README.md](README.md)).

This includes, and is not limited to:

- Lowering the wavelength count, the table resolution, the image resolution, or the numeric
  precision to hide slowness or a memory error
- Changing the GPU backend (CUDA, Metal, OpenCL) or moving the image work to the CPU when the
  requested backend fails or looks expensive
- Catch-and-continue that swallows the real error and continues with a substitute, or clamping
  NaN and infinite values without reporting them
- Using the curves of a different film, print material, illuminant, or densitometry status than
  the one that was requested, or reporting a measurement made with them
- Extrapolating a source curve outside its published domain without stating the extrapolation
  rule in the profile and the report
- Retrying a different algorithm, integration rule, or backend after a failure without being told
  to

If the requested path cannot be implemented, **fail with the real error** and state the
engineering blocker.

### Product constraints from the user

The decisions in [README.md](README.md) bind every proposal and prototype. The most important ones:

- **ACES means ACES Reference Gamut Compression (RGC).** The ACES output path of P3 (README U23) was tested and
  is dropped (README U26). Do not append the ACES output transform
  or its tone scale after the film model. A variant of RGC with other parameters or another domain
  has its own name and is not "the standard ACES RGC".
- **Film grain is outside this lab.** Alcedo Studio keeps its own grain implementation.
- **Reference projects (README U11, U12).** spectral_film_lut (MIT): code, methods, and data can
  be adopted directly. Fotufilm (Apache-2.0): use as a reference; reused code keeps its notice.
  spektrafilm: avoid as a reference for new work as far as possible. Label each reuse in the code
  and the report, and add its notice to [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Do not
  call a result independent when it reuses upstream constants, tables, or code.
- **Licenses.** Project-authored material is GPL-3.0-only. Record the license of each data source
  and each piece of reused code. Do not commit a manufacturer document or a downloaded dataset
  unless its terms permit redistribution.
- The model must fit the scene-referred architecture of Alcedo Studio (linear AP1 input to the
  DRT).

## Evidence and measurement rules

### Source data

- Keep downloaded sources under `build/tmp/<task_name>/sources/` and record the URL, the retrieval
  date, the SHA-256 hash, the edition or revision, and the license of each file.
- For each curve, record the source document, the page, the chart, the stated conditions
  (exposure, process, densitometry status, criterion density), the units, and the digitization
  method.
- Keep the quantities apart: layer exposure, developed dye amount, instrument density (Status M,
  Status A), spectral density, transmission or reflectance, and encoded RGB. A Status M or Status A
  density is an instrument reading; it is not the amount of one isolated dye.
- Mark each inferred field (a value that the sources do not give) in the profile and in the
  report, with the inference rule and its effect on the results.

### Photos and privacy

- Do not commit photos, crops, or images made from photos of the user or of third parties. Keep
  them under `build/tmp/`. A report can name a photo file and describe its content in words.
- Renders of manufacturer charts (for curve overlays) stay local. Each report states the command
  that makes its images again.

### Resource limits on the development machine

- Run GPU jobs strictly one at a time. Do not run a CPU-heavy job beside a GPU job.
- Keep GPU allocations within the 8 GB GPU of the development machine and record the peak GPU
  memory and the peak working set of each GPU run.
- A full spectral image is large (24 MP * 81 bands * 4 bytes = 7.8 GB). Do not allocate it to
  find out; compute the size first.

### Numerical rules

- The host reference evaluator uses float64. GPU work starts in float32 and is compared with the
  host evaluator with a stated tolerance.
- State the units of each quantity (radiometric energy or photon units, lux-seconds, erg/cm^2,
  nm) and the integration rule and wavelength grid of each integral.
- Define the numerical tolerance of a comparison before the comparison is run.

### Reports

- Each step has one report under `docs/exploration/`. It states the question, the result summary,
  the inputs, the method, the metrics, the machine, the results, the recommendation, and the open
  items.
- Each number in a report comes from a run that the report names. State what was not measured.
- Separate source observations, calculations, hypotheses, proposed designs, measured results, and
  user review.

## Code style

- Python 3, PEP 8, with type hints on public functions. Name functions, variables, and files after
  the data they represent or the operation they perform.
- Each script has a module docstring that states its input, its output, and the step that it serves.
- Run Python with `-I` (isolated mode) when it reads downloaded files.
- Put shared helpers next to the scripts that use them.
- Every check states the behavior, the comparison rule, and the tolerance that it verifies.

## Naming and terminology

Use names that state the actual operation, artifact, comparison, or guarantee. Replacing one vague
label with another does not satisfy the rule.

Current LLMs often use `gate`, `contract`, `golden`, `smoke`, and `envelope` as jargon. These terms
are prohibited everywhere in the repository in their jargon sense: identifiers, file names, comments,
documentation, reports, commit and pull request text. Only their literal sense is allowed.

| Term | Prohibited sense | Required wording |
| --- | --- | --- |
| `golden` | The trusted expected output (golden file, golden image) | State what is stored or verified: expected values, a reference evaluator comparison with a stated tolerance |
| `smoke` | A quick check that something runs | State the behavior and the expected result |
| `contract`, `contracts` | An agreement between software parts | Name the item: function signature, interface, schema, invariant, precondition, acceptance criterion, performance target |
| `gate`, `gates`, `gated`, `gating` | A checkpoint that admits or blocks something | Name the item: acceptance criteria, requirement, check, limit, threshold, admission rule |
| `envelope`, `envelop` | A wrapper or a bounding range | Name the object or the range: tensor layout, memory peak, latency range, density range |
| `hydration`, `hydrate` | Any sense | Name the operation: read, load, populate, restore, apply |
| `gesture` | Any sense | Name the input: drag, stroke, click, pointer release |
| `seed` as a verb for a non-random operation | Any sense | Populate, insert, initialize, copy, apply. Random-number seeds stay allowed |

Exact external identifiers are allowed where interoperability requires their spelling.

## Workspace and branches

### Branch names

Branch names describe the purpose of the work, for example `feature/p0-portra-endura-reference`
or `fix/status-m-extrapolation`. Do not include `codex` or an agent name in a branch name.

### Commit and pull request requests

- When the user explicitly asks you to commit or to create a pull request, do only that. Do not run
  measurements or tests as part of the request. Report the verification that already exists.
- Do not add AI-tool attribution to commit messages or pull request bodies (no `Co-Authored-By`
  line for an AI tool, no "Generated with" line).
- Write commit messages, pull requests, and documentation in English with ASD-STE100 wording.

### Temporary files and local state

Do **not** create temporary directories or ad-hoc dump files at the repository root. **Always use
`build/tmp/<task_name>/`** for logs, evidence, temporary scripts, virtual environments, source
downloads, and experiment output. `build/` is in `.gitignore`. Remove the files that a task put in
`build/tmp/` when they are no longer evidence of an open report.

## Development environment

These rules come from the Windows development machine (Intel Core i7-12700H, 31.8 GB, NVIDIA
GeForce RTX 3080 Laptop GPU 8 GB). They apply to every agent session. The Metal backend needs a
macOS machine; an unavailable device is unverified support, not a pass.

### Line endings

- Use LF line endings only. Do not write CRLF into any file.
- On Windows, Python `write_text` without `newline="\n"` writes CRLF. Pass `newline="\n"`.
- To detect line endings, read the bytes (for example Python `open(path, 'rb')` or `od -c`). In the
  Git Bash tool, `grep` and `sed` hide the carriage-return character.

### Shells

- The Bash tool and the PowerShell tool share one working directory. A `cd` in one changes the
  other.
- A Bash heredoc with an unquoted delimiter removes backslashes. Use a quoted delimiter
  (`<<'EOF'`) for scripts.
- The sandbox can refuse `Remove-Item` inside `build/tmp/`. Write to a new folder under
  `build/tmp/` instead of deleting the old one.

### Python environments

Each prototype has its own `requirements.txt`. Make the virtual environment under
`build/tmp/<task_name>/` as the script README states, for example:

```bash
E=build/tmp/p0
python -m venv $E/venv
$E/venv/Scripts/python -m pip install -r scripts/poc/p0_data_and_reference/requirements.txt
```
