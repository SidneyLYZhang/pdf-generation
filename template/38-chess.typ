// Chess diagrams, via the vendored staunton package (ADR-0005).
//
// This file is only inlined when the document actually uses a chess fence, so
// documents without chess never pay for the import (and never need the
// package).  The build script substitutes the pinned version, so upgrading is a
// one-place edit (`STAUNTON_VERSION` in scripts/build_pdf.py).
//
// The filter emits calls to these aliases; `st-game` is here because `at:` only
// works on a parsed game, not on raw PGN text.
#import "@preview/staunton:__STAUNTON_VERSION__": diagram as st-diagram, notation as st-notation, game as st-game, color-theme as st-color-theme
