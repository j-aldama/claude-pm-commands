# claude-pm-commands

Claude Code custom commands for project management automation with [Plane](https://plane.so).

Turn quotes and specs into structured backlogs, validate PRDs against your board, and audit scope coverage — all from the terminal.

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

These three commands form a complete project management cycle:

```
Quote/Spec docs ──► /cotizacion-to-backlog ──► Backlog in Plane
                                                      │
PRD (prd.json) ───► /validar-prd ─────────────► Sync check
                                                      │
Codebase ─────────► /audit-scope ─────────────► Coverage report
```

1. **Start**: Use `/cotizacion-to-backlog` to create the initial backlog from client quotes
2. **Validate**: Use `/validar-prd` to ensure PRD and Plane stay in sync
3. **Audit**: Use `/audit-scope` to verify code coverage against the spec

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
