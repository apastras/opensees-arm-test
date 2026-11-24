"""OpenSees regression tests used to compare an Arm (aarch64) build with an x86-64 build.

Each test writes its numerical results to a JSON file so that two machines can be compared.
Usage: python3 run_tests.py results.json
"""
import json
import math
import platform
import sys

try:
    import opensees as ops  # locally built OpenSeesPy (opensees.so on PYTHONPATH)
    SOURCE = "source build"
except ImportError:
    try:
        import openseespy.opensees as ops  # pip package (x86 only)
    except ImportError:
        import openseespylinux.opensees as ops
    SOURCE = "pip openseespy"


def cantilever_modal():
    """Steel cantilever, 20 elastic beam elements: first 3 bending frequencies vs Euler-Bernoulli theory."""
    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 3)
    L, n = 10.0, 20
    E, A, I, rho = 210e9, 0.01, 8.0e-5, 7850.0
    m = rho * A
    for i in range(n + 1):
        ops.node(i + 1, i * L / n, 0.0)
    ops.fix(1, 1, 1, 1)
    ops.geomTransf("Linear", 1)
    for i in range(n):
        ops.element("elasticBeamColumn", i + 1, i + 1, i + 2, A, E, I, 1, "-mass", m, "-cMass")
    lam = ops.eigen("-fullGenLapack", 6)
    f = sorted(math.sqrt(x) / (2 * math.pi) for x in lam)
    # bending modes only (axial modes are much higher); analytical beta*L values
    betaL = [1.875104, 4.694091, 7.854757]
    f_th = [(b / L) ** 2 * math.sqrt(E * I / m) / (2 * math.pi) for b in betaL]
    f_num = f[:3]
    err = [abs(a - b) / b for a, b in zip(f_num, f_th)]
    return {"freq_Hz": f_num, "theory_Hz": f_th, "max_rel_error_vs_theory": max(err)}


def prestressed_cable():
    """Suspension-type cable: corotational trusses with initial tension, nonlinear gravity sag, then modal analysis."""
    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 2)
    span, n = 100.0, 40
    E, A, rho, T0 = 160e9, 0.005, 7850.0, 2.0e6
    eps0 = T0 / (E * A)
    for i in range(n + 1):
        ops.node(i + 1, i * span / n, 0.0)
    ops.fix(1, 1, 1)
    ops.fix(n + 1, 1, 1)
    ops.uniaxialMaterial("Elastic", 1, E)
    ops.uniaxialMaterial("InitStrainMaterial", 2, 1, eps0)
    for i in range(n):
        ops.element("corotTruss", i + 1, i + 1, i + 2, A, 2)
    w = rho * A * 9.81 * 5.0  # include deck dead load share (5x self-weight)
    mnode = w / 9.81 * span / n
    for i in range(2, n + 1):
        ops.mass(i, mnode, mnode)
    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    for i in range(2, n + 1):
        ops.load(i, 0.0, -w * span / n)
    ops.constraints("Plain")
    ops.numberer("RCM")
    ops.system("BandGeneral")
    ops.test("NormDispIncr", 1e-12, 50)
    ops.algorithm("Newton")
    ops.integrator("LoadControl", 0.1)
    ops.analysis("Static")
    ok = ops.analyze(10)
    sag = -ops.nodeDisp(n // 2 + 1, 2)
    ops.loadConst("-time", 0.0)
    lam = ops.eigen("-fullGenLapack", 4)
    f = [math.sqrt(x) / (2 * math.pi) for x in lam]
    forces = [ops.basicForce(i + 1)[0] for i in (0, n // 2)]
    return {"converged": ok == 0, "midspan_sag_m": sag, "freq_Hz": f, "axial_force_end_mid_N": forces}


def frame_transient():
    """3D portal frame, Rayleigh damping, Newmark time history under harmonic base-level load."""
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)
    h, b = 4.0, 6.0
    coords = {1: (0, 0, 0), 2: (b, 0, 0), 3: (0, 0, h), 4: (b, 0, h), 5: (0, b, 0), 6: (b, b, 0), 7: (0, b, h), 8: (b, b, h)}
    for t, c in coords.items():
        ops.node(t, *c)
    for t in (1, 2, 5, 6):
        ops.fix(t, 1, 1, 1, 1, 1, 1)
    for t in (3, 4, 7, 8):
        ops.mass(t, 5000.0, 5000.0, 5000.0, 0.0, 0.0, 0.0)
    E, G = 30e9, 12.5e9
    A, Iz, Iy, J = 0.16, 2.133e-3, 2.133e-3, 3.6e-3
    ops.geomTransf("PDelta", 1, 1.0, 0.0, 0.0)  # columns (vertical)
    ops.geomTransf("Linear", 2, 0.0, 0.0, 1.0)  # beams (horizontal)
    eid = 1
    for i, j in ((1, 3), (2, 4), (5, 7), (6, 8)):
        ops.element("elasticBeamColumn", eid, i, j, A, E, G, J, Iy, Iz, 1)
        eid += 1
    for i, j in ((3, 4), (7, 8), (3, 7), (4, 8)):
        ops.element("elasticBeamColumn", eid, i, j, A, E, G, J, Iy, Iz, 2)
        eid += 1
    lam = ops.eigen("-fullGenLapack", 3)
    w1, w2 = math.sqrt(lam[0]), math.sqrt(lam[2])
    zeta = 0.02
    a0 = zeta * 2 * w1 * w2 / (w1 + w2)
    a1 = zeta * 2 / (w1 + w2)
    ops.rayleigh(a0, 0.0, 0.0, a1)
    dt, npts = 0.005, 2000
    vals = [20e3 * math.sin(2 * math.pi * 3.0 * k * dt) for k in range(npts + 1)]
    ops.timeSeries("Path", 1, "-dt", dt, "-values", *vals)
    ops.pattern("Plain", 1, 1)
    ops.load(3, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    ops.constraints("Transformation")
    ops.numberer("RCM")
    ops.system("UmfPack")
    ops.test("NormDispIncr", 1e-10, 20)
    ops.algorithm("Newton")
    ops.integrator("Newmark", 0.5, 0.25)
    ops.analysis("Transient")
    peak, hist = 0.0, []
    for k in range(npts):
        if ops.analyze(1, dt) != 0:
            return {"converged": False}
        u = ops.nodeDisp(4, 1)
        peak = max(peak, abs(u))
        if k % 200 == 199:
            hist.append(u)
    return {"converged": True, "freq_Hz": [math.sqrt(x) / (2 * math.pi) for x in lam],
            "peak_disp_node4_m": peak, "disp_samples_m": hist}


def main(out):
    results = {
        "machine": platform.machine(),
        "python": platform.python_version(),
        "opensees_source": SOURCE,
        "tests": {},
    }
    for name, fn in (("cantilever_modal", cantilever_modal),
                     ("prestressed_cable", prestressed_cable),
                     ("frame_transient", frame_transient)):
        try:
            results["tests"][name] = {"ok": True, **fn()}
        except Exception as exc:  # record failures instead of stopping
            results["tests"][name] = {"ok": False, "error": repr(exc)}
        print(name, json.dumps(results["tests"][name]))
    ops.wipe()
    with open(out, "w") as fh:
        json.dump(results, fh, indent=2)
    bad = [k for k, v in results["tests"].items() if not v.get("ok") or v.get("converged") is False]
    if results["tests"].get("cantilever_modal", {}).get("max_rel_error_vs_theory", 1) > 0.01:
        bad.append("cantilever_modal accuracy")
    if bad:
        print("FAILED:", bad)
        sys.exit(1)
    print("All tests passed on", results["machine"])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results.json")
