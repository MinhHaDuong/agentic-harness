# agentic-harness

Reusable framework for AI agent workflows: telemetry, hooks, runbooks, skills.

## Modules

### telemetry/

Usage tracking for Claude Code across all surfaces (CLI, VSCode, web, agents).

Three data layers:
- **Snapshots**: daily copies of `~/.claude/stats-cache.json` (free, all surfaces)
- **Events**: fine-grained JSONL from OTEL and agent task notifications
- **Reports**: analysis scripts reading both layers

#### Quick start

```bash
# Take first snapshot
telemetry/bin/snapshot

# Install daily cron (23:55)
telemetry/bin/install-cron

# View usage report
telemetry/bin/usage-report
```

## License

MIT
