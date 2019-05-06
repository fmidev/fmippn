"""Utility functions for FMI-PPN"""
import datetime as dt

import numpy as np
import h5py


def utcnow_floored(increment=5):
    """Return UTC time with minutes replaced by latest multiple of `increment`."""
    now = dt.datetime.utcnow()
    floored_minutes = now.minute - (now.minute % increment)
    now = now.replace(minute=floored_minutes)
    return now


def store_timeseries(grp, data, startdate, timestep, metadata=dict()):
    """Store timeseries for one member"""
    for index in range(data.shape[0]):
        ts_point = data[index, :, :]
        tmp = grp.create_dataset("leadtime-{:0>2}".format(index), data=ts_point)
        valid_time = startdate + (index + 1) * dt.timedelta(minutes=timestep)
        tmp.attrs["Valid for"] = int(dt.datetime.strftime(valid_time, "%Y%m%d%H%M%S"))
        for key, value in metadata.items():
            tmp.attrs[key] = value


def prepare_fct_for_saving(fct, scaler, scale_zero, store_dtype, store_nodata_value):
    """Scale and convert `fct` to correct datatype. NaN values are converted to
    `store_nodata_value`."""
    nodata_mask = ~np.isfinite(fct)
    fct_scaled = scaler * (fct - scale_zero)
    if store_nodata_value != -1 and np.any(fct_scaled >= store_nodata_value):
        raise ValueError("Cannot store forecast to a file: One or more values would be "
                         "larger than maximum allowed value (%i) causing overflow. "
                         % (store_nodata_value-1))
    fct_scaled[nodata_mask] = store_nodata_value
    fct_scaled = fct_scaled.astype(store_dtype)
    return fct_scaled
