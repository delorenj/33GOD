---
name: identity
description: Print the 33GOD identity view (the shell prompt's `id v1 5/6` PM segment, expanded). Use only when the user types /identity or $identity, optionally followed by an employee name.
---

Run exactly one shell command from the current working directory and reply with its
stdout verbatim, as markdown, with nothing before or after it.

- No argument: `flume identity manifest --markdown`
- An argument (an employee post such as `33god-pm` or a person such as `grolf`):
  `flume identity manifest <employee> --markdown`

Do not summarize, reformat, add commentary or run anything else. If the command
fails, print its output as it is.
