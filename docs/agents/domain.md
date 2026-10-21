# Domain Docs

This repository uses a single-context layout:

- `CONTEXT.md` — canonical domain vocabulary
- `docs/adr/` — durable architectural decisions

## Consumer rules

Before exploring, read the root `CONTEXT.md` and relevant ADRs.
When a skill refers to the repository's `GLOSSARY.md`, use `CONTEXT.md`.

If a document is absent, proceed silently. Create domain documents lazily
when terms or decisions are resolved.

Use glossary terms exactly and respect synonyms marked under `_Avoid_`.
Surface conflicts with existing ADRs explicitly.
