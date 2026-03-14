#!/usr/bin/env python3
"""
EA12 격자 생성: ocean_hgrid.nc (supergrid) + ocean_topog.nc

도메인: 105-160°E, 15-52°N, 1/12° 해상도
  NIGLOBAL = 660, NJGLOBAL = 444

사용법:
  cd /data01/labdisk/sungjin/MOM6-COBALT
  python tools/grid/create_ea12_grid.py

필요 패키지: numpy, xarray, scipy
입력: input/bathymetry/GEBCO_EA12.nc
출력: exps/EA12.COBALT/INPUT/ocean_hgrid.nc
      exps/EA12.COBALT/INPUT/ocean_topog.nc
"""

import os
import numpy as np
import xarray as xr
from scipy.interpolate import RegularGridInterpolator

# ============================================
# 설정
# ============================================
LON_START, LON_END = 105.0, 160.0
LAT_START, LAT_END = 15.0, 52.0
RESOLUTION = 1.0 / 12.0  # 1/12도

GEBCO_FILE = "input/bathymetry/GEBCO_EA12.nc"
OUTPUT_DIR = "exps/EA12.COBALT/INPUT"

# 격자 크기
NIGLOBAL = int(round((LON_END - LON_START) / RESOLUTION))  # 660
NJGLOBAL = int(round((LAT_END - LAT_START) / RESOLUTION))  # 444

# Supergrid은 2배 해상도
NXP = 2 * NIGLOBAL + 1  # 1321
NYP = 2 * NJGLOBAL + 1  # 889

EARTH_RADIUS = 6370.0e3  # meters


def create_supergrid():
    """1/12° 등간격 supergrid 생성"""
    print(f"격자 크기: NIGLOBAL={NIGLOBAL}, NJGLOBAL={NJGLOBAL}")
    print(f"Supergrid: NXP={NXP}, NYP={NYP}")

    # Supergrid 좌표 (1/24° 간격)
    x1d = np.linspace(LON_START, LON_END, NXP)
    y1d = np.linspace(LAT_START, LAT_END, NYP)
    x, y = np.meshgrid(x1d, y1d)

    # 격자 간격 계산 (미터)
    dx = np.zeros((NYP, NXP - 1))
    dy = np.zeros((NYP - 1, NXP))

    deg2rad = np.pi / 180.0
    dlon = np.diff(x, axis=1)  # (NYP, NXP-1)
    dlat = np.diff(y, axis=0)  # (NYP-1, NXP)

    # dx: 경도 방향 거리 (위도에 따라 변함)
    for j in range(NYP):
        dx[j, :] = EARTH_RADIUS * np.cos(y[j, :-1] * deg2rad) * dlon[j, :] * deg2rad

    # dy: 위도 방향 거리 (일정)
    for i in range(NXP):
        dy[:, i] = EARTH_RADIUS * dlat[:, i] * deg2rad

    # 격자 면적
    area = dx[:-1, :] * dy[:, :-1]

    # angle_dx: 등간격 lon/lat 격자에서는 0
    angle_dx = np.zeros_like(x)

    # NetCDF 저장
    ds = xr.Dataset(
        {
            "x": (["nyp", "nxp"], x),
            "y": (["nyp", "nxp"], y),
            "dx": (["nyp", "nxp_1"], dx),
            "dy": (["nyp_1", "nxp"], dy),
            "area": (["nyp_1", "nxp_1"], area),
            "angle_dx": (["nyp", "nxp"], angle_dx),
        },
        attrs={
            "title": "EA12 supergrid (1/12 degree)",
            "domain": f"{LON_START}-{LON_END}E, {LAT_START}-{LAT_END}N",
            "NIGLOBAL": NIGLOBAL,
            "NJGLOBAL": NJGLOBAL,
        },
    )

    ds.x.attrs = {"units": "degrees_east"}
    ds.y.attrs = {"units": "degrees_north"}
    ds.dx.attrs = {"units": "meters"}
    ds.dy.attrs = {"units": "meters"}
    ds.area.attrs = {"units": "m2"}
    ds.angle_dx.attrs = {"units": "degrees"}

    outfile = os.path.join(OUTPUT_DIR, "ocean_hgrid.nc")
    ds.to_netcdf(outfile)
    print(f"[OK] {outfile}")
    return ds


def create_topography(hgrid):
    """GEBCO에서 ocean_topog.nc 생성"""
    print(f"GEBCO 읽기: {GEBCO_FILE}")
    gebco = xr.open_dataset(GEBCO_FILE)

    # GEBCO 변수명 확인 (elevation 또는 Band1)
    if "elevation" in gebco:
        elev = gebco["elevation"]
    elif "Band1" in gebco:
        elev = gebco["Band1"]
    else:
        varname = list(gebco.data_vars)[0]
        print(f"  GEBCO 변수: {varname}")
        elev = gebco[varname]

    # T-cell 중심 좌표 추출 (supergrid에서 홀수 인덱스)
    x_t = hgrid["x"].values[1::2, 1::2]  # (NJGLOBAL, NIGLOBAL)
    y_t = hgrid["y"].values[1::2, 1::2]

    print(f"T-cell 격자: {x_t.shape}")
    print(f"  경도: {x_t.min():.2f} ~ {x_t.max():.2f}")
    print(f"  위도: {y_t.min():.2f} ~ {y_t.max():.2f}")

    # GEBCO 좌표
    gebco_lon = gebco["lon"].values if "lon" in gebco else gebco["x"].values
    gebco_lat = gebco["lat"].values if "lat" in gebco else gebco["y"].values

    # scipy RegularGridInterpolator로 내삽
    print("GEBCO → 모델 격자 내삽 중...")
    interp = RegularGridInterpolator(
        (gebco_lat, gebco_lon),
        elev.values,
        method="linear",
        bounds_error=False,
        fill_value=0.0,
    )

    points = np.column_stack([y_t.ravel(), x_t.ravel()])
    depth_interp = interp(points).reshape(x_t.shape)

    # GEBCO: 양수=육지, 음수=바다 → MOM6: depth는 양수
    depth = -depth_interp
    depth = np.maximum(depth, 0.0)  # 육지는 0

    # 최소 수심 설정 (너무 얕은 곳 제거)
    MIN_DEPTH = 10.0
    depth[(depth > 0) & (depth < MIN_DEPTH)] = 0.0

    # ntiles 차원 추가 (make_solo_mosaic 호환)
    ds = xr.Dataset(
        {
            "depth": (["ny", "nx"], depth),
            "ntiles": (["ntiles"], [1]),
        },
        attrs={
            "title": "EA12 ocean topography from GEBCO 2024",
            "source": GEBCO_FILE,
            "min_depth": f"{MIN_DEPTH} m",
        },
    )
    ds.depth.attrs = {"units": "meters", "standard_name": "topographic_depth"}

    outfile = os.path.join(OUTPUT_DIR, "ocean_topog.nc")
    ds.to_netcdf(outfile)
    print(f"[OK] {outfile}")

    # 통계
    ocean_frac = np.sum(depth > 0) / depth.size * 100
    print(f"  최대 수심: {depth.max():.0f} m")
    print(f"  해양 비율: {ocean_frac:.1f}%")

    return ds


def create_mosaic():
    """ocean_mosaic.nc 생성 (Python으로 FRE-NCtools 대체)"""
    ds = xr.Dataset(
        {
            "mosaic": ([], "ocean_mosaic"),
            "gridlocation": ([], "T"),
            "gridfiles": (["ntiles"], ["ocean_hgrid.nc"]),
            "gridtiles": (["ntiles"], ["tile1"]),
        },
        attrs={"title": "EA12 ocean mosaic"},
    )

    outfile = os.path.join(OUTPUT_DIR, "ocean_mosaic.nc")
    ds.to_netcdf(outfile)
    print(f"[OK] {outfile}")


def create_grid_spec():
    """grid_spec.nc 생성 (단순 버전)"""
    ds = xr.Dataset(
        {
            "atm_mosaic": ([], "ocean_mosaic"),
            "lnd_mosaic": ([], "ocean_mosaic"),
            "ocn_mosaic": ([], "ocean_mosaic"),
            "ocn_mosaic_file": ([], "ocean_mosaic.nc"),
            "ocn_topog_file": ([], "ocean_topog.nc"),
            "atm_mosaic_file": ([], "ocean_mosaic.nc"),
            "lnd_mosaic_file": ([], "ocean_mosaic.nc"),
        },
        attrs={"title": "EA12 grid specification"},
    )

    outfile = os.path.join(OUTPUT_DIR, "grid_spec.nc")
    ds.to_netcdf(outfile)
    print(f"[OK] {outfile}")


def main():
    print("=" * 50)
    print(" EA12 격자 생성")
    print(f" 도메인: {LON_START}-{LON_END}°E, {LAT_START}-{LAT_END}°N")
    print(f" 해상도: 1/{int(1/RESOLUTION)}°")
    print("=" * 50)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(GEBCO_FILE):
        print(f"ERROR: {GEBCO_FILE} 파일이 없습니다.")
        print("먼저 GEBCO 데이터를 다운로드하세요.")
        return

    # 1. Supergrid 생성
    print("\n--- Step 1: Supergrid (ocean_hgrid.nc) ---")
    hgrid = create_supergrid()

    # 2. 해저지형 생성
    print("\n--- Step 2: Topography (ocean_topog.nc) ---")
    create_topography(hgrid)

    # 3. 모자이크 생성
    print("\n--- Step 3: Mosaic (ocean_mosaic.nc) ---")
    create_mosaic()

    # 4. Grid spec 생성
    print("\n--- Step 4: Grid spec (grid_spec.nc) ---")
    create_grid_spec()

    print("\n" + "=" * 50)
    print(" 완료! 생성된 파일:")
    print(f"   {OUTPUT_DIR}/ocean_hgrid.nc")
    print(f"   {OUTPUT_DIR}/ocean_topog.nc")
    print(f"   {OUTPUT_DIR}/ocean_mosaic.nc")
    print(f"   {OUTPUT_DIR}/grid_spec.nc")
    print()
    print(" 다음 단계:")
    print("   1. ncdump -h ocean_hgrid.nc 로 차원 확인")
    print("   2. Python으로 depth 시각화하여 해안선 확인")
    print("   3. vgrid_75_2m.nc 복사")
    print("=" * 50)


if __name__ == "__main__":
    main()
