# Issue 847 — `BRepFilletAPI_MakeFillet::Add` hangs

The supplied BREP is a solid produced by Boolean operations. Adding two more
fillets to edges `s_8` and `s_27` does not return in the base build.

Expected behavior: the operation should finish, either producing the fillet or
reporting a normal modeling failure. It must not consume CPU indefinitely.

The attached `output.brep` and `reproduce.tcl` are the complete headless DRAW
reproduction. The test runner uses a CPU and wall-time limit.
