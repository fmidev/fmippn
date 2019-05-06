# Finnish Meteorological Institute Probabilistic Precipitation Nowcasting system (FMI-PPN)
FMI-PPN is a modular weather-radar-based nowcasting system built for research and operational usage.

## Subsystems
### Precipitation motion
Current implementation of FMI-PPN uses Lucas-Kanade optical flow method to estimate precipitation movement from radar measurements.

### Nowcasting
Currently FMI-PPN uses [pysteps](https://pysteps.github.io) to generate ensemble nowcasts.

## Known issues and limitations
- Parameter _SEED_ must be `None` or an integer between `0` and `2**32 - 1`. This is a limitation in `numpy.random`.
