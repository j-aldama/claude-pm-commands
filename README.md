# claude-pm-commands

Claude Code custom commands and skills for project management, QA automation, test generation, audited planning, end-to-end implementation, and UI design review.

Turn quotes and specs into structured backlogs, validate PRDs against your board, audit scope coverage, generate acceptance test protocols and manual test cases, auto-generate backend + frontend tests, get plans approved by an independent judge, implement them with tests that are seen failing, and review interfaces — all from the terminal.

> The commands and their outputs are written in Mexican Spanish.

## Commands

### `/cotizacion-to-backlog`

Converts quote documents (PDFs, images, markdown) into a fully structured backlog in Plane.

**What it does:**
- Reads all documents from a `cotizaciones/` folder
- Extracts features, integrations, and deliverables
- Creates Epics and Work Items in Plane with hierarchy
- Assigns labels, modules, priorities, and Fibonacci story points
- Generates a `backlog-resumen.md` report
- Verifies estimate points match after creation

**Usage:**
```
/cotizacion-to-backlog My Project Name
```

### `/audit-scope`

Gap analysis between specification documents and actual codebase.

**What it does:**
- Reads specs (PDFs, diagrams, markdown) from a folder
- Scans the entire codebase systematically
- Maps each spec item to code: Implemented / Partial / Not Started / Ambiguous
- Detects scope creep (code not in spec)
- Generates an `audit-scope.md` report with coverage metrics

**Usage:**
```
/audit-scope cotizaciones
```

### `/validar-prd`

Validates a `prd.json` file against existing Plane issues.

**What it does:**
- Compares each user story in the PRD against Plane issues
- Matches by title (exact/partial) or ID
- Reports: matches, missing in Plane, only in Plane
- Interactively creates missing issues with proper fields
- Maps domains to labels and modules automatically

**Usage:**
```
/validar-prd My Project Name
```

### `/acceptance-checklist`

Generates a comprehensive acceptance testing protocol from codebase analysis.

**What it does:**
- Reads project documentation (CLAUDE.md, README, PRD)
- Scans all endpoints, services, models, and existing tests
- Classifies what's covered by automated tests vs needs manual testing
- Generates a checklist with checkboxes, prerequisites, concrete test data, negative tests
- Produces a `protocolo-pruebas-aceptacion.md` ready for manual QA execution

**Usage:**
```
/acceptance-checklist
/acceptance-checklist QA/pruebas-v2.md
```

### `/checklist-cliente`

Generates a clean, professional acceptance testing checklist for client delivery — ready to print as PDF and sign.

**What it does:**
- Looks for an existing technical protocol (`docs/protocolo-pruebas-aceptacion.md` or `docs/checklist.md`)
- If found, transforms it by removing all technical sections (API routes, Docker, Redis, test results, E2E logs)
- If not found, generates a checklist from scratch by analyzing the codebase
- Simplifies technical jargon to client-friendly language
- Adds signature fields and observation spaces formatted for print
- Generates a PDF via `md-to-pdf`

**Usage:**
```
/checklist-cliente
/checklist-cliente docs/entrega-v2.md
```


### `/e2e-gen`

Generates automated tests for a feature, covering backend (pytest + httpx) and frontend (Playwright). Auto-detects the project stack and follows existing conventions.

**What it does:**
- Auto-detects backend (FastAPI/Django/Express) and frontend (Next/Astro/HTML) stack
- Identifies relevant endpoints, components, and services for the feature
- Plans coverage prioritizing error paths, validation, auth, and edge cases over happy paths
- Sets up Playwright if not configured (with user confirmation)
- Generates pytest tests for backend APIs and Playwright tests for UI flows
- Runs both test suites and reports results
- Reports any bugs found in the source code separately (does not hide them)

**Usage:**
```
/e2e-gen "login y registro"
/e2e-gen "dashboard alertas" --backend-only
/e2e-gen "checkout flow" --frontend-only
/e2e-gen "captura de pacientes" --no-run
```

### `/test-cases`

Generates manual test cases as a single self-contained interactive HTML, organized in tabs by user profile (role x personality), so teammates can test the app without knowing the code.

**What it does:**
- Analyzes the whole app (or the scope you name) and derives user profiles from the code
- Optionally checks screens at runtime against a local URL
- The HTML lets testers mark OK / Fail / Blocked / N-A, take notes, keeps progress in the browser, and exports results to JSON/Markdown and ready-to-paste bug reports

**Usage:**
```
/test-cases
/test-cases apps/portal/ --url http://localhost:8000
/test-cases "login y registro" --no-browser
```

### `/coverage-ci`

Wires coverage measurement with ratcheting thresholds and a GitHub Actions workflow that runs the tests on every PR, without breaking the existing suite.

**Usage:**
```
/coverage-ci
/coverage-ci --python-only
/coverage-ci --js-only --no-ci
/coverage-ci --threshold 70
```

### `/guia-usuario`

Generates a professional end-user manual for a web app: explores every screen, takes real screenshots with Playwright, documents each screen and action in plain language, produces an HTML for review and then a PDF.

Requires [md-to-pdf-engine](https://github.com/j-aldama/md-to-pdf-engine) (see [Setup](#setup)). It uses the engine's `manual-usuario` and `ejecutiva-oscura` templates. Until they are merged into the engine's `main`, check out its `feature/manual-usuario-and-ejecutiva-oscura-templates` branch before running `npm run build`.

**Usage:**
```
/guia-usuario
/guia-usuario docs/manual/ "Mi Producto"
```

### `/plan-auditado`

Writes or audits an implementation plan and gets it approved by an independent judge (Codex), up to 3 rounds. The author never approves its own plan: `scripts/jurado.py` decides from the recorded verdicts. It implements only with `--implementar` and an approved plan.

**What it does:**
- Writes the plan in a fixed table format (`plantillas/plan.html`) with cited `file:line` references, a 9-type test matrix and explicit `PENDIENTE` items
- If the plan touches the UI, adds an interface decision per screen and a `/diseno-ui critica` step
- Runs Codex rounds; every finding is fixed or answered with evidence
- `--con-advisor` adds a second judge (`agents/advisor.md` or `agents/advisor-opus.md`)

**Usage:**
```
/plan-auditado "los problemas a resolver"
/plan-auditado --plan docs/plan.html
/plan-auditado "..." --implementar
```

## Skills

### `implementa-plan`

From an agreed plan to a PR: implementation, test gaps found by Codex, tests of every type that are seen failing against a production mutation, manual test cases written by another agent and run with Playwright (screenshot and logs per step), double review of that evidence, final review by Codex + Claude (max. 3 rounds), isolated validation in a network-less container, and the PR. `scripts/implementa_plan.py` checks every step and keeps the record outside the repo. Invoking it is the go-ahead for that plan.

```
/implementa-plan docs/plan.html --url http://localhost:8000
```

### `diseno-ui`

Design vocabulary and review for web interfaces: screen types (operate, read, persuade, showcase), a quality floor, a UX critique with Nielsen heuristic scores and P0–P3 priorities, and commands to harden, polish, rewrite UI copy, and adjust intensity, typography, layout, color and motion. It also documents the visual system in `DESIGN.md`. It is used automatically on UI requests, or explicitly:

```
/diseno-ui critica templates/dashboard.html
/diseno-ui endurecer el formulario de alta
/diseno-ui documentar
```

Adapted from [pbakaus/impeccable](https://github.com/pbakaus/impeccable) under Apache 2.0 (see `skills/diseno-ui/NOTICE.md`), without its binary, hooks, live mode or telemetry.

### `generar-pdf`

Converts a Markdown file into a professional PDF with [md-to-pdf-engine](https://github.com/j-aldama/md-to-pdf-engine).

```
/generar-pdf docs/reporte.md --template corporativa-clasica --cover
```

## Setup

### Prerequisites

- [Claude Code](https://claude.ai/code) installed
- [Plane](https://plane.so) instance with API access, and the Plane MCP server configured in Claude Code (for `/cotizacion-to-backlog` and `/validar-prd`)
- For `/plan-auditado` and `implementa-plan`:
  - Python 3.12+ as `python3`
  - [Codex CLI](https://github.com/openai/codex) authenticated, with access to the pinned model `gpt-6.1-sol` (see `MODELO_CODEX` in `scripts/jurado.py`)
  - Docker, for the isolated validation (`scripts/valida_impl.py`). Build the image once: `docker build -t ejecutor-valida ~/.claude/scripts/ejecutor`
  - [GitHub CLI](https://cli.github.com) (`gh`) to open the PR, and Playwright in the target project for the evidence runs
- For `generar-pdf` and `/guia-usuario`: [md-to-pdf-engine](https://github.com/j-aldama/md-to-pdf-engine) cloned and built, with its path in `MD_PDF_ENGINE`:
  ```bash
  git clone https://github.com/j-aldama/md-to-pdf-engine.git
  cd md-to-pdf-engine && npm install && npm run build
  export MD_PDF_ENGINE="$PWD"   # add it to your shell profile
  ```

### Installation

The repo mirrors the layout of `~/.claude`. Copy every folder into it:

```bash
for d in commands skills scripts schemas rubricas agents plantillas; do
  mkdir -p ~/.claude/$d && cp -R $d/. ~/.claude/$d/
done
```

The scripts look for `schemas/`, `rubricas/` and `auditorias/` under `$CLAUDE_HOME` (default `~/.claude`). Audit records are written to `~/.claude/auditorias/`, outside your project repos.

If you only want the Plane and QA commands, copying `commands/*.md` is enough (globally to `~/.claude/commands/` or per project to `.claude/commands/`).

### Running the script tests

```bash
cd ~/.claude/scripts
python3 -m unittest tests.test_jurado tests.test_implementa_plan tests.test_valida_impl tests.test_rubrica tests.test_ejecutor_real
```

`python3` must be 3.12+, also for the subprocesses the tests launch. `test_ejecutor_real` is skipped when Docker or the `ejecutor-valida` image is missing.

### Conventions these commands assume

- **Plan first, implement only on an explicit go-ahead.** `/plan-auditado` implements only with `--implementar` and an approved plan; invoking `implementa-plan` is the go-ahead for that plan.
- The instructions name the repo owner ("Juan") as the person who approves and answers questions. Replace it with your name if you adopt them.

### Plane MCP Configuration

These commands use `mcp__plane-admin` tools. Add the Plane MCP server to your Claude Code settings:

```json
{
  "mcpServers": {
    "plane-admin": {
      "command": "npx",
      "args": ["-y", "@anthropic/plane-mcp-server"],
      "env": {
        "PLANE_API_URL": "https://your-plane-instance.com",
        "PLANE_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

## Workflow

These commands and skills form a complete project management, delivery and QA cycle:

```
Quote/Spec docs ──► /cotizacion-to-backlog ──► Backlog in Plane
                                                      │
PRD (prd.json) ───► /validar-prd ─────────────► Sync check
                                                      │
Codebase ─────────► /audit-scope ─────────────► Coverage report
                                                      │
Codebase ─────────► /e2e-gen ─────────────────► Backend + Playwright tests
                                                      │
Codebase ─────────► /acceptance-checklist ────► Manual QA protocol
                                                      │
Protocol ─────────► /checklist-cliente ───────► Client-ready PDF

Problems ─────────► /plan-auditado ───────────► Plan approved by the judge
                                                      │
Approved plan ────► /implementa-plan ─────────► Tested PR with evidence
                                                      │
Screens ──────────► /diseno-ui critica ───────► Scored UX review
```

1. **Start**: Use `/cotizacion-to-backlog` to create the initial backlog from client quotes
2. **Validate**: Use `/validar-prd` to ensure PRD and Plane stay in sync
3. **Audit**: Use `/audit-scope` to verify code coverage against the spec
4. **Auto-test**: Use `/e2e-gen` to generate backend + frontend tests for each feature
5. **Manual test**: Use `/acceptance-checklist` to generate manual QA protocols before delivery
6. **Client sign-off**: Use `/checklist-cliente` to generate a client-facing checklist PDF for signature
7. **Plan**: Use `/plan-auditado` to get each change planned and approved before writing code
8. **Implement**: Use `/implementa-plan` to go from the approved plan to a tested PR
9. **Review the UI**: Use `/diseno-ui critica` on every screen the change touches

## Examples

See the [`examples/`](examples/) folder for:
- `prd-example.json` — Sample PRD structure for `/validar-prd`
- `plane-estimates-example.json` — Fibonacci estimate point UUID mapping

## Tech Stack

- [Claude Code](https://claude.ai/code) — AI-powered CLI
- [Plane](https://plane.so) — Open source project management
- Plane MCP Server — Model Context Protocol integration

## License

MIT, except `skills/diseno-ui/`, which is Apache 2.0 (adapted from [pbakaus/impeccable](https://github.com/pbakaus/impeccable); see its `LICENSE` and `NOTICE.md`).
