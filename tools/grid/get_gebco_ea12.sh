#!/bin/bash
#
# 동아시아(EA12) GEBCO 해저지형 데이터 다운로드 및 추출 스크립트
#
# GEBCO는 계정 없이 다운로드 가능합니다.
#
# 방법 1: 전체 GEBCO 다운로드 후 추출 (아래 스크립트 사용)
# 방법 2: GEBCO 웹사이트에서 영역 지정 다운로드 (권장, 파일 크기 작음)
#          https://download.gebco.net/
#          → 105E~160E, 15N~52N 선택 → NetCDF 다운로드
#
# 사용법:
#   방법 2를 사용한 경우:
#     ./get_gebco_ea12.sh -i /path/to/downloaded_gebco.nc
#
#   방법 1 (전체 GEBCO에서 추출):
#     ./get_gebco_ea12.sh -i /path/to/GEBCO_2023.nc

OUTDIR="/data01/labdisk/sungjin/MOM6-COBALT/datasets/gebco/EA12"
INPUT_FILE=""

while getopts ":i:o:" opt; do
  case $opt in
    i) INPUT_FILE="$OPTARG";;
    o) OUTDIR="$OPTARG";;
    \?) echo "Invalid option: -$OPTARG" >&2; exit 1;;
  esac
done

if [ -z "$INPUT_FILE" ]; then
    echo "============================================"
    echo " GEBCO 해저지형 데이터 다운로드 안내"
    echo "============================================"
    echo ""
    echo " 1. 아래 URL에서 동아시아 영역 데이터를 다운로드하세요:"
    echo "    https://download.gebco.net/"
    echo ""
    echo " 2. 영역 설정:"
    echo "    West: 105, East: 160"
    echo "    South: 15, North: 52"
    echo ""
    echo " 3. Format: NetCDF"
    echo ""
    echo " 4. 다운로드 후 이 스크립트 재실행:"
    echo "    ./get_gebco_ea12.sh -i /path/to/gebco_data.nc"
    echo ""
    echo "============================================"
    exit 0
fi

mkdir -p "$OUTDIR"

# ncks가 있으면 영역 추출 (전체 GEBCO 파일인 경우)
if command -v ncks &> /dev/null; then
    echo "NCO로 동아시아 영역 추출 중..."
    ncks -d lon,105.0,160.0 -d lat,15.0,52.0 \
         "$INPUT_FILE" -O "${OUTDIR}/GEBCO_EA12.nc"
    echo "[OK] ${OUTDIR}/GEBCO_EA12.nc"
else
    echo "NCO가 설치되어 있지 않습니다. 파일을 복사합니다."
    cp "$INPUT_FILE" "${OUTDIR}/GEBCO_EA12.nc"
    echo "[OK] ${OUTDIR}/GEBCO_EA12.nc (영역 추출 필요시 NCO 설치 후 재실행)"
fi

echo ""
echo "============================================"
echo " 다음 단계: ocean_topog.nc 생성"
echo " tools/grid/ 의 도구를 사용하여 GEBCO에서"
echo " MOM6 격자에 맞는 해저지형을 생성하세요."
echo "============================================"
