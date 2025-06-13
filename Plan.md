1. Detection Module (detection.py)

  Classes:
  - Detection: Single detection data
    - Attributes: sensor_lat, sensor_lon, ioo_lat, ioo_lon, freq_mhz, timestamp, bistatic_range_km, doppler_hz
    - Methods:
        - validate(): Check data validity
  - DetectionPair: Container for two simultaneous detections
    - Attributes: detection1, detection2
    - Methods:
        - from_json(json_string): Parse input JSON
      - get_enu_origin(): Calculate midpoint between sensors in LLA

  Functions:
  - load_detections(json_file): Load and validate input

  2. Initial Guess Module (initial_guess.py)

  Functions:
  - calculate_ellipse_center_enu(ioo_enu, sensor_enu):
    - Return midpoint between foci in ENU
  - get_initial_guess(detection_pair):
    - Get ENU origin (sensor midpoint)
    - Convert all LLA positions to ENU relative to origin
    - Calculate both ellipse centers in ENU
    - Average the centers for initial position
    - Return: [x, y, vx, vy] in ENU with zero velocity

  3. LM Solver Module (lm_solver.py)

  Functions:
  - bistatic_range_residual(state, ioo_enu, sensor_enu, measured_range_m):
    - Extract x, y from state (z=5000m)
    - Calculate distances in ENU
    - Return: calculated_range - measured_range
  - doppler_residual(state, ioo_enu, sensor_enu, freq_hz, measured_doppler_hz):
    - Calculate bistatic Doppler using ENU positions/velocities
    - Return: calculated_doppler - measured_doppler
  - residual_function(state, detections_enu):
    - Calculate 4 residuals using ENU coordinates throughout
    - Return numpy array of residuals
  - solve_position_velocity(detection_pair, initial_guess):
    - Convert all positions to ENU once at start
    - Run least_squares solver
    - Return solution in ENU or None

  4. Main Program (main.py)

  Functions:
  - main():
    a. Load detections
    b. Get initial guess (in ENU)
    c. Solve (in ENU)
    d. Convert solution from ENU back to LLA using Geometry.ecef2lla
    e. Output JSON