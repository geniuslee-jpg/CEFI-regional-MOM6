#!/bin/bash
#
# 동아시아(EA12) GLORYS 데이터 다운로드 스크립트
#
# 사용법:
#   1) copernicusmarine 설치: pip install copernicusmarine==1.3.2
#   2) 로그인: copernicusmarine login
#   3) 실행:
#      ./get_glorys_ea12.sh -o /data01/labdisk/sungjin/MOM6-COBALT/datasets/glorys/EA12/daily \
#                           -s "2019-01-01" -e "2019-01-31"
#
# 전체 1년 다운로드 예시:
#      ./get_glorys_ea12.sh -o /data01/labdisk/sungjin/MOM6-COBALT/datasets/glorys/EA12/daily \
#                           -s "2019-01-01" -e "2019-12-31"

# ============================================
# 동아시아 도메인 기본값 (EA12: 105-160E, 15-52N)
# ============================================
outdir="/data01/labdisk/sungjin/MOM6-COBALT/datasets/glorys/EA12/daily"
lon_min=105
lon_max=160
lat_min=15
lat_max=52
startDate="2019-01-01"
endDate="2019-01-31"

# Parse command-line arguments
while getopts ":o:x:X:y:Y:s:e:" opt; do
  case $opt in
    o) outdir="$OPTARG";;
    x) lon_min="$OPTARG";;
    X) lon_max="$OPTARG";;
    y) lat_min="$OPTARG";;
    Y) lat_max="$OPTARG";;
    s) startDate="$OPTARG";;
    e) endDate="$OPTARG";;
    \?) echo "Invalid option: -$OPTARG" >&2; exit 1;;
    :) echo "Option -$OPTARG requires an argument." >&2; exit 1;;
  esac
done

# 출력 디렉토리 생성
mkdir -p "$outdir"

# 로그인 확인
if ! copernicusmarine login --skip-if-user-logged-in 2>/dev/null; then
    echo "Error: copernicusmarine 로그인이 필요합니다."
    echo "먼저 실행: copernicusmarine login"
    exit 1
fi

# Product ID
productId="cmems_mod_glo_phy_my_0.083deg_P1D-m"

# Variables: 온도, 염분, 유속(u,v), 해수면 높이
variables=("so" "thetao" "uo" "vo" "zos")

echo "============================================"
echo " EA12 GLORYS 다운로드"
echo " 영역: ${lon_min}~${lon_max}E, ${lat_min}~${lat_max}N"
echo " 기간: ${startDate} ~ ${endDate}"
echo " 저장: ${outdir}"
echo "============================================"

# 종료일 +1 (루프 포함 처리용)
loopEnd=$(date -d "$endDate + 1 days" +%Y-%m-%d)
currentDate="$startDate"

# 다운로드 카운터
total=0
failed=0

while [[ "$currentDate" != "$loopEnd" ]]; do
    outfile="GLORYS_REANALYSIS_${currentDate}.nc"

    # 이미 다운로드된 파일 건너뛰기
    if [ -f "${outdir}/${outfile}" ]; then
        echo "[SKIP] ${outfile} 이미 존재"
        currentDate=$(date -d "$currentDate + 1 days" +%Y-%m-%d)
        continue
    fi

    echo "=============== Date: $currentDate ===================="

    var_flags=""
    for v in "${variables[@]}"; do
        var_flags="$var_flags -v $v"
    done

    copernicusmarine subset -i "$productId" \
        $var_flags \
        -x "$lon_min" -X "$lon_max" \
        -y "$lat_min" -Y "$lat_max" \
        -t "$currentDate" -T "$currentDate" \
        --force-download \
        -o "$outdir" \
        -f "$outfile"

    if [ $? -eq 0 ]; then
        echo "[OK] ${outfile}"
        total=$((total + 1))
    else
        echo "[FAIL] ${outfile}"
        failed=$((failed + 1))
    fi

    currentDate=$(date -d "$currentDate + 1 days" +%Y-%m-%d)
done

echo "============================================"
echo " 다운로드 완료!"
echo " 성공: ${total}, 실패: ${failed}"
echo " 저장 위치: ${outdir}"
echo "============================================"
