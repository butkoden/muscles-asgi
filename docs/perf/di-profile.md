# DI profile-run (muscles#36 follow-up)

Run:

```bash
PYTHONPATH=../muscles/src:src python benchmarks/profile_di_hotpath.py
```

Expected:

- script completes without errors;
- profile output dictionary contains `inspect_signature_in_profile`;
- after muscles#36 this value should stay `0` for hot-path loops.

