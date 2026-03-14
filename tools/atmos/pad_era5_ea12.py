#!/usr/bin/env python3
"""
EA12 ERA5 atmospheric forcing preprocessor.

Reads monthly ERA5 files, computes specific humidity from dewpoint,
calculates liquid precipitation, flips latitude, and pads with
the first timestep of the next year for temporal interpolation.

Usage:
    python pad_era5_ea12.py

Input:  /data01/labdisk/sungjin/MOM6-COBALT/input/atmos/era5/
        ERA5_ea12_YYYY_MM_VAR.nc  (10 variables × 12 months)
Output: /data01/labdisk/sungjin/MOM6-COBALT/exps/EA12.COBALT/INPUT/
        ERA5_{var}_1993_padded.nc
"""

import os
import numpy as np
import xarray as xr

# ============================================
# Configuration
# ============================================
YEAR = 1993
INPUT_DIR = "/data01/labdisk/sungjin/MOM6-COBALT/input/atmos/era5"
OUTPUT_DIR = "/data01/labdisk/sungjin/MOM6-COBALT/exps/EA12.COBALT/INPUT"

# ERA5 variable mapping: output_name -> (era5_varname, input_file_key)
# Files are named: ERA5_ea12_{YEAR}_{MM:02d}_{var}.nc
VARIABLES = {
    't2m':  {'era5_name': 't2m',  'output': 'ERA5_t2m'},
    'u10':  {'era5_name': 'u10',  'output': 'ERA5_u10'},
    'v10':  {'era5_name': 'v10',  'output': 'ERA5_v10'},
    'msl':  {'era5_name': 'msl',  'output': 'ERA5_msl'},
    'sp':   {'era5_name': 'sp',   'output': 'ERA5_sp'},
    'd2m':  {'era5_name': 'd2m',  'output': 'ERA5_d2m'},
    'ssrd': {'era5_name': 'ssrd', 'output': 'ERA5_ssrd'},
    'strd': {'era5_name': 'strd', 'output': 'ERA5_strd'},
    'tp':   {'era5_name': 'tp',   'output': 'ERA5_tp'},
    'sf':   {'era5_name': 'sf',   'output': 'ERA5_sf'},
}


def compute_specific_humidity(d2m, sp):
    """Compute specific humidity from 2m dewpoint temperature and surface pressure.

    Args:
        d2m: 2m dewpoint temperature (K)
        sp: surface pressure (Pa)
    Returns:
        sphum: specific humidity (kg/kg)
    """
    # Clausius-Clapeyron: saturation vapor pressure at dewpoint
    e = 611.2 * np.exp(17.67 * (d2m - 273.15) / (d2m - 29.65))
    # Specific humidity
    sphum = 0.622 * e / (sp - 0.378 * e)
    sphum = np.maximum(sphum, 0.0)
    return sphum


def compute_liquid_precip(tp, sf):
    """Compute liquid precipitation = total precip - snowfall.

    Args:
        tp: total precipitation (m)
        sf: snowfall (m water equivalent)
    Returns:
        lp: liquid precipitation (m)
    """
    lp = tp - sf
    lp = np.maximum(lp, 0.0)
    return lp


def find_era5_files(var, year):
    """Find all monthly ERA5 files for a variable and year.

    Tries multiple naming conventions:
        ERA5_ea12_{year}_{month:02d}_{var}.nc
        ERA5_{var}_{year}_{month:02d}.nc
        {var}_{year}_{month:02d}.nc
    """
    files = []
    for month in range(1, 13):
        patterns = [
            f"ERA5_ea12_{year}_{month:02d}_{var}.nc",
            f"ERA5_{var}_{year}_{month:02d}.nc",
            f"{var}_{year}_{month:02d}.nc",
        ]
        found = False
        for pat in patterns:
            fpath = os.path.join(INPUT_DIR, pat)
            if os.path.exists(fpath):
                files.append(fpath)
                found = True
                break
        if not found:
            print(f"  WARNING: No file found for {var} {year}-{month:02d}")
            print(f"  Tried: {patterns}")
            return None
    return files


def flip_latitude(ds):
    """Flip latitude from N→S to S→N if needed (MOM6 expects S→N)."""
    lat_name = None
    for name in ['latitude', 'lat']:
        if name in ds.dims:
            lat_name = name
            break
    if lat_name is None:
        return ds

    if ds[lat_name].values[0] > ds[lat_name].values[-1]:
        ds = ds.isel({lat_name: slice(None, None, -1)})
        print(f"  Flipped {lat_name} (N→S → S→N)")
    return ds


def process_variable(var, year):
    """Process a single variable: concatenate months, flip lat, output."""
    print(f"\nProcessing {var}...")

    files = find_era5_files(var, year)
    if files is None:
        return None

    print(f"  Found {len(files)} monthly files")

    # Concatenate all months
    ds = xr.open_mfdataset(files, combine='by_coords')

    # Flip latitude
    ds = flip_latitude(ds)

    return ds


def pad_with_next_year(ds, var_name, year):
    """Pad the end of the year with first timestep of next year.

    If next year data not available, duplicate last timestep with time shifted.
    """
    next_year = year + 1
    next_files = find_era5_files(var_name, next_year)

    if next_files is not None:
        # Use first timestep of next year
        next_ds = xr.open_dataset(next_files[0])
        next_ds = flip_latitude(next_ds)
        pad = next_ds.isel(time=0)
    else:
        # Duplicate last timestep with time = Jan 1 next year
        print(f"  No next year data, duplicating last timestep")
        pad = ds.isel(time=-1)

    # Set time to midnight Jan 1 of next year
    import pandas as pd
    pad_time = pd.Timestamp(f"{year + 1}-01-01T00:00:00")
    pad = pad.assign_coords(time=pad_time).expand_dims('time')

    # Concatenate
    ds_padded = xr.concat([ds, pad], dim='time')
    return ds_padded


def main():
    print("=" * 60)
    print(f" EA12 ERA5 Preprocessing")
    print(f" Year: {YEAR}")
    print(f" Input:  {INPUT_DIR}")
    print(f" Output: {OUTPUT_DIR}")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Check what files exist
    if not os.path.exists(INPUT_DIR):
        print(f"ERROR: Input directory not found: {INPUT_DIR}")
        return

    existing = os.listdir(INPUT_DIR)
    print(f"Found {len(existing)} files in input directory")

    # Process each standard variable
    processed = {}
    for var in ['t2m', 'u10', 'v10', 'msl', 'ssrd', 'strd', 'tp', 'sf', 'sp', 'd2m']:
        ds = process_variable(var, YEAR)
        if ds is not None:
            processed[var] = ds

    if not processed:
        print("ERROR: No ERA5 files found. Check file naming convention.")
        print(f"Expected files in: {INPUT_DIR}")
        print("Naming convention: ERA5_ea12_{year}_{month:02d}_{var}.nc")
        return

    # Compute derived variables
    if 'd2m' in processed and 'sp' in processed:
        print("\nComputing specific humidity from d2m and sp...")
        d2m_data = processed['d2m']['d2m'] if 'd2m' in processed['d2m'] else list(processed['d2m'].data_vars.values())[0]
        sp_data = processed['sp']['sp'] if 'sp' in processed['sp'] else list(processed['sp'].data_vars.values())[0]
        sphum = compute_specific_humidity(d2m_data, sp_data)
        sphum.name = 'sphum'
        sphum_ds = sphum.to_dataset()
        processed['sphum'] = sphum_ds

    if 'tp' in processed and 'sf' in processed:
        print("Computing liquid precipitation from tp and sf...")
        tp_data = processed['tp']['tp'] if 'tp' in processed['tp'] else list(processed['tp'].data_vars.values())[0]
        sf_data = processed['sf']['sf'] if 'sf' in processed['sf'] else list(processed['sf'].data_vars.values())[0]
        lp = compute_liquid_precip(tp_data, sf_data)
        lp.name = 'lp'
        lp_ds = lp.to_dataset()
        processed['lp'] = lp_ds

    # Output variables needed by data_table
    output_vars = {
        't2m':   'ERA5_t2m',
        'u10':   'ERA5_u10',
        'v10':   'ERA5_v10',
        'msl':   'ERA5_msl',
        'sphum': 'ERA5_sphum',
        'ssrd':  'ERA5_ssrd',
        'strd':  'ERA5_strd',
        'lp':    'ERA5_lp',
        'sf':    'ERA5_sf',
    }

    for var, prefix in output_vars.items():
        if var not in processed:
            print(f"\n  SKIP {var}: not available")
            continue

        ds = processed[var]

        # Pad with next year
        ds_padded = pad_with_next_year(ds, var if var not in ['sphum', 'lp'] else ('d2m' if var == 'sphum' else 'tp'), YEAR)

        outfile = os.path.join(OUTPUT_DIR, f"{prefix}_{YEAR}_padded.nc")
        print(f"\n  Writing {outfile}...")

        # Set encoding
        encoding = {}
        for v in ds_padded.data_vars:
            encoding[v] = {'_FillValue': None}

        ds_padded.to_netcdf(outfile, unlimited_dims='time', encoding=encoding)
        print(f"  [OK] {outfile} ({ds_padded.dims})")

    print("\n" + "=" * 60)
    print(" Done! Generated ERA5 padded files:")
    for var, prefix in output_vars.items():
        outfile = f"{prefix}_{YEAR}_padded.nc"
        exists = os.path.exists(os.path.join(OUTPUT_DIR, outfile))
        status = "[OK]" if exists else "[SKIP]"
        print(f"  {status} {outfile}")
    print("=" * 60)


if __name__ == "__main__":
    main()
