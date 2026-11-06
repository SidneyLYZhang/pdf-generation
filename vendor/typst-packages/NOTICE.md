# Vendored Typst package: `staunton` 2.0.0

This subtree vendors the Typst Universe package **`staunton` 2.0.0**, pinned and unmodified,
from <https://github.com/ndg6/staunton> (tag `v2.0.0`). It is resolved at build time with
`typst compile --package-path <repo>/vendor/typst-packages`, so documents can keep importing
`@preview/staunton:2.0.0` without any network access.

Every file was extracted from the upstream `v2.0.0` tree and checked byte-for-byte against its
git blob SHA-1 and size.

## Licensing

- **Typst code** (`lib.typ`, `typst.toml`, `src/*.typ`, `src/assets/i18n/*.typ`) is **MIT**,
  © 2026 Frank Lippert.
- **Bundled piece SVGs** (`src/assets/piece_sets/cburnett`, `src/assets/piece_sets/merida`) are
  **GPL-2.0-or-later** (see `LICENSE-PIECES`).
- The rest of the `pdf-generation` repository remains **MIT**. This subtree is the single
  GPL-bearing exception; it is aggregated alongside, not linked into, the MIT code, so the
  repository's own licence and produced PDFs are unaffected.

## Upgrading

1. Replace the whole `preview/staunton/<version>` directory with the new release bundle.
2. Update every `@preview/staunton:<version>` import spec and the pinned version in the build script.
3. Re-run `python scripts/build_pdf.py doctor` (it imports the package and renders an empty board), then re-render a document that actually contains a board.
