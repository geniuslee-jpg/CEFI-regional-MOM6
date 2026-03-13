# 동아시아(EA12) MOM6 셋업 실행 가이드

> 기존 NWA12.COBALT 설정을 기반으로 동아시아 도메인을 구축하는 단계별 절차

---

## 전제 조건

- HPC 환경 (Gaea, AWS, GCP 등) 또는 64GB+ 메모리 서버
- Copernicus Marine Service 계정 (GLORYS 다운로드용)
- ECMWF CDS 계정 (ERA5 다운로드용)

---

## 1단계: 실험 디렉토리 생성

NWA12.COBALT 구조를 복제하여 동아시아 실험 디렉토리를 만듭니다.

```bash
cd CEFI-regional-MOM6/exps
mkdir -p EA12.COBALT/INPUT
mkdir -p EA12.COBALT/RESTART

# NWA12에서 설정 파일 템플릿 복사
cp NWA12.COBALT/input.nml_24hr       EA12.COBALT/
cp NWA12.COBALT/input.nml_48hr       EA12.COBALT/
cp NWA12.COBALT/data_table            EA12.COBALT/
cp NWA12.COBALT/diag_table            EA12.COBALT/
cp NWA12.COBALT/field_table           EA12.COBALT/
cp NWA12.COBALT/execrunscript.sh      EA12.COBALT/
cp NWA12.COBALT/INPUT/MOM_input       EA12.COBALT/INPUT/
cp NWA12.COBALT/INPUT/MOM_override    EA12.COBALT/INPUT/
cp NWA12.COBALT/INPUT/SIS_input       EA12.COBALT/INPUT/
cp NWA12.COBALT/INPUT/SIS_override    EA12.COBALT/INPUT/
cp NWA12.COBALT/INPUT/COBALT_input    EA12.COBALT/INPUT/
cp NWA12.COBALT/INPUT/COBALT_override EA12.COBALT/INPUT/
```

---

## 2단계: 도메인 정의 및 그리드 생성

### 2-1. 도메인 범위 결정

```
경도: 105°E ~ 160°E
위도:  15°N ~  52°N
해상도: 1/12° (~8km)
격자: NIGLOBAL=660, NJGLOBAL=444
```

### 2-2. ocean_hgrid.nc (수평 그리드) 생성

ESMG Gridtools 또는 COSIMA regional-mom6 도구를 사용합니다.

```python
# 예시: COSIMA regional-mom6 gridtools 사용
# pip install regional-mom6
from regional_mom6 import experiment

ea_expt = experiment(
    longitude_extent=[105, 160],
    latitude_extent=[15, 52],
    resolution=1/12,
    vlayers=75,
    ...
)
```

또는 직접 supergrid를 생성:
- 참고: https://github.com/jsimkins2/nwa25/blob/main/misc/gridgen/nwa12_grid_generation.ipynb

### 2-3. ocean_topog.nc (해저지형) 생성

GEBCO 또는 ETOPO 데이터에서 동아시아 영역 추출:

```python
import xarray as xr

gebco = xr.open_dataset('GEBCO_2023.nc')
ea_topo = gebco.sel(lon=slice(105, 160), lat=slice(15, 52))
ea_topo.to_netcdf('ocean_topog.nc')
```

### 2-4. 모자이크/마스크 파일 생성

```bash
# tools/grid/make_mosaic.sh 참고
ncap2 -s 'defdim("ntiles", 1);ntiles[ntiles]=1' ocean_topog.nc -O ocean_topog.nc
make_solo_mosaic --num_tiles 1 --dir . --mosaic_name ocean_mosaic --tile_file ocean_hgrid.nc
make_quick_mosaic --input_mosaic ocean_mosaic.nc --mosaic_name grid_spec --ocean_topog ocean_topog.nc
```

출력 파일:
- `ocean_hgrid.nc` → `EA12.COBALT/INPUT/`
- `ocean_topog.nc` → `EA12.COBALT/INPUT/`
- `ocean_mosaic.nc` → `EA12.COBALT/INPUT/`
- `ocean_mask.nc` → `EA12.COBALT/INPUT/`
- `land_mask.nc` → `EA12.COBALT/INPUT/`
- `grid_spec.nc` → `EA12.COBALT/INPUT/`

---

## 3단계: Python 환경 설정

```bash
mamba create -n ea12_setup python=3.10
mamba activate ea12_setup
mamba install -c conda-forge xarray dask netCDF4 h5py bottleneck matplotlib \
    scipy pandas PyYAML cartopy xskillscore utide gsw colorcet cmcrameri xesmf
pip3 install git+https://github.com/raphaeldussin/HCtFlood.git

# Copernicus Marine Service 도구 (별도 환경 권장)
conda env create --file tools/initial/copernicusmarine-env.yml
```

---

## 4단계: GLORYS 데이터 다운로드

`tools/initial/get_glorys_data.sh` 스크립트의 좌표를 동아시아로 변경:

```bash
conda activate cmc
cd tools/initial

# 동아시아 영역 GLORYS 다운로드 (예: 1993년)
./get_glorys_data.sh \
    -u YOUR_USERNAME \
    -p YOUR_PASSWORD \
    -o "../../datasets/glorys/daily" \
    -x 105 -X 160 \
    -y 15 -Y 52 \
    -s "1993-01-01" \
    -e "1993-12-31"
```

다운로드 변수: `thetao`, `so`, `uo`, `vo`, `zos` (온도, 염분, 유속, 해수면 높이)

---

## 5단계: 초기조건(IC) 생성

### 5-1. YAML 설정 파일 작성

`tools/initial/ea12_glorys_ic.yaml` 생성:

```yaml
glorys_file: ../../datasets/glorys/daily/GLORYS_REANALYSIS_1993-01-01.nc
vgrid_file: ../../datasets/grid/vgrid_75_2m.nc
grid_file: ../EA12.COBALT/INPUT/ocean_hgrid.nc
output_file: ../../exps/EA12.COBALT/INPUT/glorys_ic_1993-01-01.nc
reuse_weights: False

variable_names:
  temperature: thetao
  salinity: so
  sea_surface_height: zos
  zonal_velocity: uo
  meridional_velocity: vo
```

### 5-2. 실행

```bash
conda activate ea12_setup
cd tools/initial
./write_glorys_initial.py --config_file ea12_glorys_ic.yaml
```

### 5-3. BGC 초기조건

```bash
cd tools/initial
./write_bgc_initial.py --config_file ea12_bgc_ic.yaml
```

---

## 6단계: 경계조건(OBC) 생성

### 6-1. YAML 설정 파일 작성

`tools/boundary/ea12_glorys_obc.yaml` 생성:

```yaml
first_year: 1993
last_year: 1993
glorys_dir: '../../datasets/glorys/daily'
output_dir: './outputs'
hgrid: '../../exps/EA12.COBALT/INPUT/ocean_hgrid.nc'
ncrcat_years: true
ncrcat_names:
  - 'thetao'
  - 'so'
  - 'zos'
  - 'uv'
segments:
  - id: 1
    border: 'south'    # 남쪽 경계 (15°N)
  - id: 2
    border: 'north'    # 북쪽 경계 (52°N)
  - id: 3
    border: 'east'     # 동쪽 경계 (160°E)
variables:
  - 'thetao'
  - 'so'
  - 'zos'
  - 'uv'
```

### 6-2. 물리 경계조건 생성

```bash
cd tools/boundary
./write_glorys_boundary.py --config ea12_glorys_obc.yaml
```

출력 파일 → `EA12.COBALT/INPUT/` 으로 복사:
- `thetao_001.nc`, `thetao_002.nc`, `thetao_003.nc` (세그먼트 1,2,3)
- `so_001.nc`, `so_002.nc`, `so_003.nc`
- `zos_001.nc`, `zos_002.nc`, `zos_003.nc`
- `uv_001.nc`, `uv_002.nc`, `uv_003.nc`

### 6-3. 조석 경계조건

```bash
./write_tpxo_boundary.py --config ea12_tpxo_obc.yaml
```

출력: `tu_001.nc`, `tu_002.nc`, `tu_003.nc`, `tz_001.nc`, `tz_002.nc`, `tz_003.nc`

### 6-4. BGC 경계조건

```bash
./write_bgc_boundary.py --config ea12_bgc_obc.yaml
```

---

## 7단계: 대기 강제력 (ERA5) 준비

ERA5 데이터를 동아시아 영역으로 다운로드하고, NWA12 형식에 맞게 변환:

필요한 ERA5 변수:
| 파일명 패턴 | 변수 | 설명 |
|------------|------|------|
| `ERA5_t2m_1993_padded.nc` | t2m | 2m 기온 |
| `ERA5_u10_1993_padded.nc` | u10 | 10m u-바람 |
| `ERA5_v10_1993_padded.nc` | v10 | 10m v-바람 |
| `ERA5_msl_1993_padded.nc` | msl | 해면기압 |
| `ERA5_sphum_1993_padded.nc` | sphum | 비습 |
| `ERA5_ssrd_1993_padded.nc` | ssrd | 단파복사 |
| `ERA5_strd_1993_padded.nc` | strd | 장파복사 |
| `ERA5_lp_1993_padded.nc` | lp | 강수량 |
| `ERA5_sf_1993_padded.nc` | sf | 강설량 |

다운로드 후 → `EA12.COBALT/INPUT/` 으로 복사

---

## 8단계: 하천 유출(Runoff) 데이터 준비

### 8-1. GloFAS 유출량

`tools/rivers/ea12_runoff_glofas.yaml` 생성:

```yaml
grid_mask_file: '../../exps/EA12.COBALT/INPUT/ocean_mask.nc'
grid_mosaic_file: '../../exps/EA12.COBALT/INPUT/ocean_mosaic.nc'
hgrid_file: '../../exps/EA12.COBALT/INPUT/ocean_hgrid.nc'
ldd_file: '/path/to/GloFAS_3.1/ldd_glofas.nc'

output_dir: './outputs/'
start_year: 1993
end_year: 1993

glofas_files_pattern: '/path/to/glofas/GloFAS_river_discharge_{year}.nc'

latitude_range:
  start: 52
  end: 15
longitude_range:
  start: 105
  end: 160
```

```bash
cd tools/rivers
python write_runoff_glofas.py --config ea12_runoff_glofas.yaml
```

출력: `glofas_runoff_1993.nc` → `EA12.COBALT/INPUT/`

### 8-2. 하천 BGC (영양염) - 신규 구축 필요

기존 `tools/rivers/bgc/NWA/` 를 참고하여 `tools/rivers/bgc/EA/` 를 만들어야 합니다.
GlobalNEWS2 데이터셋에서 동아시아 하천(양쯔강, 황하, 한강, 낙동강, 메콩강 등) 추출.

출력: `RiverNutrients_EA12.nc` → `EA12.COBALT/INPUT/`

---

## 9단계: 기타 정적 입력 데이터 준비

NWA12에서 사용하는 글로벌/클리마톨로지 데이터를 동아시아 영역으로 재가공:

| 파일 | 원본 소스 | 처리 방법 |
|------|----------|-----------|
| `vgrid_75_2m.nc` | NWA12 것 그대로 사용 | 복사 |
| `seawifs-clim-*.nc` | SeaWIFS 글로벌 클리마톨로지 | 동아시아 영역 추출 + 그리드 보간 |
| `esm4_dry*.nc`, `esm4_wet*.nc` | ESM4 대기 침착 | 동아시아 영역 추출 |
| `mole_fraction_of_co2_*.nc` | 글로벌 CO2 농도 | 그대로 사용 가능 (시간 데이터) |
| `bgc_cobalt.nc`, `bgc_woa.nc` | COBALT/WOA 클리마톨로지 | 동아시아 그리드로 보간 |
| `esper_glorys_*.nc` | ESPER 데이터 | 동아시아 영역으로 재생성 |
| `diag_dz.nc` | 진단용 수직 레벨 | NWA12 것 그대로 사용 |

---

## 10단계: MOM_input 수정

`EA12.COBALT/INPUT/MOM_input` 핵심 수정 항목:

```fortran
! === 도메인 크기 ===
NIGLOBAL = 660                  ! x방향 격자수 (55° × 12)
NJGLOBAL = 444                  ! y방향 격자수 (37° × 12)
NK = 75                         ! 수직 75층

! === 경계 조건 ===
REENTRANT_X = False             ! 비주기적
REENTRANT_Y = False

! === 시간 간격 (NWA12와 동일하게 시작, 필요시 조정) ===
DT = 600.0                      ! 동역학 시간간격 (초)
DT_THERM = 1800.0               ! 열역학 시간간격 (초)

! === 수심 ===
MAXIMUM_DEPTH = 6500.0
MINIMUM_DEPTH = 9.5

! === OBC 세그먼트 수 ===
OBC_NUMBER_OF_SEGMENTS = 3      ! south, north, east

! === 그리드 파일 ===
GRID_CONFIG = "mosaic"
GRID_FILE = "ocean_hgrid.nc"
TOPO_CONFIG = "file"
TOPO_FILE = "ocean_topog.nc"
```

---

## 11단계: MOM_layout 설정

HPC 코어 수에 맞게 병렬 레이아웃 설정:

`EA12.COBALT/INPUT/MOM_layout`:
```fortran
! 예시: 660x444 도메인
! 총 프로세서 = LAYOUT_X * LAYOUT_Y
LAYOUT = 30, 20                 ! 600 프로세서
MASKTABLE = "mask_table"        ! 육지 영역 제외로 효율 향상
IO_LAYOUT = 1, 1
```

`EA12.COBALT/INPUT/SIS_layout`:
```fortran
LAYOUT = 30, 20
IO_LAYOUT = 1, 1
```

---

## 12단계: data_table 수정

`EA12.COBALT/data_table` 에서 파일 경로를 EA12 데이터로 변경:

```
"ATM", "p_surf",  "msl",   "INPUT/ERA5_msl_1993_padded.nc",    "bilinear", 1.0
"ATM", "t_bot",   "t2m",   "INPUT/ERA5_t2m_1993_padded.nc",    "bilinear", 1.0
...
"ICE", "runoff",  "runoff", "INPUT/glofas_runoff_1993.nc",      "none",     1.0
...
"OCN", "runoff_no3_flux_ice_ocn", "NO3_CONC", "./INPUT/RiverNutrients_EA12.nc", "none", 1.0e-3
...
```

---

## 13단계: input.nml 수정

`EA12.COBALT/input.nml`:
```fortran
&coupler_nml
    months = 0
    days   = 1                    ! 테스트: 1일
    current_date = 1993,1,1,0,0,0 ! 시작 날짜
    calendar = 'gregorian'
    dt_cpld  = 3600
    dt_atmos = 3600
    do_ice = .true.
    do_ocean = .true.
/
```

---

## 14단계: 빌드 (컴파일)

### 방법 A: HPC에서 직접 빌드

```bash
cd CEFI-regional-MOM6/builds
./linux-build.bash -m gaea -p ncrc5.intel23 -t repro -f mom6sis2
```

### 방법 B: Docker 이미지 빌드

```bash
cd ci/NWA
docker build -t cefi-mom6:ea12 .
```

빌드 결과물: `MOM6SIS2` 실행 파일 (어떤 지역이든 동일한 바이너리)

---

## 15단계: 테스트 실행

### HPC (Gaea) 에서 실행

`EA12.COBALT/run.sub` 작성:
```bash
#!/bin/bash
#SBATCH --nodes=5              # 660x444는 NWA12보다 작으므로 노드 수 감소
#SBATCH --time=30
#SBATCH --job-name="EA12_cobalt"
#SBATCH --account=YOUR_ACCOUNT

ntasks=600  # 30x20 레이아웃

ln -fs input.nml_24hr input.nml
pushd INPUT/
ln -fs MOM_layout MOM_layout
ln -fs MOM_layout SIS_layout
popd

srun --ntasks ${ntasks} --export=ALL \
    apptainer exec --writable-tmpfs $img \
    bash ./execrunscript.sh > out 2>err
```

```bash
sbatch run.sub
```

### Docker 에서 실행

```bash
docker run -v $(pwd)/exps/EA12.COBALT:/run cefi-mom6:ea12 \
    mpirun -np 600 MOM6SIS2
```

---

## 16단계: 검증

실행 완료 후 확인할 항목:

1. **ocean.stats** - 에너지/모멘텀 값이 발산하지 않는지 확인
2. **RESTART/** 폴더 - 재시작 파일 정상 생성 확인
3. **SST 검증** - 모델 SST vs GLORYS/위성 SST 비교
4. **해류 검증** - 쿠로시오, 대한해협 수송량 확인
5. **조석 검증** - 황해/동중국해 조석 진폭/위상 비교

---

## 전체 파일 체크리스트

`EA12.COBALT/INPUT/` 에 있어야 하는 파일들:

```
[ ] ocean_hgrid.nc              ← 2단계에서 생성
[ ] ocean_topog.nc              ← 2단계에서 생성
[ ] ocean_mosaic.nc             ← 2단계에서 생성
[ ] ocean_mask.nc               ← 2단계에서 생성
[ ] land_mask.nc                ← 2단계에서 생성
[ ] grid_spec.nc                ← 2단계에서 생성
[ ] atmos_mosaic_tile1Xland_mosaic_tile1.nc    ← 2단계
[ ] atmos_mosaic_tile1Xocean_mosaic_tile1.nc   ← 2단계
[ ] land_mosaic_tile1Xocean_mosaic_tile1.nc    ← 2단계
[ ] vgrid_75_2m.nc              ← NWA12에서 복사
[ ] diag_dz.nc                  ← NWA12에서 복사
[ ] MOM_input                   ← 10단계에서 수정
[ ] MOM_override                ← NWA12 참고 수정
[ ] MOM_layout                  ← 11단계에서 생성
[ ] SIS_input                   ← NWA12에서 복사
[ ] SIS_layout                  ← 11단계에서 생성
[ ] SIS_override                ← NWA12에서 복사
[ ] COBALT_input                ← NWA12에서 복사
[ ] COBALT_override             ← NWA12에서 복사
[ ] glorys_ic_1993-01-01.nc     ← 5단계에서 생성 (또는 MOM.res.nc)
[ ] thetao_001~003.nc           ← 6단계에서 생성
[ ] so_001~003.nc               ← 6단계에서 생성
[ ] zos_001~003.nc              ← 6단계에서 생성
[ ] uv_001~003.nc               ← 6단계에서 생성
[ ] tu_001~003.nc               ← 6단계에서 생성 (조석)
[ ] tz_001~003.nc               ← 6단계에서 생성 (조석)
[ ] ERA5_t2m_1993_padded.nc     ← 7단계에서 준비
[ ] ERA5_u10_1993_padded.nc     ← 7단계에서 준비
[ ] ERA5_v10_1993_padded.nc     ← 7단계에서 준비
[ ] ERA5_msl_1993_padded.nc     ← 7단계에서 준비
[ ] ERA5_sphum_1993_padded.nc   ← 7단계에서 준비
[ ] ERA5_ssrd_1993_padded.nc    ← 7단계에서 준비
[ ] ERA5_strd_1993_padded.nc    ← 7단계에서 준비
[ ] ERA5_lp_1993_padded.nc      ← 7단계에서 준비
[ ] ERA5_sf_1993_padded.nc      ← 7단계에서 준비
[ ] glofas_runoff_1993.nc       ← 8단계에서 생성
[ ] RiverNutrients_EA12.nc      ← 8단계에서 생성 (신규)
[ ] seawifs-clim-*.nc           ← 9단계에서 준비
[ ] esm4_dry*.nc / esm4_wet*.nc ← 9단계에서 준비
[ ] bgc_cobalt.nc               ← 9단계에서 준비
[ ] bgc_woa.nc                  ← 9단계에서 준비
[ ] esper_glorys_*.nc           ← 9단계에서 준비
[ ] mole_fraction_of_co2_*.nc   ← NWA12에서 복사
</content>
</invoke>