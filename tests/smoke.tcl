# Minimal Tcl OpenSees check: cantilever eigen analysis
wipe
model basic -ndm 2 -ndf 3
node 1 0.0 0.0
node 2 5.0 0.0
fix 1 1 1 1
mass 2 100.0 100.0 1.0
geomTransf Linear 1
element elasticBeamColumn 1 1 2 0.01 2.0e11 1.0e-4 1
set lam [eigen -fullGenLapack 2]
puts "Tcl OpenSees eigenvalues: $lam"
if {[lindex $lam 0] <= 0} { puts "FAIL"; exit 1 }
puts "Tcl smoke test passed"
wipe
