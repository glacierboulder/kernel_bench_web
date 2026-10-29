# Source and scoring scope

The exact upstream test bytes are retained as `official_upstream.tcl`. The scored wrapper isolates the reported section-continuity defect: it builds the six intersection edges and checks the section edge count, the upstream isolated-endpoint rule, and every endpoint-pair distance using the original upstream limit.

The score does not claim that the complete upstream test passes. Its separate `xdistcs` face-residual diagnostic remains available in the validation evidence; the F961 reference produced two samples above the upstream face-residual limit. That diagnostic is not part of this issue's scored defect oracle. The two neighborhood cases apply a common translation and reverse operand order while keeping the same section-continuity checks; the healthy control is separate.
