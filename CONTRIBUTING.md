# Contributing

Describe a bug, proposed change or unresolved question in the relevant repository's issue tracker. Include the affected version and target where useful. Use public or synthetic examples. Documentation and code contributions are welcome; project artifacts are written in English.

For a change, open a pull request explaining the problem, the resulting behavior and the checks you ran. State failures and checks you could not run. Link existing design or test records rather than repeating them. Keep each change small enough to review.

## AI assistance and responsibility

This project uses AI-assisted development tools. Misja Hoebe (@misja) is the maintainer and is responsible for deciding what is merged and released.

Contributors must understand and review the changes they submit, whether written manually or with assistance. If AI materially contributed to a change, briefly state what it helped with and how the result was checked. Tool output and generated text are not evidence that a change is correct.

The maintainer reviews proposed changes before merge. Crypto behavior, runtime/package isolation and release-critical changes also require verification separate from implementation. Reports must distinguish automated checks, assistant review and human review. An assistant reviewing its own work, or another assistant agreeing with it, is not a human audit. The maintainer decides whether the evidence is sufficient; unresolved findings stay open.

AI tools cannot approve their own changes, waive acceptance criteria or authorize installation or publication. Merge acceptance is separate from permission to change devices/systems, publish packages or send upstream contributions.

## Testing and licensing

Engineering tools and test reports use synthetic data or published test vectors. Do not submit real keys, password stores, OTP material, credentials or recovery data in issues, PRs or test inputs. Preserve Jolla's packages and keep private runtime isolation explicit.

Original work is GPL-3.0-or-later; see [LICENSING](LICENSING.md). Upstream code and derived patches retain the licenses and notices listed in [THIRD_PARTY](THIRD_PARTY.md).

Shared working agreements are maintained in sailfish-workspace. Each repository carries its essential contribution and assistant instructions. [AGENTS.md](AGENTS.md) gives operational instructions to coding assistants; contributors can start with this document.
