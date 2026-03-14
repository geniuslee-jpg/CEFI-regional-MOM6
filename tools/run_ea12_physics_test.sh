#!/bin/bash
#
# EA12 Physics-Only Test - Full Preprocessing & Run Script
#
# Usage:
#   cd /data01/labdisk/sungjin/MOM6-COBALT
#   bash tools/run_ea12_physics_test.sh
#
# Prerequisites:
#   - GEBCO_2024.nc in input/grid/
#   - GLORYS wide data in input/ocean_ic_bc/glorys12/glorys12_EAS_wide_1993.nc
#   - ERA5 data in input/atmos/era5/ (120 files)
#   - vgrid_75_2m.nc in tools/grid/
#
set -e

BASEDIR="/data01/labdisk/sungjin/MOM6-COBALT"
EXPDIR="$BASEDIR/exps/EA12.COBALT"
INPUTDIR="$EXPDIR/INPUT"
TOOLDIR="$BASEDIR/tools"
CEFI_REF="$BASEDIR/cefi_ref"

echo "============================================"
echo " EA12 Physics-Only Test Setup"
echo "============================================"

# Step 0: Create directories
echo ""
echo "--- Step 0: Directory check ---"
mkdir -p "$INPUTDIR" "$EXPDIR/RESTART"

# Step 1: Extract GEBCO EA12 subset
echo ""
echo "--- Step 1: GEBCO EA12 extraction ---"
if [ ! -f "$BASEDIR/input/bathymetry/GEBCO_EA12.nc" ]; then
    if [ -f "$BASEDIR/input/grid/GEBCO_2024.nc" ]; then
        mkdir -p "$BASEDIR/input/bathymetry"
        python3 -c "
import xarray as xr
print('Loading GEBCO_2024.nc...')
gebco = xr.open_dataset('$BASEDIR/input/grid/GEBCO_2024.nc')
print('Extracting EA12 region (105-160E, 15-52N)...')
ea12 = gebco.sel(lon=slice(105, 160), lat=slice(15, 52))
ea12.to_netcdf('$BASEDIR/input/bathymetry/GEBCO_EA12.nc')
print('[OK] GEBCO_EA12.nc created')
"
    else
        echo "ERROR: GEBCO_2024.nc not found in input/grid/"
        echo "Download: wget https://www.bodc.ac.uk/data/open_download/gebco/gebco_2024/zip/ -O GEBCO_2024.zip"
        exit 1
    fi
else
    echo "[SKIP] GEBCO_EA12.nc already exists"
fi

# Step 2: Generate grid files
echo ""
echo "--- Step 2: Grid generation ---"
if [ ! -f "$INPUTDIR/ocean_hgrid.nc" ]; then
    cd "$BASEDIR"
    python3 tools/grid/create_ea12_grid.py
else
    echo "[SKIP] Grid files already exist"
fi

# Step 3: Copy vertical grid
echo ""
echo "--- Step 3: Vertical grid ---"
if [ ! -f "$INPUTDIR/vgrid_75_2m.nc" ]; then
    cp "$TOOLDIR/grid/vgrid_75_2m.nc" "$INPUTDIR/"
    echo "[OK] vgrid_75_2m.nc copied"
else
    echo "[SKIP] vgrid_75_2m.nc already exists"
fi

# Step 4: Generate initial conditions from GLORYS
echo ""
echo "--- Step 4: Physical initial conditions (MOM.res.nc) ---"
if [ ! -f "$INPUTDIR/MOM.res.nc" ]; then
    cd "$BASEDIR"
    PYTHONPATH="$CEFI_REF/tools/initial:$CEFI_REF/tools/boundary" \
        python3 "$CEFI_REF/tools/initial/write_glorys_initial.py" \
        --config_file "$TOOLDIR/initial/ea12_glorys_ic.yaml"
    echo "[OK] MOM.res.nc generated"
else
    echo "[SKIP] MOM.res.nc already exists"
fi

# Step 5: Generate OBC (boundary conditions)
echo ""
echo "--- Step 5: Open boundary conditions ---"
if [ ! -f "$INPUTDIR/uv_001.nc" ]; then
    cd "$BASEDIR"
    PYTHONPATH="$TOOLDIR/boundary:$CEFI_REF/tools/boundary" \
        python3 "$TOOLDIR/boundary/write_ea12_obc.py" \
        --config "$TOOLDIR/boundary/ea12_obc.yaml"
    echo "[OK] OBC files generated"
else
    echo "[SKIP] OBC files already exist"
fi

# Step 6: Process ERA5 atmospheric forcing
echo ""
echo "--- Step 6: ERA5 atmospheric forcing ---"
if [ ! -f "$INPUTDIR/ERA5_t2m_1993_padded.nc" ]; then
    cd "$BASEDIR"
    python3 "$TOOLDIR/atmos/pad_era5_ea12.py"
    echo "[OK] ERA5 padded files generated"
else
    echo "[SKIP] ERA5 padded files already exist"
fi

# Step 7: Copy config files from repo
echo ""
echo "--- Step 7: Configuration files ---"
REPO_EXP="$CEFI_REF/exps/EA12.COBALT"
if [ -d "$REPO_EXP" ]; then
    # Copy config files that are not in INPUT/
    for f in data_table field_table diag_table input.nml; do
        if [ -f "$REPO_EXP/$f" ]; then
            cp "$REPO_EXP/$f" "$EXPDIR/"
            echo "  [OK] Copied $f"
        fi
    done
    # Copy INPUT/ config files
    for f in MOM_input MOM_override MOM_layout MOM_mask_table SIS_input SIS_layout SIS_override; do
        if [ -f "$REPO_EXP/INPUT/$f" ]; then
            cp "$REPO_EXP/INPUT/$f" "$INPUTDIR/"
            echo "  [OK] Copied INPUT/$f"
        fi
    done
else
    echo "  Config files should be at: $REPO_EXP"
    echo "  Pull from git: cd $CEFI_REF && git pull"
fi

# Step 8: Verify all required files
echo ""
echo "--- Step 8: File verification ---"
echo ""
MISSING=0
for f in ocean_hgrid.nc ocean_topog.nc ocean_mosaic.nc grid_spec.nc vgrid_75_2m.nc \
         MOM.res.nc \
         uv_001.nc uv_002.nc uv_003.nc \
         thetao_001.nc thetao_002.nc thetao_003.nc \
         so_001.nc so_002.nc so_003.nc \
         zos_001.nc zos_002.nc zos_003.nc \
         ERA5_t2m_1993_padded.nc ERA5_u10_1993_padded.nc ERA5_v10_1993_padded.nc \
         ERA5_msl_1993_padded.nc ERA5_sphum_1993_padded.nc \
         ERA5_ssrd_1993_padded.nc ERA5_strd_1993_padded.nc \
         ERA5_lp_1993_padded.nc ERA5_sf_1993_padded.nc \
         MOM_input MOM_override MOM_layout MOM_mask_table \
         SIS_input SIS_layout SIS_override; do
    if [ -f "$INPUTDIR/$f" ]; then
        echo "  [OK] INPUT/$f"
    else
        echo "  [MISSING] INPUT/$f"
        MISSING=$((MISSING + 1))
    fi
done

for f in data_table field_table diag_table input.nml; do
    if [ -f "$EXPDIR/$f" ]; then
        echo "  [OK] $f"
    else
        echo "  [MISSING] $f"
        MISSING=$((MISSING + 1))
    fi
done

echo ""
if [ $MISSING -eq 0 ]; then
    echo "============================================"
    echo " All files ready! Run the model:"
    echo ""
    echo "  cd $EXPDIR"
    echo "  mpirun -np 100 /data01/labdisk/sungjin/COBART_TEST/CEFI-regional-MOM6/builds/build/mylinux-gnu/ocean_ice/repro/MOM6SIS2"
    echo ""
    echo "============================================"
else
    echo "============================================"
    echo " $MISSING files missing. Fix above issues."
    echo "============================================"
fi
