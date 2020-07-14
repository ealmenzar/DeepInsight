"""
DeepInsight Toolbox
© Markus Frey
https://github.com/CYHSM/DeepInsight
Licensed under MIT License
"""
import numpy as np
import pandas as pd
import h5py

from . import hdf5
from . import stats


def read_open_ephys(fp_raw_file):
    """
    Reads ST open ephys files

    Parameters
    ----------
    fp_raw_file : str
        File path to open ephys file

    Returns
    -------
    continouos : (N,M) array_like
        Continous ephys with N timepoints and M channels
    timestamps : (N,1) array_like
        Timestamps for each sample in continous
    positions : (N,5) array_like
        Position of animal with two LEDs and timestamps
    info : object
        Additional information about experiments
    """
    fid_ephys = h5py.File(fp_raw_file, mode='r')

    # Load timestamps and continuous data, python 3 keys() returns view
    recording_key = list(fid_ephys['acquisition']['timeseries'].keys())[0]
    processor_key = list(fid_ephys['acquisition']['timeseries'][recording_key]['continuous'].keys())[0]

    # Load raw ephys and timestamps
    # not converted to microvolts, need to multiply by 0.195. We don't multiply here as we cant load full array into memory
    continuous = fid_ephys['acquisition']['timeseries'][recording_key]['continuous'][processor_key]['data']
    timestamps = fid_ephys['acquisition']['timeseries'][recording_key]['continuous'][processor_key]['timestamps']

    # We can also read position directly from the raw file
    positions = fid_ephys['acquisition']['timeseries'][recording_key]['tracking']['ProcessedPos']

    # Read general settings
    info = fid_ephys['general']['data_collection']['Settings']

    return (continuous, timestamps, positions, info)


def read_tetrode_data(fp_raw_file):
    """
    Read ST data from openEphys recording system

    Parameters
    ----------
    fp_raw_file : str
        File path to open ephys file

    Returns
    -------
    raw_data : (N,M) array_like
        Continous ephys with N timepoints and M channels
    raw_timestamps : (N,1) array_like
        Timestamps for each sample in continous
    output : (N,4) array_like
        Position of animal with two LEDs
    output_timestamps : (N,1) array_like
        Timestamps for positions
    info : object
        Additional information about experiments
    """
    (raw_data, raw_timestamps, positions, info) = read_open_ephys(fp_raw_file)
    output_timestamps = positions[:, 0]
    output = positions[:, 1:5]
    bad_channels = info['General']['badChan']
    bad_channels = [int(n) for n in bad_channels[()].decode('UTF-8').split(',')]
    good_channels = np.delete(np.arange(0, 128), bad_channels)
    info = {'channels': good_channels, 'bad_channels': bad_channels, 'sampling_rate': 30000}

    return (raw_data, raw_timestamps, output, output_timestamps, info)


def preprocess_output(fp_hdf_out, raw_timestamps, output, output_timestamps, average_window=1000, sampling_rate=30000):
    """
    Write behaviours to decode into HDF5 file

    Parameters
    ----------
    fp_hdf_out : str
        File path to HDF5 file
    raw_timestamps : (N,1) array_like
        Timestamps for each sample in continous
    output : (N,1) array_like
        Orientation
    output_timestamps : (N,1) array_like
        Timestamps for positions
    average_window : int, optional
        Downsampling factor for raw data and orientation, by default 1000
    sampling_rate : int, optional
        Sampling rate of raw ephys, by default 30000
    """
    hdf5_file = h5py.File(fp_hdf_out, mode='a')

    # Get size of wavelets
    input_length = hdf5_file['inputs/wavelets'].shape[0]

    # Get orientation and calculates alignment to the raw_data with downsampling factor average_window
    raw_timestamps = raw_timestamps[()]  # Slightly faster than np.array
    output_orientation = np.interp(raw_timestamps[np.arange(0, raw_timestamps.shape[0],
                                                       average_window)], output_timestamps, output)  #np.arange with average_window makes a reduction on the data
    raw_orientation = np.array([output_orientation]).transpose()
    
    # Create and save datasets in HDF5 File
    hdf5.create_or_update(hdf5_file, dataset_name="outputs/raw_orientation",
                          dataset_shape=[input_length, 1], dataset_type=np.float16, dataset_value=raw_positions[0: input_length, :])
    hdf5_file.flush()
    hdf5_file.close()
