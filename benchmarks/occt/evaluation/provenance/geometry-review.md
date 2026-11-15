# Three OCCT geometry regressions

The three tasks share the locked OCCT 8.0.1 source and have separate suites. Reference patches and evidence are stored under evaluation/provenance.

- #1610: the repository offline reevaluation passed all five checks after a clean rebuild, run a2fc1d4f9e21d1b2. This run used an extended local build time limit. The upstream bug29093 performance input was unavailable.
- #25237: four checks passed with the rebuilt TKBO library in local replay. Full offline reevaluation was pending at submission. Equal-tolerance edge selection is outside the reproduced case.
- #28366: Windows replay from the original STEP failed all three angles before the patch and passed all three afterward. Linux replay from the derived BREP passed the four suite checks. Full offline reevaluation was pending at submission.
