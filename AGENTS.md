# Agent instructions — Sailfish workspace

Baseline version: 1.1.0 (2026-10-14).

These are operational instructions for coding assistants. Contributors should
start with CONTRIBUTING.md. Misja Hoebe (@misja) is the human maintainer and
retains responsibility for merge and release decisions.

- Read STATUS.md and the relevant accepted ADR before project work. Project artifacts are English; use the maintainer’s language for discussion.
- AI tools may propose changes and run authorized checks. The maintainer reviews changes before merge. Identify automated checks, assistant review and human review accurately; assistant agreement is not a human audit. AI tools cannot approve their own work, waive acceptance criteria or authorize deployment/publication.
- Work autonomously on routine reversible local work within approved scope. Software installation, remote repository creation/push, OBS writes/publication, device/system/destructive changes and security exceptions require explicit scoped human approval. Architecture approval does not grant these permissions.
- Never inspect, import, export or log real private keys, password stores, OTP seeds/URIs, passwords or recovery codes. Use synthetic fixtures and published test vectors only.
- Preserve Jolla packages, binaries and libraries. Private runtime isolation must include ELF loading, helper paths, RPM resolution, configuration, agent sockets and upgrade/removal.
- Keep one accountable owner per task. Role consultation does not transfer ownership. Investigate blockers and propose options; allow one clarification round-trip for the same blocker, then escalate to its decision owner.
- Use distinct agents only on explicit delegation authorization. Independent security/release verification is required for crypto/isolation/release-critical changes; Builder self-tests do not count as independent approval.
- Pin source/tool/template versions and cite dated evidence. Separate facts, supplied observations, assumptions and unresolved questions. No silent upstream updates or automatic Chum webhooks.
- Use one spec/plan/task set per feature. Record concise artifact handoffs in STATUS.md. Do not create speculative app/common-library repositories.
- Run checks appropriate to the change; record failures and limitations. Never label unexecuted tests as passed.
- Child repositories must contain this essential baseline themselves: a parent file outside their Git root is not assumed loaded. Copy changes with baseline version and reviewed diff.
