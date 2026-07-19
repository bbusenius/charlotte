# Contributing to Charlotte

Charlotte welcomes focused bug fixes, documentation improvements, runtime
adapters, and reusable homeschool workflows. The project is maintained from a
real family's working system, so contributions must preserve the boundary
between reusable project code and private family content.

Use [SUPPORT.md](SUPPORT.md) for help and bug-reporting guidance. Report
security or privacy vulnerabilities according to [SECURITY.md](SECURITY.md),
not in a public issue containing sensitive details.

## Before opening a change

- Discuss large features or format changes in an issue before investing in an
  implementation.
- Keep purchased curricula, family records, student names, message
  attachments, spreadsheets, generated dashboards, generated slide packages,
  credentials, hosts, and tokens out of commits and test fixtures.
- Use fictional people and documentation-safe network values in examples.
- Do not add third-party text, images, audio, or code unless its provenance and
  redistribution terms are documented in `THIRD_PARTY_NOTICES.md`.
- Keep Charlotte useful without MindFeast credentials or the MindFeast Android
  application.

## Development

Create a virtual environment, install the development extra, and run the test
suite:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
```

Add focused tests for behavior changes. Do not make tests depend on a real
Signal account, family spreadsheet, paid curriculum, provider API key, or
tablet.

## License of contributions

Charlotte is licensed under the Apache License, Version 2.0. Under section 5 of
that license, any contribution intentionally submitted for inclusion in
Charlotte is submitted under Apache-2.0 unless you explicitly state otherwise
at the time of submission.

No contributor license agreement or Developer Certificate of Origin is
required at this stage. By contributing, you represent that you have the right
to submit the material under those terms.

## MindFeast compatibility and trademarks

Truthful plain-text statements that a tool or pack is compatible with
MindFeast are permitted. Do not imply that an independent contribution,
product, or pack is official, approved, certified, sponsored, or endorsed by
MindFeast. MindFeast logos, app icons, official-looking badges, and other
visual brand assets require separate permission.

MindFeast is a trademark of MindFeast LLC. The Apache-2.0 license does not
grant trademark rights.
