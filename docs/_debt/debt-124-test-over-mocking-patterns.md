# DEBT-124: Test Suite Over-Mocking Reduces Confidence

**Priority:** P2
**Status:** Open
**Found:** 2026-01-31
**Component:** `tests/unit/`

## Summary

Multiple unit tests mock so many dependencies that they test mock behavior rather than actual code. This creates brittle tests coupled to implementation details that pass when code is broken.

## Evidence

### test_ask/test_helpers.py

Lines 18-56: Tests mock 2-3 dependencies each (loader, index, build_search_index) to verify method call contracts, not actual behavior.

### test_pdf/test_converter.py

Lines 448-495: `test_convert_pdf_torch_device_is_thread_safe()` uses 5+ mock patches. The test name claims thread-safety testing but only verifies env var restoration - actual concurrent behavior is simulated, not tested.

### test_ask/test_retrieval.py

Lines 12-49: Uses `MagicMock(spec=SearchIndex)` to verify method call parameters. Never tests what real `SearchIndex.search()` returns.

## Uncle Bob's Criticism

"If all your tests pass but production breaks, you're testing too many mocks."

These tests verify:
- Method calls were made with correct arguments
- Mocks returned expected values

They don't verify:
- Actual business logic works
- Integration between components
- Real error handling

## Recommended Fix

1. Add integration tests that use real dependencies
2. Reduce mock depth - mock at boundaries, not everywhere
3. Test behavior (output given input), not implementation (method calls)

## Impact

- Medium: False confidence in test coverage
- Tests break on refactoring even when logic is correct
- Missing edge cases in real integration paths

## Related

- DEBT-074: Test quality issues (archived - partially addressed)
- DEBT-108: E2E test coverage thin (archived - partially addressed)
