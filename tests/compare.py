"""Compare OpenSees results from two machines (e.g. x86-64 and aarch64).
Usage: python3 compare.py results_x86.json results_arm.json
"""
import json
import sys

RTOL = 1e-6   # relative tolerance; floating-point differences between CPUs are far smaller
ATOL = 1e-12


def flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


a = json.load(open(sys.argv[1]))
b = json.load(open(sys.argv[2]))
print(f"A: {a['machine']} ({a['opensees_source']}, Python {a['python']})")
print(f"B: {b['machine']} ({b['opensees_source']}, Python {b['python']})\n")
fa, fb = dict(flatten(a["tests"])), dict(flatten(b["tests"]))
fails, worst = [], 0.0
print(f"{'quantity':55s} {'A':>16s} {'B':>16s} {'rel diff':>10s}")
for key in sorted(set(fa) | set(fb)):
    va, vb = fa.get(key), fb.get(key)
    if isinstance(va, (int, float)) and not isinstance(va, bool) and isinstance(vb, (int, float)):
        rel = abs(va - vb) / max(abs(va), abs(vb), ATOL)
        worst = max(worst, rel)
        flag = "" if rel <= RTOL or abs(va - vb) <= ATOL else "  <-- MISMATCH"
        print(f"{key:55s} {va:16.9g} {vb:16.9g} {rel:10.2e}{flag}")
        if flag:
            fails.append(key)
    elif va != vb:
        print(f"{key:55s} {str(va):>16s} {str(vb):>16s}  <-- MISMATCH")
        fails.append(key)
print(f"\nLargest relative difference: {worst:.2e} (tolerance {RTOL:.0e})")
if fails:
    print("RESULTS DIFFER:", fails)
    sys.exit(1)
print("Arm and x86 results agree.")
