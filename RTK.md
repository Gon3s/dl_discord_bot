# RTK - Rust Token Killer (Codex CLI)

**Usage**: Token-optimized CLI proxy for shell commands.

## Rule

Prefix shell commands with `rtk` when RTK supports the command. Use the native
command when RTK changes required behavior, lacks a suitable proxy, or hinders
diagnosis.

Examples:

```bash
rtk git status
rtk npm run build
rtk pytest -q
rtk ruff check .
```

## Meta Commands

```bash
rtk gain            # Token savings analytics
rtk gain --history  # Recent command savings history
rtk proxy <cmd>     # Run raw command without filtering
```

## Verification

```bash
rtk --version
rtk gain
which rtk
```
