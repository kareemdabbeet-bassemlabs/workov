# Changelog

All notable changes to workov are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The version is the `version` field in `specs/workov.config.json`.

## [0.1]

First release of workov.

- Ticket-driven workflow for Claude Code, OpenCode and the Codex CLI: `/write-tickets` turns feature requests into `rd.md` + `eval.md`, and the `router` dispatches ready tickets to workers in isolated git worktrees or to an agent team.
- Agents: `router`, `worker`, `teammate`, `tester`, `reviewer`, `merger`, `checker`, `reproducer` and `watchdog`.
- Fleet Control Dashboard with a board, live worker cards, dependency chains, approvals, telemetry and budgets, reachable locally or through a Cloudflare Tunnel or ngrok.
- Token-based dashboard auth, push notifications (ntfy, Telegram, Slack), a script-scheduled watchdog, and direct or PR landing.
- `install.sh` to install the workflow into an existing git repository, `/setup` (`apply-setup.py`) to configure it, and `selftest.py` to check it.
