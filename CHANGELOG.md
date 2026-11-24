# RuleNova Changelog

Releases, newest first. The weekly rule updates are the
`chore(output)` commits.

## Unreleased

- Documentation: README now describes RuleNova as region-based routing, with the per-region sets as the main building blocks and `china` / `global` as combinations.
- Documentation: commercial licensing terms reworded as an explanation of "NonCommercial" in CC BY-NC-SA 4.0, not extra terms on top of it.
- Documentation: the Quantumult X parser describes `server_remote` resources by their Quantumult X name.
- Documentation: the sing-box example routes to an outbound named `China`, like the policy names in the other examples, instead of `direct`.
- Documentation: the changelog moved from the README to this file.
- Documentation: the README ends with the Nova toolkit line, like the other projects.
- Documentation: the README opens with a centered header and a navigation row, and its version badge follows the latest release instead of a hand-written number.
- No change to rule files, file names, URLs or policy names.

## 2.3.0 (2026-11-16)

- First public release.
- IPv6 in every IP rule set, using each client's native IPv6 rule type.
- Version number recorded in `output/meta.json`.
