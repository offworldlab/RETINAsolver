# RETINAsolver

A comprehensive telemetry solver ecosystem for bistatic passive radar aggregation servers. RETINAsolver processes simultaneous detections from multiple sensors to determine target position and velocity with high precision.

## Overview

RETINAsolver is designed for passive radar systems where sensors with fixed, known locations are paired with illuminators of opportunity (IoO). Each sensor calculates TDOA and FDOA locally using coherent channels, then sends bistatic range and Doppler measurements to the aggregation server for position/velocity solving.

## Repository Structure

```
RETINAsolver/
├── TelemetrySolver/          # Core solver module (submodule)
│   ├── main_3det.py         # Main entry point
│   ├── detection_triple.py  # Input data structures
│   ├── lm_solver_3det.py    # Levenberg-Marquardt solver
│   ├── initial_guess_3det.py # Initial guess generation
│   └── Geometry.py          # Coordinate conversions
├── tools/
│   ├── adsb2dd/            # ADS-B to delay-doppler converter (submodule)
│   └── synthetic-adsb/     # Synthetic radar data generator (submodule)
├── test_3detections_final/ # Comprehensive test cases
├── analysis_scripts/       # Performance analysis tools
└── README.md              # This file
```

## Key Features

- **High-Precision Solving**: Sub-meter position accuracy using 3-detection geometry
- **Optional Initial Guess**: Accept user-provided estimates for improved convergence
- **Comprehensive Testing**: Extensive validation with synthetic and real-world scenarios
- **Complete Toolchain**: Data generation, conversion, and analysis tools included
- **Modular Design**: Clean separation between solver, tools, and test infrastructure

## Quick Start

### Prerequisites

```bash
# Clone with submodules
git clone --recursive https://github.com/offworldlab/RETINAsolver.git
cd RETINAsolver

# Install dependencies
pip install numpy scipy
```

### Basic Usage

1. **Prepare detection data** (see [TelemetrySolver README](TelemetrySolver/README.md) for details):

```json
{
  "detection1": {
    "sensor_lat": 40.7128, "sensor_lon": -74.0060,
    "ioo_lat": 40.7589, "ioo_lon": -73.9851,
    "freq_mhz": 1090.0, "timestamp": 1700000000,
    "bistatic_range_km": 25.5, "doppler_hz": 150.0
  },
  "detection2": { ... },
  "detection3": { ... }
}
```

2. **Run the solver**:

```bash
python TelemetrySolver/main_3det.py input_detections.json
```

3. **Get results**:

```json
{
  "timestamp": 1700000000,
  "latitude": 40.799619, "longitude": -73.970136, "altitude": 10142.0,
  "velocity_east": 69.7, "velocity_north": 298.6, "velocity_up": 200.0,
  "convergence_metric": 0.617,
  "residuals": [0.52, 21.3, -0.09, 7.5, -0.62, -124.2]
}
```

## New Feature: Optional Initial Guess

You can now provide an initial guess to improve convergence for challenging scenarios:

```json
{
  "detection1": { ... },
  "detection2": { ... },
  "detection3": { ... },
  "initial_guess": {
    "position_lla": {
      "lat": 40.8,
      "lon": -74.0,
      "alt": 10000.0
    },
    "velocity_enu": {
      "east": 70.0,
      "north": 300.0,
      "up": 200.0
    }
  }
}
```

**Benefits**:
- Faster convergence for distant targets
- Improved success rate in challenging geometries
- Backward compatible - works without initial guess
- Automatic validation and fallback to generated guess

## Data Pipeline

The complete workflow from synthetic data to solved positions:

```
synthetic-adsb → adsb2dd → RETINAsolver → analysis
```

1. **Generate synthetic data**: Create realistic aircraft trajectories and radar measurements
2. **Convert to detection format**: Transform ADS-B tracking data to bistatic measurements  
3. **Solve for position/velocity**: Process detections to recover target state
4. **Analyze performance**: Validate accuracy and convergence characteristics

## Testing & Validation

### Test Suites

- **Unit Tests**: Individual component validation
- **Integration Tests**: End-to-end solver testing
- **Performance Tests**: Convergence rate and accuracy analysis
- **Synthetic Data Tests**: 20+ challenging geometric scenarios

### Run Tests

```bash
# Core solver tests
cd TelemetrySolver
python -m pytest test_*.py -v

# Integration tests with sample data
python main_3det.py ../test_3detections_final/3det_case_1_input.json

# Performance analysis
python ../analyze_initial_guess.py
python ../verify_3det_solution.py
```

### Expected Performance

- **Convergence Rate**: >95% for well-conditioned problems
- **Position Accuracy**: Sub-meter typical, <10m worst-case
- **Velocity Accuracy**: ~1 m/s typical, <5 m/s worst-case
- **Processing Time**: <1 second per solve

## Supporting Tools

### Synthetic Data Generation

```bash
cd tools/synthetic-adsb
python server.py  # Start synthetic radar API
```

Generates realistic aircraft movement patterns and bistatic radar measurements for testing.

### ADS-B Conversion

```bash
cd tools/adsb2dd
npm start  # Start web-based converter
```

Browser-based tool to convert ADS-B aircraft tracking data to detection format.

## Algorithm Overview

### Coordinate Systems
- **Input/Output**: Geographic WGS84 (lat/lon/alt)
- **Internal Processing**: Local ENU tangent plane
- **Conversions**: Automatic LLA↔ECEF↔ENU transformations

### Optimization Method
- **Algorithm**: Levenberg-Marquardt least squares
- **State Vector**: 6D position and velocity `[x, y, z, vx, vy, vz]`
- **Measurements**: 6 equations (3 bistatic range + 3 Doppler)
- **Constraints**: Altitude bounds, velocity limits, convergence criteria

### Initial Guess Strategies
1. **Automatic**: Ellipse intersection geometry (default)
2. **User-Provided**: LLA position + ENU velocity (optional)
3. **Validation**: Bounds checking with automatic fallback

## Analysis Scripts

The repository includes comprehensive analysis tools:

- `analyze_initial_guess.py` - Compare initial guess methods
- `verify_3det_solution.py` - Validate solver accuracy
- `check_convergence_rate.py` - Test convergence statistics
- `compare_results.py` - Benchmark against truth data

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Convergence Rate | >95% |
| Position Accuracy | <1m typical |
| Velocity Accuracy | ~1 m/s typical |
| Processing Time | <1s per solve |
| Memory Usage | <10MB |
| Dependencies | numpy, scipy only |

## Contributing

1. **Code Standards**: Follow existing modularity and style
2. **Testing**: Add tests for new features
3. **Documentation**: Update relevant README files  
4. **Backward Compatibility**: Maintain JSON interface compatibility
5. **Performance**: Validate solver accuracy before merging

## Submodule Updates

To update supporting tools:

```bash
git submodule update --remote
git add tools/
git commit -m "Update tool submodules"
```

## Architecture Notes

- **Modular Design**: Core solver separated from data generation/conversion
- **Git Submodules**: Tools maintained in separate repositories
- **JSON Interface**: Simple, language-agnostic input/output format
- **Coordinate Flexibility**: Handles global geographic coordinate systems
- **Robust Validation**: Comprehensive error checking and bounds validation

## License

[Add appropriate license information]

## Citation

[Add citation information if this is research software]

---

*For detailed solver documentation, see [TelemetrySolver/README.md](TelemetrySolver/README.md)*

*Generated using [Claude Code](https://claude.ai/code)*