#!/usr/bin/env python3
"""
FINAL ANALYSIS: Why TelemetrySolver velocity signs are wrong
"""

print("=== DOPPLER SIGN CONVENTION ANALYSIS ===\n")

print("I've traced through all three systems and found the root cause!\n")

print("1. **ADSB2DD (Ground Truth System)**:")
print("   File: adsb2dd/src/server.js, Line 202")
print("   Code: const doppler = -doppler_ms/(1*(299792458/(dict[key]['fc']*1000000)));")
print("   → NEGATIVE sign applied to doppler_ms")
print("   → doppler_ms is the rate of change of bistatic delay")

print("\n2. **OUR SYNTHETIC GENERATOR**:")
print("   File: generate_test_detections.py, Line 237")
print("   Code: doppler_hz = (FREQ_MHZ * 1e6 / C) * (v_radial_tx + v_radial_rx)")
print("   → NO negative sign applied")
print("   → We calculate standard physics Doppler")

print("\n3. **TELEMETRY SOLVER**:")
print("   File: lm_solver.py, Line 63")
print("   Code: doppler_ratio = -(v_radial_ioo + v_radial_sensor) / c")
print("   → NEGATIVE sign applied")
print("   → Matches adsb2dd convention!")

print("\n=== THE MISMATCH ===")
print("✓ adsb2dd:       Uses NEGATIVE sign")
print("✗ Our generator: Uses NO negative sign") 
print("✓ TelemetrySolver: Uses NEGATIVE sign (correct!)")

print("\n=== WHY THIS CAUSES VELOCITY SIGN ERRORS ===")

print("\n1. **Our generator produces wrong-sign Doppler measurements**")
print("   - We generate: +X Hz when adsb2dd would produce -X Hz")
print("   - The measurements have opposite signs from what they should be")

print("\n2. **TelemetrySolver correctly interprets the sign convention**")
print("   - It expects adsb2dd-style measurements (with negative sign)")
print("   - It applies the correct negative sign in its calculations")
print("   - But our input data has the wrong sign!")

print("\n3. **Solver compensates by flipping velocity**")
print("   - To match wrong-sign Doppler measurements")
print("   - The solver flips the velocity signs")
print("   - This makes the calculated Doppler match our wrong measurements")
print("   - Position is still correct because range constraints dominate")

print("\n=== PHYSICAL INTERPRETATION ===")

print("\nThe negative sign in adsb2dd comes from the fact that:")
print("- doppler_ms = rate of change of bistatic delay")
print("- When target approaches: bistatic delay decreases (negative rate)")
print("- When target approaches: frequency increases (positive Doppler)")
print("- Hence: Doppler = -rate_of_delay_change")

print("\n=== VERIFICATION ===")
print("This explains perfectly why:")
print("✓ Position errors are small (30-70m) - geometry works")
print("✗ Velocity magnitudes are correct but signs are flipped")
print("✓ The pattern is consistent across all test cases")

print("\n=== THE FIX ===")
print("Our synthetic data generator should match adsb2dd convention:")
print("Change line 237 in generate_test_detections.py from:")
print("  doppler_hz = (FREQ_MHZ * 1e6 / C) * (v_radial_tx + v_radial_rx)")
print("To:")
print("  doppler_hz = -(FREQ_MHZ * 1e6 / C) * (v_radial_tx + v_radial_rx)")

print("\n=== CONFIDENCE LEVEL ===")
print("🔴 HIGH CONFIDENCE: This is definitely the root cause")
print("- adsb2dd and TelemetrySolver both use same convention")
print("- Our generator uses different convention")
print("- Explains exact symptom: correct magnitude, wrong sign")
print("- The physics and math all check out")

print("\n=== ALTERNATIVE APPROACHES ===")
print("Instead of fixing the generator, we could:")
print("1. Remove negative sign from TelemetrySolver (but breaks adsb2dd compatibility)")
print("2. Add conversion factor when using TelemetrySolver with our data")
print("3. Document the convention difference")
print("\nBut fixing the generator is the cleanest solution.")