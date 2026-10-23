"""Minimal offline test runner (sandbox has no pytest).

CI uses real pytest (pyproject dev extras); this runner executes the
same test functions with a tiny pytest shim so logic can be verified
without network access.
"""
import importlib.util
import sys
import traceback


class _Raises:
    def __init__(self, exc): self.exc = exc; self.value = None
    def __enter__(self): return self
    def __exit__(self, t, v, tb):
        if t is None:
            raise AssertionError(f"expected {self.exc.__name__}, nothing raised")
        if issubclass(t, self.exc):
            self.value = v
            return True
        return False

import types

shim = types.ModuleType("pytest")
shim.raises = lambda exc: _Raises(exc)
sys.modules["pytest"] = shim

def main():
    sys.path.insert(0, "src")
    import glob
    passed = failed = 0
    for path in sorted(glob.glob("tests/unit/test_*.py")):
        spec = importlib.util.spec_from_file_location(path, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name in dir(mod):
            if name.startswith("test_"):
                try:
                    getattr(mod, name)()
                    passed += 1
                    print(f"PASS {path}::{name}")
                except Exception:  # noqa: BLE001 - runner must isolate any test failure
                    failed += 1
                    print(f"FAIL {path}::{name}")
                    traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
