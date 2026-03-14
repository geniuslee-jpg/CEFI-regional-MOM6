# 동아시아(EA12) MOM6-COBALT 모델 셋업 가이드

**작성일:** 2026-03-14
**작업 서버:** bjerknes00 (`/data01/labdisk/sungjin/MOM6-COBALT`)
**참고 레포:** NOAA-GFDL/CEFI-regional-MOM6 (NWA12.COBALT 기반)

---

## 1. 개요

### 1.1 목표
- 동아시아 해역에서 MOM6(물리) + COBALT(생지화학) 결합 모델 실행
- 기간: 1993년 1년
- 참고: NWA12.COBALT (북서대서양) 설정을 동아시아(EA12)로 적응

### 1.2 도메인 정의
| 항목 | 값 |
|------|-----|
| 경도 | 105°E ~ 160°E |
| 위도 | 15°N ~ 52°N |
| 수평 해상도 | 1/12° (~8 km) |
| 격자 크기 | NIGLOBAL=660, NJGLOBAL=444 |
| 연직 층수 | 75층 (총 깊이 ~7,499 m) |
| 개방 경계 | 3면 (남, 북, 동) |

### 1.3 모델 구성 요소
- **MOM6**: 해양 물리 (온도, 염분, 유속, 해수면)
- **SIS2**: 해빙 모델
- **COBALT**: 해양 생지화학 (영양염, 엽록소, 탄소 순환 등)
- **실행 바이너리**: `/data01/labdisk/sungjin/COBART_TEST/CEFI-regional-MOM6/builds/build/mylinux-gnu/ocean_ice/repro/MOM6SIS2`

---

## 2. 디렉토리 구조

### 2.1 디렉토리 생성
스크립트: `tools/setup_ea12_dirs.sh`

```
/data01/labdisk/sungjin/MOM6-COBALT/
├── input/                          # 원본 다운로드 데이터
│   ├── bathymetry/                 # GEBCO 해저지형
│   ├── atmos/era5/                 # ERA5 대기강제력 원본
│   ├── ocean_ic_bc/glorys12/       # GLORYS12 재분석 데이터
│   ├── bgc_ic/woa23/              # WOA23 생지화학 데이터
│   ├── bgc_ic/glodap/             # GLODAPv2 (선택)
│   ├── deposition/esm4/           # ESM4 대기침적
│   ├── tidal/                     # TPXO 조석 (선택)
│   ├── rivers/glofas/             # GloFAS 하천유출 (선택)
│   ├── co2/                       # CO2 농도 원본
│   └── opacity/                   # SeaWiFS 엽록소 원본
├── exps/EA12.COBALT/              # 실험 디렉토리
│   ├── INPUT/                     # MOM6가 읽는 전처리 완료 파일
│   └── RESTART/                   # 재시작 파일 출력
├── tools/                         # 전처리 도구
│   ├── grid/                      # 격자 생성
│   ├── initial/                   # 초기조건 생성
│   ├── boundary/                  # 경계조건 생성
│   ├── atmos/                     # 대기강제력 처리
│   ├── rivers/                    # 하천유출 처리
│   └── sponge/                    # 스펀지층
└── cefi_ref/CEFI-regional-MOM6/   # 참고용 클론 레포
```

### 2.2 중복 디렉토리 정리
초기 setup 스크립트에서 `exps/exps/`, `exps/input/`, `exps/tools/` 등 중복 디렉토리가 생성됨.
스크립트: `tools/cleanup_ea12_dirs.sh`로 정리.

---

## 3. 데이터 다운로드

### 3.1 GEBCO 해저지형 (완료)
- **출처**: https://download.gebco.net/ (무료, 계정 불필요)
- **영역**: 105°E~160°E, 15°N~52°N
- **파일**: `input/bathymetry/GEBCO_EA12.nc`
- **방법**: GEBCO 웹사이트에서 영역 지정 후 NetCDF 다운로드
- **후처리**: 전체 GEBCO에서 xarray로 영역 추출 (ncks 라이브러리 오류로 Python 사용)

```python
import xarray as xr
gebco = xr.open_dataset('GEBCO_2024.nc')
ea12 = gebco.sel(lon=slice(105, 160), lat=slice(15, 52))
ea12.to_netcdf('GEBCO_EA12.nc')
```

### 3.2 GLORYS12 재분석 데이터 (다운로드 중)
- **출처**: Copernicus Marine Service (무료 계정 필요)
- **데이터셋**: `cmems_mod_glo_phy_my_0.083deg_P1D-m`
- **변수**: thetao, so, uo, vo, zos
- **파일**:
  - `glorys12_EAS_1993.nc` (원본, 98~147°E) — 완료
  - `glorys12_EAS_wide_1993.nc` (확장, 100~165°E) — 다운로드 중

**원본 다운로드 (98~147°E):**
```bash
copernicusmarine subset \
  -i cmems_mod_glo_phy_my_0.083deg_P1D-m \
  -v thetao -v so -v uo -v vo -v zos \
  -x 98 -X 147 -y 13 -Y 57 \
  -t 1993-01-01 -T 1993-12-31 \
  -o input/ocean_ic_bc/glorys12 -f glorys12_EAS_1993.nc
```

**확장 다운로드 (100~165°E) — 동쪽 경계(160°E) 커버:**
동쪽 경계 OBC 생성 시 GLORYS 데이터가 147°E까지만 있어서 160°E를 커버하지 못하는 문제 발생.
해결: 더 넓은 영역으로 재다운로드.

```bash
nohup copernicusmarine subset \
  -i cmems_mod_glo_phy_my_0.083deg_P1D-m \
  -v thetao -v so -v uo -v vo -v zos \
  -x 100 -X 165 -y 10 -Y 55 \
  -t 1993-01-01 -T 1993-12-31 \
  --force-download \
  -o input/ocean_ic_bc/glorys12 -f glorys12_EAS_wide_1993.nc \
  > glorys_download.log 2>&1 &
```

### 3.3 WOA23 (World Ocean Atlas 2023) (완료)
- **출처**: NOAA NCEI (무료)
- **변수**: NO3(n_an), O2(o_an), PO4(p_an), SiO4(i_an)
- **파일**: `input/bgc_ic/woa23/` 디렉토리에 연간 기후값

### 3.4 ERA5 대기강제력 (다운로드 중)
- **출처**: ECMWF CDS (무료 계정 필요, 라이선스 동의 필요)
- **변수**: 10개 (t2m, u10, v10, msl, sp, d2m, ssrd, strd, tp, sf)
- **기간**: 1993년 1~12월 (120개 파일)
- **스크립트**: `tools/atmos/get_era5_ea12.py`

```bash
pip install cdsapi
# ~/.cdsapirc에 API 키 설정 필요
# CDS 웹사이트에서 라이선스 동의 필요 (403 에러 해결)
python tools/atmos/get_era5_ea12.py
```

**주의사항:**
- 최초 실행 시 `403 Forbidden` 에러 발생 → CDS 웹사이트에서 라이선스 동의 필요
- `conda install cdsapi` 또는 `pip install cdsapi`로 설치

### 3.5 NWA12 데이터셋 (다운로드 중)
- **출처**: GFDL FTP
- **내용**: ESM4 대기침적 8개 + CO2 + SeaWiFS + 기타 (51GB)
- **파일**: `input/nwa12_datasets.tar.gz`

```bash
cd /data01/labdisk/sungjin/MOM6-COBALT/input
nohup wget ftp://ftp.gfdl.noaa.gov/pub/Yi-cheng.Teng/nwa12_datasets.tar.gz > nwa12_download.log 2>&1 &
```

**포함 데이터:**
- esm4_dryfe/wetfe/drydust/wetdust/drynoy/wetnoy/drynh4/wetnh4_climo_1993-2014.nc
- mole_fraction_of_co2_extended_ssp245.nc
- seawifs-clim-1997-2010.nwa12.nc
- 기타 NWA12 격자/경계/초기조건 파일

### 3.6 SeaWiFS 엽록소 기후값 (완료)
- **출처**: UCAR SVN (무료)
- **파일**: `input/opacity/seawifs-clim-1997-2010.1440x1080.v20180328.nc` (112MB)

```bash
cd input/opacity
svn export https://svn-ccsm-inputdata.cgd.ucar.edu/trunk/inputdata/ocn/mom/tx0.25v1/seawifs-clim-1997-2010.1440x1080.v20180328.nc
```

### 3.7 CO2 농도 (input4MIPs)
- **출처**: ESGF input4MIPs (또는 NWA12 데이터셋에 포함)
- 2개 파일 필요: Historical(~2014) + SSP2-4.5(2015~)
- NWA12 데이터셋 다운로드 완료 시 이미 병합된 파일 포함

---

## 4. 격자 생성

### 4.1 개요
스크립트: `tools/grid/create_ea12_grid.py`
Python으로 FRE-NCtools를 대체하여 격자 파일 생성.

### 4.2 생성 파일
| 파일 | 설명 | 차원 |
|------|------|------|
| ocean_hgrid.nc | Supergrid (2배 해상도) | nyp=889, nxp=1321 |
| ocean_topog.nc | 해저지형 (GEBCO에서 내삽) | ny=444, nx=660 |
| ocean_mosaic.nc | 모자이크 메타데이터 | — |
| grid_spec.nc | 격자 사양 | — |

### 4.3 실행
```bash
cd /data01/labdisk/sungjin/MOM6-COBALT
python tools/grid/create_ea12_grid.py
```

### 4.4 Supergrid 생성 로직
- 1/12° 등간격 lon/lat 격자
- Supergrid은 모델 격자의 2배 해상도 (1/24° 간격)
- `dx`: 경도 방향 거리 (위도에 따라 변함, R·cos(lat)·dlon)
- `dy`: 위도 방향 거리 (일정, R·dlat)
- `angle_dx`: 등간격 lon/lat이므로 0도

### 4.5 해저지형 생성 로직
- GEBCO elevation → scipy.interpolate.RegularGridInterpolator로 모델 격자에 내삽
- GEBCO 부호 변환: 양수(육지)/음수(바다) → MOM6 depth는 양수
- 최소 수심: 10m 미만은 0(육지)으로 설정
- 결과: 최대 수심 9,782m, 해양 비율 63.2%

### 4.6 연직 격자
- 파일: `vgrid_75_2m.nc` (75층, 총 깊이 ~7,499m)
- NWA12와 동일한 연직 좌표 사용
- Python으로 직접 생성 (dz 배열에서)

### 4.7 검증
- `ncdump -h ocean_hgrid.nc`로 차원 확인 (nyp=889, nxp=1321)
- Python으로 depth 시각화하여 해안선 올바른지 확인
- 경도/위도 범위가 105~160°E, 15~52°N 커버하는지 확인

---

## 5. 초기조건 생성

### 5.1 물리 초기조건 (MOM.res.nc)
스크립트: `tools/initial/write_ea12_initial.py`

**입력:** `glorys12_EAS_1993.nc` (GLORYS12, 1993년 1월 1일)
**출력:** `exps/EA12.COBALT/INPUT/MOM.res.nc`

**처리 과정:**
1. GLORYS 1월 1일 데이터 추출
2. 수평 내삽: nearest-neighbor (scipy)
3. 연직 내삽: GLORYS 50층 → 모델 75층 (선형 보간 + 최심부 외삽)
4. 육지 NaN 처리: flood-fill
5. 변수명 변환: thetao→Temp, so→Salt, zos→ssh, uo→u, vo→v
6. 층 두께(h) 계산

**결과:**
- Temp: -1.91 ~ 27.61°C
- Salt: 0 ~ 35.43 PSU

**참고:** GLORYS wide 다운로드 완료 후 재생성 필요 (현재 147~160°E 구간 외삽)

### 5.2 BGC 초기조건 (bgc_woa_ics_1993.nc)
스크립트: `tools/initial/write_ea12_bgc_initial.py`

**입력:** WOA23 연간 기후값 (NO3, O2, PO4, SiO4)
**출력:** `exps/EA12.COBALT/INPUT/bgc_woa_ics_1993.nc`

**처리 과정:**
1. WOA23 파일 읽기 (`decode_times=False` 필요 — "months since" 시간 단위 문제)
2. 육지 flood-fill
3. 모델 격자에 nearest-neighbor 내삽
4. 연직 102층 → 75층 내삽

**참고:** DIC/ALK는 ESPER 데이터 필요 (아직 미완)

---

## 6. 경계조건(OBC) 생성

### 6.1 개요
스크립트: `tools/boundary/write_ea12_obc.py` + `ea12_obc.yaml`

기존 `write_glorys_boundary.py`에서 변경:
1. GLORYS 파일 형식: 월별 → 연간 통합 파일
2. YAML에 `glorys_pattern` 추가
3. ncrcat 기본 비활성화

### 6.2 세그먼트 정의
| 세그먼트 | 경계 | MOM6 정의 |
|----------|------|-----------|
| 001 (South) | 15°N | J=0, I=0:N |
| 002 (North) | 52°N | J=N, I=N:0 |
| 003 (East) | 160°E | I=N, J=0:N |

### 6.3 출력 파일 (12개)
각 세그먼트 × 4개 변수:
- `uv_001.nc`, `uv_002.nc`, `uv_003.nc`
- `thetao_001.nc`, `thetao_002.nc`, `thetao_003.nc`
- `so_001.nc`, `so_002.nc`, `so_003.nc`
- `zos_001.nc`, `zos_002.nc`, `zos_003.nc`

### 6.4 실행 (GLORYS wide 다운로드 완료 후)
```bash
cd /data01/labdisk/sungjin/MOM6-COBALT
PYTHONPATH=cefi_ref/CEFI-regional-MOM6/tools/boundary \
  python tools/boundary/write_ea12_obc.py --config tools/boundary/ea12_obc.yaml
```

### 6.5 의존성
- `xesmf`: 수평 내삽 (`conda install -c conda-forge xesmf`)
- `boundary.py`: CEFI 레포의 Segment 클래스 (변경 불필요)

---

## 7. 설정 파일

### 7.1 MOM_input
- 위치: `exps/EA12.COBALT/INPUT/MOM_input`
- NWA12.COBALT에서 EA12로 수정
- 주요 변경: NIGLOBAL=660, NJGLOBAL=444, NK=75
- DT=600s, DT_THERM=1800s, MAXIMUM_DEPTH=9800m
- OBC 3개 세그먼트 정의
- TIDES=False (조석 비활성화)
- USE_generic_tracer=True (COBALT 활성화)

### 7.2 MOM_override
```
#override USE_generic_tracer = True
#override GENERIC_TRACER_IC_FILE = ""
#override RESTART_CHECKSUMS_REQUIRED = False
#override TRACERS_MAY_REINIT = True
DT_OBC_SEG_UPDATE_OBGC = 1800
```

### 7.3 MOM_layout
```
#override LAYOUT = 10,10
#override IO_LAYOUT = 1,1
```

### 7.4 SIS_input
- 해빙 모델 설정
- NIGLOBAL=660, NJGLOBAL=444

### 7.5 COBALT_input / COBALT_override
- NWA12.COBALT에서 복사

### 7.6 data_table
- ERA5 대기강제력 매핑 (9개 변수)
- ESM4 대기침적 매핑 (8개 변수)
- CO2 농도 매핑
- 하천 runoff = 0.0 (GloFAS 없음)
- 하천 영양염 제거 (NWA12 전용 파일 없음)

### 7.7 input.nml
- cold start (`input_filename = 'n'`)
- current_date = 1993,1,1,0,0,0
- days = 2 (테스트용 2일)

### 7.8 field_table
- NWA12.COBALT에서 복사
- COBALT 트레이서 OBC 정의

### 7.9 MOM_mask_table
- 현재 NWA12 것 사용 중 → EA12용 재생성 필요

---

## 8. COBALT 강제 데이터

### 8.1 ESM4 대기침적 (8개 파일)
NWA12 데이터셋(51GB)에서 확보.
전구 기후값이므로 EA12에 그대로 사용 가능.

| 파일 | 변수 | 설명 |
|------|------|------|
| esm4_dryfe_climo_1993-2014.nc | dryfe | 건성 철 침적 |
| esm4_wetfe_climo_1993-2014.nc | wetfe | 습성 철 침적 |
| esm4_drydust_climo_1993-2014.nc | drydust | 건성 먼지 침적 |
| esm4_wetdust_climo_1993-2014.nc | wetdust | 습성 먼지 침적 |
| esm4_drynoy_climo_1993-2014.nc | drynoy | 건성 NOy 침적 |
| esm4_wetnoy_climo_1993-2014.nc | wetnoy | 습성 NOy 침적 |
| esm4_drynh4_climo_1993-2014.nc | drynh4 | 건성 NH4 침적 |
| esm4_wetnh4_climo_1993-2014.nc | wetnh4 | 습성 NH4 침적 |

### 8.2 CO2 농도
- 파일: `mole_fraction_of_co2_extended_ssp245.nc`
- Historical(~2014) + SSP2-4.5(2015~) 병합
- NWA12 데이터셋에 포함 또는 `merge_co2_forcing.py`로 생성

### 8.3 SeaWiFS 엽록소 기후값
- 원본: `seawifs-clim-1997-2010.1440x1080.v20180328.nc` (UCAR SVN에서 다운로드 완료)
- EA12 격자로 regrid 필요 (`regrid_opacity.py` 수정)

---

## 9. 남은 전처리 작업

| # | 작업 | 상태 | 입력 | 출력 |
|---|------|------|------|------|
| 1 | OBC 생성 | GLORYS 대기 중 | GLORYS wide | uv/thetao/so/zos_001~003.nc |
| 2 | ERA5 후처리 | ERA5 대기 중 | ERA5 월별 | 연간 padded 9개 파일 |
| 3 | CO2 생성 | NWA12 대기 중 | input4MIPs 또는 NWA12 | mole_fraction_of_co2.nc |
| 4 | SeaWiFS regrid | 원본 다운 완료 | 전구 SeaWiFS | seawifs-clim.ea12.nc |
| 5 | MOM.res.nc 재생성 | GLORYS 대기 중 | GLORYS wide | MOM.res.nc |
| 6 | MOM_mask_table | 미착수 | EA12 격자 | mask_table |

---

## 10. 모델 실행

### 10.1 실행 명령
```bash
cd /data01/labdisk/sungjin/MOM6-COBALT/exps/EA12.COBALT
mpirun -np 100 /data01/labdisk/sungjin/COBART_TEST/CEFI-regional-MOM6/builds/build/mylinux-gnu/ocean_ice/repro/MOM6SIS2
```
- `-np 100`: LAYOUT=10,10 (10×10=100 프로세스)

### 10.2 테스트 실행
- `input.nml`에서 `days = 2`로 설정하여 2일 테스트
- 물리만 테스트: `MOM_override`에서 `USE_generic_tracer = False`

### 10.3 exps/EA12.COBALT/INPUT/ 최종 파일 목록
```
[격자/지형]
  ocean_hgrid.nc, ocean_topog.nc, ocean_mosaic.nc, grid_spec.nc, vgrid_75_2m.nc

[초기조건]
  MOM.res.nc, bgc_woa_ics_1993.nc

[경계조건 - 물리]
  uv_001~003.nc, thetao_001~003.nc, so_001~003.nc, zos_001~003.nc

[대기강제력 - ERA5]
  ERA5_t2m/u10/v10/msl/sphum/ssrd/strd/lp/sf_1993_padded.nc

[BGC 강제력]
  esm4_dryfe/wetfe/drydust/wetdust/drynoy/wetnoy/drynh4/wetnh4_climo_1993-2014.nc
  mole_fraction_of_co2_extended_ssp245.nc
  seawifs-clim-1997-2010.ea12.nc

[설정파일]
  MOM_input, MOM_override, MOM_layout, MOM_mask_table
  SIS_input, SIS_layout, SIS_override
  COBALT_input, COBALT_override
  field_table, data_table, diag_table, input.nml
```

---

## 11. 트러블슈팅 기록

### 11.1 GEBCO ncks 라이브러리 오류
- **문제**: `libnco-5.3.4.so` not found
- **해결**: ncks 대신 Python xarray로 영역 추출

### 11.2 ERA5 403 Forbidden
- **문제**: CDS API 라이선스 미동의
- **해결**: CDS 웹사이트에서 라이선스 동의 후 재실행

### 11.3 WOA23 시간 디코딩 오류
- **문제**: `ValueError: unable to decode time units 'months since 1965-01-01'`
- **해결**: `xr.open_dataset(..., decode_times=False)` 추가

### 11.4 GLORYS 커버리지 부족
- **문제**: 원본 GLORYS가 98~147°E로 동쪽 경계(160°E) 미커버
- **해결**: 100~165°E로 확장하여 재다운로드

### 11.5 COBALT 데이터 심볼릭 링크 깨짐
- **문제**: CEFI 레포의 ESM4/CO2/SeaWiFS가 `datasets/` 심볼릭 링크 → 실제 데이터 없음
- **해결**: NWA12 데이터셋(51GB) FTP 다운로드

---

## 12. 참고 자료

- CEFI-regional-MOM6: https://github.com/NOAA-GFDL/CEFI-regional-MOM6
- CEFI 사용자 가이드: https://cefi-regional-mom6.readthedocs.io/
- Copernicus Marine: https://marine.copernicus.eu/
- ECMWF CDS: https://cds.climate.copernicus.eu/
- GEBCO: https://download.gebco.net/
- NASA OceanColor: https://oceandata.sci.gsfc.nasa.gov/
- ESGF input4MIPs: https://esgf-node.llnl.gov/search/input4mips/
- NWA12 데이터셋: `wget ftp://ftp.gfdl.noaa.gov/pub/Yi-cheng.Teng/nwa12_datasets.tar.gz`
