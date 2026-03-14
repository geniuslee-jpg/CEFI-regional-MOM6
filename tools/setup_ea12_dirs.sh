#!/bin/bash
#
# 동아시아(EA12) MOM6-COBALT 디렉토리 구조 자동 생성
#
# 사용법:
#   cd /data01/labdisk/sungjin/MOM6-COBALT
#   bash setup_ea12_dirs.sh
#
# 또는 다른 위치에서:
#   bash setup_ea12_dirs.sh /data01/labdisk/sungjin/MOM6-COBALT

BASEDIR="${1:-.}"

echo "============================================"
echo " EA12 MOM6-COBALT 디렉토리 구조 생성"
echo " 기준 경로: $(cd "$BASEDIR" && pwd)"
echo "============================================"

# ---- 원본 데이터 (다운로드한 그대로 보관) ----
mkdir -p "$BASEDIR/input/bathymetry"           # GEBCO 해저지형
mkdir -p "$BASEDIR/input/atmos/era5"           # ERA5 대기강제력 원본
mkdir -p "$BASEDIR/input/ocean_ic_bc/glorys12" # GLORYS12 (이미 있음)
mkdir -p "$BASEDIR/input/bgc_ic/woa23"         # WOA23 (이미 있음)
mkdir -p "$BASEDIR/input/bgc_ic/glodap"        # GLODAPv2 (DIC/ALK, 선택)
mkdir -p "$BASEDIR/input/tidal"                # TPXO9 조석 (선택)
mkdir -p "$BASEDIR/input/rivers/glofas"        # GloFAS 하천유출 (선택)
mkdir -p "$BASEDIR/input/deposition/esm4"      # ESM4 대기침적 (COBALT용)

# ---- 실험 디렉토리 (MOM6가 읽는 전처리 완료 파일) ----
mkdir -p "$BASEDIR/exps/EA12.COBALT/INPUT"
mkdir -p "$BASEDIR/exps/EA12.COBALT/RESTART"

# ---- 전처리 도구 ----
mkdir -p "$BASEDIR/tools/grid"
mkdir -p "$BASEDIR/tools/initial"
mkdir -p "$BASEDIR/tools/boundary"
mkdir -p "$BASEDIR/tools/atmos"
mkdir -p "$BASEDIR/tools/rivers"
mkdir -p "$BASEDIR/tools/sponge"

echo ""
echo "✅ 디렉토리 생성 완료!"
echo ""
echo "현재 구조:"
cd "$BASEDIR" && find . -type d | sort | head -40
echo ""

# ---- 데이터 현황 체크 ----
echo "============================================"
echo " 데이터 현황 체크"
echo "============================================"

check_data() {
    local label="$1"
    local path="$2"
    if [ -e "$path" ]; then
        local count=$(find "$path" -name "*.nc" 2>/dev/null | wc -l)
        echo "  ✅ $label ($count개 NC파일)"
    else
        echo "  ❌ $label - 없음"
    fi
}

check_data "GLORYS12 1993"        "$BASEDIR/input/ocean_ic_bc/glorys12"
check_data "WOA23"                "$BASEDIR/input/bgc_ic/woa23"
check_data "GEBCO 해저지형"        "$BASEDIR/input/bathymetry"
check_data "ERA5 대기강제력"       "$BASEDIR/input/atmos/era5"
check_data "TPXO 조석 (선택)"     "$BASEDIR/input/tidal"
check_data "GloFAS 하천 (선택)"    "$BASEDIR/input/rivers/glofas"
check_data "ESM4 대기침적"         "$BASEDIR/input/deposition/esm4"
check_data "GLODAP (선택)"        "$BASEDIR/input/bgc_ic/glodap"

echo ""
echo "============================================"
echo " 다음 단계"
echo "============================================"
echo ""
echo " 1. GEBCO 다운로드 (무료, 계정 불필요)"
echo "    → https://download.gebco.net/"
echo "    → 105E~160E, 15N~52N 선택, NetCDF"
echo "    → input/bathymetry/ 에 저장"
echo ""
echo " 2. ERA5 다운로드 (ECMWF CDS 무료계정 필요)"
echo "    → https://cds.climate.copernicus.eu/"
echo "    → pip install cdsapi"
echo "    → 9개 변수: t2m,u10,v10,msl,d2m,ssrd,strd,tp,sf"
echo "    → input/atmos/era5/ 에 저장"
echo ""
echo " 3. 격자 생성 (GEBCO 다운 후)"
echo "    → ocean_hgrid.nc, ocean_topog.nc 생성"
echo "    → exps/EA12.COBALT/INPUT/ 에 저장"
echo ""
echo " 4. IC/OBC 생성 (격자 생성 후)"
echo "    → GLORYS → MOM.res.nc, uv_00X.nc 등"
echo "    → WOA23 + ESPER → bgc_woa_esper_ics.nc"
echo ""
echo "============================================"
