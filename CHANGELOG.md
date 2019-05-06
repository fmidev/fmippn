# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

This project DOES NOT adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Instead, version numbering will be a running number. Each major number increases when a dependency module is upgraded, added, or removed (e.g. pysteps). Each minor number increases when a research version is updated, either by RAS or PAK.

## [v2.0] - 2019-09-02
### Added
- Changelog
- New dependency: pysteps (1.0.0)
- Now it is possible to set motion perturbation parameters
- Default motion perturbation parameters for Lucas-Kanade method
- STEPS nowcasts can now be calculated in dBZ, no need to convert to rain rate first
- Functionality for regenerating perturbed motion fields (for a given SEED)
- Projection metadata is now stored in output file
- Configuration parameters and their values are now stored in output file
- Added new configuration parameters for controlling program flow
- Added configuration for heavy rainfall event in Helsinki on 23 Aug 2019

### Changed
- Renamed readme.md to README.md
- Deterministic nowcast uses now extrapolation
- Old deterministic nowcast is renamed as "unperturbed nowcast"
- utcnow_floored() function was moved to utils module
- Edited "dev" and "verification" parameters a bit

### Removed
- Extra dependencies that were unused or no longer needed

## [v1.1] - 2019-05-06
### Added
- New parameters: SEED, ZR\_A, ZR\_B, SCALE\_ZERO, SCALER, FIELD\_VALUES
- Now it is possible to set random number generator seed via SEED parameter
- Now R(Z)-relation coefficients _a_ and _b_ can be set via parameters ZR\_A and ZR\_B
- Nowcasts can be stored either in dBZ or mm/h units. This is chosen via FIELD\_VALUES parameter
- Scaling parameter in output file can now be set via parameter SCALER
- Scaling offset in output file can now be set via SCALE\_ZERO parameter
- Program uses nowcast data array`s minimum non-NaN value as scaling offset, unless given via configuration parameters
- Parameters SEED and FIELD\_VALUES are stored in output file`s metadata

### Changed
- "Valid for" attribute in output file is now an integer (was: string)
- OUTPUT\_TIME\_FORMAT parameter no longer affects the "Valid for" attribute

## [v1.0] - 2019-01-22
- First prototype version given to operational testing

[v2.0]:
[v1.1]:
[v1.0]:

