# OCCT 2026-11-14 candidate acceptance

The main catalog gains two independent fillet cases, 32929 and GitHub #1738, and one extension to #172 covering GitHub #1177. Together with the 22 candidate folders here, this change delivers 24 independent entries plus the extension. The prior eight submissions are already in the base merge and are omitted.

- The nine reference-only DRAW reproductions are 12507, 17194, 22790, 25983, 26450, 26452, 27221, 28274, and 33904. All nine were replayed with OCCT 8.0.1 at b8f597c677811d1f9f4d8a97f5ae2825c0353a42. Each run exited successfully within a 25-second process limit and printed CASE_PASS without RUN_ERROR. The 12507 check also verifies three vertices. The 26452 check runs the reported bfillds path before testing fusion. 25983 uses the documented fuzzy tolerance of 0.001.
- The nine additional Boolean and intersection packages retain their own baseline, reference, and test scope. 31850 includes the frozen-suite replay with a fresh GCC baseline build. Its frozen B rejects the original and rotated cases and passes translation and box regression. F passes all four.
- Fillet candidates 1163, 1371, 1701 and 1702 retain the original reports and recorded B/F runs. 1163 is a fillet case derived from the upstream chamfer input. For 1371, 1701 and 1702 a controlled failure satisfies the upstream issue's expectations. The 1701 reference patch is captured at d0d43b4927a5240ad606805201227aa0982d2b35. Its incremental bundle requires the stock 8.0.1 commit. The 1702 patch is identical to the 1371 reference patch at b7c4c6fffc7f13832b68461ae480c1801151a566, with newlines normalized for reliable application.
- GitHub #1568 is held back. The available reference handles the crash by returning incomplete. The reported expectation is a successfully generated fillet.

Import the named OCCT Git bundles separately from the benchmark repository when preparing source caches. The candidate folders outside the main catalog preserve the stated validation scope and can be reviewed and registered independently.

The shared occt75-reference-source.bundle contains 9dd2d67c21767c7198a7e0b474f6c464fcd39b15 for the Boolean cases that cite that derived reference.

Large source bundles are provided separately in the local complete handoff. Their exact names and SHA-256 hashes are recorded in SOURCE-BUNDLES.md. The small incremental #1701 bundle remains in Git. Full source handoff is needed for the derived commits named in the catalog or evidence.
