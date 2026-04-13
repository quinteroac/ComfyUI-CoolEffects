# Lessons Learned — Iteration 000004

## US-001 — Single image input remains backward-compatible

**Summary:** Added a regression test to verify `CoolVideoGenerator.execute` produces identical frame output when the image input is provided as `[H, W, 3]` or `[1, H, W, 3]`.

**Key Decisions:** Reused the existing fake ModernGL path in `tests/test_video_generator_node.py` and asserted strict tensor equality to lock in backward compatibility without changing node contracts.

**Pitfalls Encountered:** Full-suite pytest could not be cleanly used as a confidence gate because there are unrelated pre-existing failures in widget tests in this environment.

**Useful Context for Future Agents:** The implementation already supports both shapes via `_extract_input_image`; this story is protected primarily by adding explicit regression coverage rather than changing runtime behavior.

## US-002 — IMAGE batch used as per-frame texture sequence

**Summary:** Updated `CoolVideoGenerator` to accept IMAGE batches (`[N, H, W, 3]`) as a per-frame texture source, using modulo indexing so each rendered frame samples `batch[i % N]`.

**Key Decisions:** Kept a single ModernGL input texture and switched source data with `texture.write(...)` only when the modulo-selected batch frame changes; this preserves behavior for `[H, W, 3]` and `[1, H, W, 3]` while avoiding pre-uploading unused batch frames.

**Pitfalls Encountered:** Test execution initially skipped runtime coverage until `torch` was installed in the virtual environment; after installing `torch` and `numpy`, the generator tests validated the new behavior.

**Useful Context for Future Agents:** The fake texture test double now tracks upload order through `uploads`, which makes it easy to assert exact batch-frame usage and detect unnecessary GPU uploads for short outputs.
