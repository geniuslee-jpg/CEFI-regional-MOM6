#!/usr/bin/env python3
"""
EA12 OBC 생성: GLORYS 연간 파일 → MOM6 경계조건 파일

기존 write_glorys_boundary.py에서 변경된 부분:
  1. GLORYS 파일 형식: 월별 → 연간 통합 파일 (glorys12_EAS_wide_YYYY.nc)
  2. YAML에 glorys_pattern 추가 (파일명 패턴 지정)
  3. ncrcat 기본 비활성화

사용법:
  cd /data01/labdisk/sungjin/MOM6-COBALT
  python tools/boundary/write_ea12_obc.py --config tools/boundary/ea12_obc.yaml
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subprocess import run
from os import path
import xarray
import yaml
from boundary import Segment
import argparse

import warnings
warnings.filterwarnings('ignore')


def load_config(config_file):
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    return config


def write_year(year, glorys_dir, glorys_pattern, segments, variables, is_first_year=False, is_last_year=False):
    # --- 변경점 1: 연간 파일 읽기 (open_mfdataset → open_dataset) ---
    glorys_file = path.join(glorys_dir, glorys_pattern.format(year=year))
    print(f"Reading: {glorys_file}")
    glorys = (
        xarray.open_dataset(glorys_file)
        .rename({'latitude': 'lat', 'longitude': 'lon', 'depth': 'z'})
    )

    # Floor first time down to midnight so that it matches initial conditions
    if is_first_year:
        tnew = xarray.concat((glorys['time'][0].dt.floor('1d'), glorys['time'][1:]), dim='time')
        glorys['time'] = ('time', tnew.data)
    elif is_last_year:
        tnew = xarray.concat((glorys['time'][0:-1], glorys['time'][-1].dt.ceil('1d')), dim='time')
        glorys['time'] = ('time', tnew.data)

    for seg in segments:
        for var in variables:
            if var == 'uv':
                print(f'{seg.border} {var}')
                seg.regrid_velocity(glorys['uo'], glorys['vo'], suffix=year, flood=False)
            elif var == 'thetao' or var == 'so':
                print(f'{seg.border} {var}')
                seg.regrid_tracer(glorys[var], suffix=year, flood=False)
            elif var == 'zos':
                print(f'{seg.border} {var}')
                seg.regrid_tracer(glorys['zos'], suffix=year, flood=False)


def ncrcat_years(nsegments, output_dir, variables, ncrcat_names):
    if not ncrcat_names:
        ncrcat_names = variables[:]

    for var, var_name in zip(variables, ncrcat_names):
        for seg in range(1, nsegments + 1):
            run([f'ncrcat -O {var}_{seg:03d}_* {var_name}_{seg:03d}.nc'], cwd=output_dir, shell=True)


def main(config_file):
    config = load_config(config_file)

    first_year = config.get('first_year', 1993)
    last_year = config.get('last_year', 1993)
    glorys_dir = config.get('glorys_dir', '.')
    # --- 변경점 2: 파일명 패턴을 YAML에서 읽기 ---
    glorys_pattern = config.get('glorys_pattern', 'glorys12_EAS_wide_{year}.nc')
    output_dir = config.get('output_dir', './outputs')
    hgrid_file = config.get('hgrid', 'ocean_hgrid.nc')
    ncrcat_years_flag = config.get('ncrcat_years', False)
    ncrcat_names = config.get('ncrcat_names', [])

    if not path.exists(output_dir):
        os.makedirs(output_dir)

    hgrid = xarray.open_dataset(hgrid_file)

    variables = config.get('variables', [])

    segments = []
    for seg_config in config.get('segments', []):
        segment = Segment(seg_config['id'], seg_config['border'], hgrid, output_dir=output_dir)
        segments.append(segment)

    for y in range(first_year, last_year + 1):
        print(f"=== Year {y} ===")
        write_year(y, glorys_dir, glorys_pattern, segments, variables,
                   is_first_year=y == first_year, is_last_year=y == last_year)

    if ncrcat_years_flag:
        assert len(ncrcat_names) == len(variables)
        ncrcat_years(len(segments), output_dir, variables, ncrcat_names)

    print("\n=== 완료! ===")
    print(f"출력 디렉토리: {output_dir}")
    for seg_config in config.get('segments', []):
        sid = seg_config['id']
        border = seg_config['border']
        for var in variables:
            fname = f"{var}_{sid:03d}_{first_year}.nc"
            print(f"  {border}: {fname}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate EA12 OBC from Glorys')
    parser.add_argument('--config', type=str, default='ea12_obc.yaml',
                        help='YAML configuration file')
    args = parser.parse_args()
    main(args.config)
