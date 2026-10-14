# Local subscription pricing patch

Based on CodexBar v0.74.1. Native Codex rollouts retain Standard, Fast and Ultrafast settings per turn and across incremental scans. Ultrafast on GPT-6.1 Sol and GPT-6 Astra uses the user's requested 8x subscription-usage equivalent against the existing standard token-price baseline. This numeric estimate is not an API charge or a measured subscription balance. Fast retains the existing API-equivalent multiplier of 2x; only the supported model table is extended.

Parser revision 13 and a distinct pricing fingerprint trigger normal bounded historical reparsing and repricing. Original caches and login state are retained.

Codex Speed description can be reapplied after model-catalog refresh with:

    python3 local-patch/reapply-speed-description.py

The script backs up the cache and changes only Ultrafast descriptions. The displayed text is the user's custom wording, not an independently measured speed guarantee.

This Mac has Command Line Tools, without full Xcode. Local packaging retains the installed, unchanged widget extension using `CODEXBAR_EXISTING_WIDGET_EXTENSION=/Applications/CodexBar.app/Contents/PlugIns/CodexBarWidget.appex`. Main app, CLI, core and app resource bundles are rebuilt. The normal package script still builds the widget from source when that explicit override is absent.

The local package uses ad-hoc signing and disables automatic update checks. Upstream CloudKit signing entitlements are not available in this build; login data is preserved but macOS may require reauthorization after the signing identity changes.

Use the installed macOS 26.5 SDK, rather than the default macOS 27 preview SDK (which requires unavailable SwiftUI state macros). The local Swift wrapper supplies that SDK to builds and tests. `@Entry` declarations are expanded into equivalent EnvironmentKey properties; dependency design-time previews are disabled. No app behavior is intentionally changed by this compatibility work.

Rebuild with `./local-patch/build-app.sh`. The preparation script makes the two dependency adjustments reproducible. The installed Vortex compiled catalog is retained for its unchanged particle images.

Focused offline tests (7 tests, parameterized cases included) passed with:

    source Scripts/test_environment.sh
    CODEXBAR_LOCAL_PRICING_TESTS=1 local-patch/toolchain/bin/swift test --disable-xctest --filter CostUsageCodexSessionTierTests

The optional manifest branch uses the same maintained tier tests and store helpers through symlinks, an isolated temporary fixture, and the installed Testing macro plugin. The normal full test target is unchanged when the environment flag is absent. Full `make test` remains unavailable here because Command Line Tools does not contain XCTest.

## GitHub maintenance

This branch is maintained in [libukai/CodexBar](https://github.com/libukai/CodexBar). Read [MAINTAINING.md](MAINTAINING.md) for the upstream mirror, release integration, recovery branches, manual GitHub checks and clean bundle installation. Machine-specific installation state and generated patch exports are ignored by Git.
