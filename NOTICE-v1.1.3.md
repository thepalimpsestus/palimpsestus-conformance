# Notice: conformance check v1.1.3

We found a defect in `validators/verify_corpus_conformance.py` as released in v1.1.3. It matches "Derives From:" case-sensitively, so it extracts no derivation links, and its acyclicity check passes without testing anything.

We are correcting it, and the fix will ship in the 1.1.4 pre-release.

Until then, a pass from the v1.1.3 acyclicity check should not be taken as evidence that the corpus is acyclic.

Other findings are still being verified and will be reported when confirmed.
