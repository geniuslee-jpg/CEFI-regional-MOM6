#!/usr/bin/env python3
"""
동아시아(EA12) ERA5 데이터 다운로드 스크립트

사전 준비:
  1. ECMWF CDS 계정 생성: https://cds.climate.copernicus.eu/
  2. API key 발급 후 ~/.cdsapirc 파일 생성:
     url: https://cds.climate.copernicus.eu/api
     key: YOUR_API_KEY
  3. 설치: pip install cdsapi

사용법:
  python get_era5_ea12.py --year 2019 --month 1
  python get_era5_ea12.py --year 2019  # 전체 연도
"""

import argparse
import os

try:
    import cdsapi
except ImportError:
    print("Error: cdsapi가 설치되지 않았습니다.")
    print("설치: pip install cdsapi")
    print("CDS 계정: https://cds.climate.copernicus.eu/")
    exit(1)


# 동아시아 도메인 (North/West/South/East)
# GLORYS 도메인보다 약간 넓게 잡음 (대기 강제력은 넓은 영역 필요)
AREA = [55, 100, 10, 165]  # N, W, S, E

# 기본 저장 경로
DEFAULT_OUTDIR = "/data01/labdisk/sungjin/MOM6-COBALT/datasets/era5/EA12"

# ERA5 변수 매핑 (MOM6에 필요한 변수들)
VARIABLES = {
    "t2m": {
        "era5_name": "2m_temperature",
        "description": "2m 기온",
    },
    "u10": {
        "era5_name": "10m_u_component_of_wind",
        "description": "10m u-바람",
    },
    "v10": {
        "era5_name": "10m_v_component_of_wind",
        "description": "10m v-바람",
    },
    "msl": {
        "era5_name": "mean_sea_level_pressure",
        "description": "해면기압",
    },
    "sp": {
        "era5_name": "surface_pressure",
        "description": "지표기압 (비습 계산용)",
    },
    "d2m": {
        "era5_name": "2m_dewpoint_temperature",
        "description": "이슬점 온도 (비습 계산용)",
    },
    "ssrd": {
        "era5_name": "surface_solar_radiation_downwards",
        "description": "단파복사",
    },
    "strd": {
        "era5_name": "surface_thermal_radiation_downwards",
        "description": "장파복사",
    },
    "tp": {
        "era5_name": "total_precipitation",
        "description": "총 강수량",
    },
    "sf": {
        "era5_name": "snowfall",
        "description": "강설량",
    },
}


def download_era5(year, month, outdir):
    """단일 변수, 단일 월의 ERA5 데이터 다운로드"""
    c = cdsapi.Client()

    months = [month] if month else list(range(1, 13))

    for m in months:
        for short_name, info in VARIABLES.items():
            outfile = os.path.join(
                outdir, f"ERA5_{short_name}_{year}_{m:02d}.nc"
            )

            if os.path.exists(outfile):
                print(f"[SKIP] {outfile} 이미 존재")
                continue

            print(f"[DOWN] {info['description']} ({short_name}) - {year}/{m:02d}")

            c.retrieve(
                "reanalysis-era5-single-levels",
                {
                    "product_type": "reanalysis",
                    "variable": info["era5_name"],
                    "year": str(year),
                    "month": f"{m:02d}",
                    "day": [f"{d:02d}" for d in range(1, 32)],
                    "time": [f"{h:02d}:00" for h in range(24)],
                    "area": AREA,
                    "data_format": "netcdf",
                },
                outfile,
            )
            print(f"[OK] {outfile}")


def main():
    parser = argparse.ArgumentParser(
        description="동아시아(EA12) ERA5 데이터 다운로드"
    )
    parser.add_argument("--year", type=int, required=True, help="다운로드 연도")
    parser.add_argument(
        "--month", type=int, default=None, help="다운로드 월 (생략하면 전체 연도)"
    )
    parser.add_argument("--outdir", type=str, default=DEFAULT_OUTDIR, help="저장 경로")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    print("============================================")
    print(" EA12 ERA5 다운로드")
    print(f" 영역: {AREA} (N/W/S/E)")
    print(f" 기간: {args.year}/{args.month or '전체'}")
    print(f" 저장: {args.outdir}")
    print("============================================")

    download_era5(args.year, args.month, args.outdir)

    print()
    print("============================================")
    print(" 다운로드 완료!")
    print()
    print(" 후처리 필요:")
    print(" 1) 비습 계산: python era5_sphum.py  (sp + d2m → sphum)")
    print(" 2) 액체강수:  cdo -setrtoc,-1e9,0,0 -chname,tp,lp \\")
    print("               -sub ERA5_tp_*.nc ERA5_sf_*.nc ERA5_lp_*.nc")
    print(" 3) 패딩:      연말에 다음해 1월1일 0시 데이터 추가")
    print("============================================")


if __name__ == "__main__":
    main()
