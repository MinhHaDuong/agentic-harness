---
name: ticket-close
description: Close a local ticket.
disable-model-invocation: false
user-invocable: true
argument-hint: <ticket-id> [reason]
---

# Close ticket $ARGUMENTS

1. Parse `$ARGUMENTS`: first word is `<id>`, rest is `<reason>` (default: `done`).
2. Run: `${ERG:-erg} close <id> <reason>`
3. Commit: `git add tickets/ && git commit -m "ticket(<id>): close — <reason>"`
