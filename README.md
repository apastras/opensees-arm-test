# OpenSees on Arm (aarch64) vs x86-64

Checks that OpenSees and OpenSeesPy build and give the same results on 64-bit Arm Linux as on x86-64, ahead of running them on an NVIDIA GB10 machine (Dell Pro Precision with GB10, DGX OS = Ubuntu 24.04 on Arm).

The GitHub Actions workflow:

1. builds the latest OpenSees source with its own `makeUbuntu.sh` (Conan 2, LAPACK/OpenBLAS, no Intel MKL) on GitHub's `ubuntu-24.04` (x86-64) and `ubuntu-24.04-arm` (aarch64) runners;
2. runs a Tcl smoke test and three Python test models:
   - steel cantilever modal analysis, checked against Euler-Bernoulli theory;
   - prestressed corotational cable under gravity (nonlinear static) followed by modal analysis;
   - 3D portal frame with Rayleigh damping, Newmark time history (UmfPack solver);
3. compares every result between the two machines (relative tolerance 1e-6).

The workflow re-runs weekly against the latest OpenSees source. Built binaries are kept as run artifacts.

To test your own model, add it to `tests/run_tests.py` as another function that returns a dict of numbers.
