# claude-pm-commands

Claude Code custom commands for project management, QA automation, and test generation.

Turn quotes and specs into structured backlogs, validate PRDs against your board, audit scope coverage, generate acceptance test protocols, and auto-generate backend + frontend tests — all from the terminal.

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

## Setup

### Prerequisites

- [Claude Code](https://claude.ai/code) installed
- [Plane](https://plane.so) instance with API access
- Plane MCP server configured in Claude Code

### Installation

Copy the commands to your Claude Code commands directory:

```bash
# Global (available in all projects)
cp commands/*.md ~/.claude/commands/

# Or project-level (available only in current project)
mkdir -p .claude/commands
cp commands/*.md .claude/commands/
```

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

These six commands form a complete project management and QA cycle:

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
```

1. **Start**: Use `/cotizacion-to-backlog` to create the initial backlog from client quotes
2. **Validate**: Use `/validar-prd` to ensure PRD and Plane stay in sync
3. **Audit**: Use `/audit-scope` to verify code coverage against the spec
4. **Auto-test**: Use `/e2e-gen` to generate backend + frontend tests for each feature
5. **Manual test**: Use `/acceptance-checklist` to generate manual QA protocols before delivery
6. **Client sign-off**: Use `/checklist-cliente` to generate a client-facing checklist PDF for signature

## Examples

See the [`examples/`](examples/) folder for:
- `prd-example.json` — Sample PRD structure for `/validar-prd`
- `plane-estimates-example.json` — Fibonacci estimate point UUID mapping

## Tech Stack

- [Claude Code](https://claude.ai/code) — AI-powered CLI
- [Plane](https://plane.so) — Open source project management
- Plane MCP Server — Model Context Protocol integration

## License

MIT
