# Lessons Learned — Iteration 000004

## US-001 — Single image input remains backward-compatible

**Summary:** Added a regression test to verify `CoolVideoGenerator.execute` produces identical frame output when the image input is provided as `[H, W, 3]` or `[1, H, W, 3]`.

**Key Decisions:** Reused the existing fake ModernGL path in `tests/test_video_generator_node.py` and asserted strict tensor equality to lock in backward compatibility without changing node contracts.

**Pitfalls Encountered:** Full-suite pytest could not be cleanly used as a confidence gate because there are unrelated pre-existing failures in widget tests in this environment.

**Useful Context for Future Agents:** The implementation already supports both shapes via `_extract_input_image`; this story is protected primarily by adding explicit regression coverage rather than changing runtime behavior.
