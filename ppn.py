"""Main program for FMI-PPN.

FMI-PPN (Finnish Meteorological Institute Probabilistic Precipitation
Nowcaster) is a script for weather radar-based nowcasting. It is
heavily based on pySTEPS initiative.

For more information about pySTEPS, see https://pysteps.github.io .

Author: Petteri Karsisto
Year: 2019
"""
import datetime as dt
import os

import numpy as np
import h5py
import pysteps
from pysteps import rcparams as pystepsrc

import ppn_logger
import ppn_config
import utils

# Global object for storing and accessing configuration parameters
PD = dict()

def run(timestamp=None, config=None, **kwargs):
    """Main function for FMI-PPN.

    Input:
        timestamp -- timestamp of form YYYYMMDDHHMM (str)
                     If None, use latest composite (default=None)
        config -- Configuration parameter. If None, use defaults. (default=None)

    Optional keyword arguments:
        test -- If True, use development configuration (default=False)
    """

    if kwargs.get("test", False):
        # Use frontal precipitation event (verification) for development
        config = "dev"
        timestamp = "201506231400"

    PD.update(get_config(config))

    # TODO: log_folder should be parameter with a default value
    # TODO: log_fname should be parameter with a default value
    # Configure logging if enabled
    if PD["WRITE_LOG"]:
        log_folder = os.path.expanduser("~/devel/fmippn/logs/")
        log_fname = "ppn-{:%Y%m%d}.log".format(dt.datetime.utcnow())
        ppn_logger.config_logging(os.path.join(log_folder, log_fname))

    log("info", "Program starting.")
    log("debug", "Start setup")

    # Default is generate nowcasts from previous radar composite
    # We need to replace utcnow() minutes with nearest (floor) multiple of 5
    # to get a valid timestamp for the data
    # However, if a timestamp is given, that should be used.
    if timestamp is not None:
        startdate = dt.datetime.strptime(timestamp, "%Y%m%d%H%M")
    else:
        startdate = utcnow_floored(increment=5)

    # TODO: Better file name
    # Use a development name for output file for clarity purposes
    if kwargs.get("test", False):
        nc_fname = "00_nc_dev.h5"
    else:
        nc_fname = "nc_{:%Y%m%d%H%M}.h5".format(startdate)

    enddate = startdate + dt.timedelta(minutes=PD["MAX_LEADTIME"])


    # GENERAL SETUP

    # generate suitable objects for passing to pysteps methods
    datasource, nowcast_kwargs = generate_pysteps_setup()

    # Used methods
    importer = importer_method(name=datasource["importer"])
    optflow = optflow_method()
    nowcaster = nowcast_method()

    log("debug", "Setup finished")


    # NOWCASTING

    log("info", "Generating nowcasts from %s to %s" % (startdate, enddate))

    time_at_start = dt.datetime.today()

    observations, obs_metadata = read_observations(startdate, datasource, importer)

    motion_field = optflow(observations)

    ensemble_forecast, ens_meta = generate(observations, motion_field, nowcaster,
                                           nowcast_kwargs, metadata=obs_metadata)


    deterministic, det_meta = generate_deterministic(observations, motion_field, nowcaster,
                                                     nowcast_kwargs, metadata=obs_metadata)

    time_at_end = dt.datetime.today()
    log("debug", "Finished nowcasting at %s" % time_at_end)
    log("info", "Finished nowcasting. Time elapsed: %s" % (time_at_end - time_at_start))

    gen_output = {
        "motion_field": motion_field,
        "fct": ensemble_forecast,
        "det_fct": deterministic,
    }

    # Metadata for storage
    store_meta = dict()

    if "unit" in ens_meta:
        unit = ens_meta["unit"]
    elif "unit" in det_meta:
        unit = det_meta["unit"]
    else:
        unit = "Unknown"
    store_meta["unit"] = unit
    store_meta["seed"] = PD["SEED"]

    # WRITE OUTPUT TO A FILE
    write_to_file(startdate, gen_output, time_at_start, time_at_end, nc_fname, store_meta)
    log("info", "Finished writing output to a file.")

    log("info", "Run complete. Exiting.")

# TODO: Automatically add more options here based on ppn_config.py? How?
# Overriding defaults with configuration from file
def get_config(init=None):
    """Get configuration parameters and update non-default values."""
    params = ppn_config.defaults

    if init is not None:
        cfg = ppn_config.get_params(init)
    else:
        cfg = dict()

    params.update(cfg)

    if params.get("NUM_TIMESTEPS", None) is None:
        params.update(NUM_TIMESTEPS=int(params["MAX_LEADTIME"] / params["NOWCAST_TIMESTEP"]))

    return params


def log(level, msg, *args, **kwargs):
    """Wrapper for ppn_logger. Function does nothing if writing to log is
    not enabled."""
    if PD["WRITE_LOG"]:
        ppn_logger.write_to_log(level, msg, *args, **kwargs)


def utcnow_floored(increment=5):
    """Return UTC time with minutes replaced by latest multiple of `increment`."""
    now = dt.datetime.utcnow()
    floored_minutes = now.minute - (now.minute % increment)
    now = now.replace(minute=floored_minutes)
    return now

def importer_method(module="pysteps", **kwargs):
    """Wrapper for easily switching between modules which provide data importer
    methods.

    Input:
        module -- parameter for if/else block (default="pysteps")
        **kwargs -- additional keyword arguments passed to importer method

    Output:
        function -- a function object

    Raise ValueError for invalid `module` selectors.
    """
    if module == "pysteps":
        return pysteps.io.get_method(method_type="importer", **kwargs)
    # Add more options here

    raise ValueError("Unknown module {} for importer method".format(module))


def optflow_method(module="pysteps", **kwargs):
    """Wrapper for easily switching between modules which provide optical flow
    methods.

    Input:
        module -- parameter for if/else block (default="pysteps")
        **kwargs -- additional keyword arguments passed to optical flow method

    Output:
        function -- a function object

    Raise ValueError for invalid `module` selectors.
    """
    if module == "pysteps":
        return pysteps.motion.get_method(PD["OPTFLOW_METHOD"], **kwargs)
    # Add more options here

    raise ValueError("Unknown module {} for optical flow method".format(module))


def nowcast_method(module="pysteps", **kwargs):
    """Wrapper for easily switching between modules which provide nowcasting
    methods.

    Input:
        module -- parameter for if/else block (default="pysteps")
        **kwargs -- additional keyword arguments passed to nowcast method

    Output:
        function -- a function object

    Raise ValueError for invalid `module` selectors.
    """
    if module == "pysteps":
        return pysteps.nowcasts.get_method("steps", **kwargs)
    # Add more options here

    raise ValueError("Unknown module {} for nowcast method".format(module))


def generate_pysteps_setup():
    """Generate `datasource` and `nowcast_kwargs` objects that are suitable
    for using in pysteps nowcasting methods."""
    # Paths, importers etc.
    datasource = pystepsrc["data_sources"][PD["DOMAIN"]]
    datasource["root_path"] = os.path.expanduser(datasource["root_path"])

    # kwargs for nowcasting method
    nowcast_kwargs = {
        "n_cascade_levels": PD["NUM_CASCADES"],
        "kmperpixel": PD["KMPERPIXEL"],
        "timestep": PD["NOWCAST_TIMESTEP"],
        "num_workers": PD["NUM_WORKERS"],
        "fft_method": PD["FFT_METHOD"],
        "n_ens_members": PD["ENSEMBLE_SIZE"],
        "vel_pert_method": PD["VEL_PERT_METHOD"],
        "seed": PD["SEED"],
    }

    # R_MIN needs to be transformed to decibel, so that comparisons can be done
    # The pysteps method is kinda clunky here, since it expects a numpy array
    # as input.
    r_min = np.asarray([PD["R_MIN"]])
    nowcast_kwargs["R_thr"] = pysteps.utils.transformation.dB_transform(r_min)[0][0]


    return datasource, nowcast_kwargs


def read_observations(startdate, datasource, importer):
    """Read observations from archives using pysteps methods."""
    try:
        filelist = pysteps.io.find_by_date(startdate,
                                           datasource["root_path"],
                                           datasource["path_fmt"],
                                           datasource["fn_pattern"],
                                           datasource["fn_ext"],
                                           datasource["timestep"],
                                           num_prev_files=PD["NUM_PREV_OBSERVATIONS"])
    except OSError:
        # Re-raise so traceback is shown in stdout and program stops
        # TODO: Implement more detailed error logging for this
        # TODO: Implement more graceful exit strategy or ability to retry
        log("error", "OSError was raised, see output for traceback")
        raise

    # PGM files contain dBZ values
    obs, _, metadata = pysteps.io.readers.read_timeseries(filelist,
                                                          importer,
                                                          **datasource["importer_kwargs"])

    # TODO: Refactor the conversion into own method
    # TODO: Check if optical flow and FFT methods work also for dBZ values, not just dBR values
    # Converting dBZ to rain rate
    obs, metadata = pysteps.utils.conversion.to_rainrate(obs, metadata, PD["ZR_A"], PD["ZR_B"])

    # NaNs need to be converted to finite values before decibel transformation
    obs[~np.isfinite(obs)] = metadata["zerovalue"]

    # Decibel transformation (R -> dBR) is done for FFT calculations
    obs, metadata = pysteps.utils.transformation.dB_transform(obs, metadata)

    return obs, metadata


def generate(observations, motion_field, nowcaster, nowcast_kwargs, metadata=None):
    """Generate ensemble nowcast using pysteps nowcaster."""
    if PD["GENERATE_ENSEMBLE"]:
        fct = nowcaster(observations,
                        motion_field,
                        PD["NUM_TIMESTEPS"],
                        **nowcast_kwargs)

        fct, meta = pysteps.utils.transformation.dB_transform(fct, metadata, inverse=True)
        # Convert to dBZ if wanted, RRATE units are default units
        if PD["FIELD_VALUES"] == "DBZ":
            fct, meta = pysteps.utils.conversion.to_reflectivity(fct, meta, PD["ZR_A"], PD["ZR_B"])
    else:
        fct, meta = None, dict()

    return fct, meta


def generate_deterministic(observations, motion_field, nowcaster, nowcast_kwargs,
                           metadata=None):
    """Generate deterministic nowcast using pysteps nowcaster."""
    if PD["GENERATE_DETERMINISTIC"]:
        # Need to override ensemble settings and to set noise settings to None
        # for deterministic nowcast generation
        det_kwargs = nowcast_kwargs.copy()
        det_kwargs.update({
            "n_ens_members": 1,
            "noise_method": None,
            "vel_pert_method": None,
        })
        det_fct = nowcaster(observations,
                            motion_field,
                            PD["NUM_TIMESTEPS"],
                            **det_kwargs)

        det_fct, meta = pysteps.utils.transformation.dB_transform(det_fct, metadata,
                                                                  inverse=True)
        # Convert to dBZ if wanted, RRATE units are default units
        if PD["FIELD_VALUES"] == "DBZ":
            det_fct, meta = pysteps.utils.conversion.to_reflectivity(det_fct, meta, PD["ZR_A"], PD["ZR_B"])
    else:
        det_fct, meta = None, dict()

    return det_fct, meta


def prepare_data_for_writing(forecast=None, deterministic=None):
    """Convert and scale ensemble and deterministic forecast data to uint16 type"""
    # Store data in integer format to save space (float64 -> uint16)
    store_dtype = 'uint16'
    store_nodata_value = np.iinfo(store_dtype).max if store_dtype.startswith('u') else -1
    scaler = PD["SCALER"]
    scale_zero = PD["SCALE_ZERO"]
    if scale_zero in [None, "auto"]:
        scale_zero = None

    if PD["GENERATE_ENSEMBLE"] and PD["STORE_ENSEMBLE"] and forecast is not None:
        if scale_zero is None:
            scale_zero = np.nanmin(forecast)
        fct = utils.prepare_fct_for_saving(forecast, scaler, scale_zero, store_dtype,
                                           store_nodata_value)
    else:
        fct = None

    if PD["GENERATE_DETERMINISTIC"] and PD["STORE_DETERMINISTIC"] and deterministic is not None:
        if scale_zero is None:
            scale_zero = np.nanmin(deterministic)
        det_fct = utils.prepare_fct_for_saving(deterministic, scaler, scale_zero, store_dtype,
                                               store_nodata_value)
    else:
        det_fct = None

    prepared = {
        'forecast': fct,
        'deterministic': det_fct,
    }

    metadata = {
        "nodata": store_nodata_value,
        "gain": 1./scaler,
        "offset": scale_zero,
    }

    return prepared, metadata


def write_to_file(startdate, gen_output, time_at_start, time_at_end, nc_fname,
                  metadata=dict()):
    """Write output to a HDF5 file."""
    fct = gen_output["fct"]
    det_fct = gen_output.get("det_fct", None)
    motion_field = gen_output.get("motion_field", None)

    # Corner case handling when
    #   STORE_ENSEMBLE == False and
    #   STORE_DETERMINISTIC == False and
    #   STORE_MOTION == False
    # TODO: Should these raise ValueError instead of returning?
    if not PD["STORE_ENSEMBLE"] and not PD["STORE_DETERMINISTIC"] and not PD["STORE_MOTION"]:
        print("Nothing to store.")
        log("warning", "Nothing to store into .h5 file. Skipping.")
        return None
    if PD["STORE_DETERMINISTIC"] and det_fct is None:
        print("Cannot store deterministic nowcast when it is None.")
        log("error", "Cannot store deterministic nowcast when it is None.")
        return None

    # TODO: Move these to a more logical place
    if PD["OUTPUT_PATH"] is None:
        output_path = pystepsrc["outputs"]["path_outputs"]
    else:
        output_path = PD["OUTPUT_PATH"]
    output_path = os.path.expanduser(output_path)
    nc_fpath = os.path.join(output_path, nc_fname)

    prepared, scale_meta = prepare_data_for_writing(fct, det_fct)
    fct = prepared["forecast"]
    det_fct = prepared["deterministic"]

    with h5py.File(nc_fpath, 'w') as outf:
        if PD["STORE_ENSEMBLE"]:
            for eidx in range(PD["ENSEMBLE_SIZE"]):
                ens_grp = outf.create_group("member-{:0>2}".format(eidx))
                utils.store_timeseries(ens_grp, fct[eidx, :, :, :], startdate,
                                       timestep=PD["NOWCAST_TIMESTEP"],
                                       metadata=scale_meta)

        if PD["GENERATE_DETERMINISTIC"] and PD["STORE_DETERMINISTIC"]:
            det_grp = outf.create_group("deterministic")
            utils.store_timeseries(det_grp, det_fct[0, :, :, :], startdate,
                                   timestep=PD["NOWCAST_TIMESTEP"],
                                   metadata=scale_meta)

        if PD["STORE_MOTION"]:
            #~ mot_grp = outf.create_group("motion")
            outf.create_dataset("motion", data=motion_field)

        # TODO: Improve metadata storing functionality
        meta = outf.create_group("meta")
        meta.attrs["nowcast_started"] = dt.datetime.strftime(time_at_start,
                                                             PD["OUTPUT_TIME_FORMAT"])
        meta.attrs["nowcast_ended"] = dt.datetime.strftime(time_at_end,
                                                           PD["OUTPUT_TIME_FORMAT"])
        meta.attrs["nowcast_units"] = metadata.get("unit", "Unknown")
        meta.attrs["nowcast_seed"] = metadata.get("seed", "Unknown")

    return None

    # Operative runs should store the following:
    # - Deterministic member
    # - Probability products for different periods and thresholds
    # - Ensemble mean

if __name__ == '__main__':
    run(test=True)
