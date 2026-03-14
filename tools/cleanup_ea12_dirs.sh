#!/bin/bash
# 디렉토리 정리 스크립트
# 실행 위치: /data01/labdisk/sungjin/MOM6-COBALT
# 사용법: cd /data01/labdisk/sungjin/MOM6-COBALT && bash cleanup_ea12_dirs.sh

echo "=== 잘못된 중복 디렉토리 삭제 ==="
rm -rf exps/exps
rm -rf exps/input
rm -rf exps/tools

echo "=== 올바른 디렉토리 확인/생성 ==="
mkdir -p input/bathymetry
mkdir -p input/atmos/era5
mkdir -p input/ocean_ic_bc/glorys12
mkdir -p input/bgc_ic/woa23
mkdir -p input/bgc_ic/glodap
mkdir -p input/deposition/esm4
mkdir -p input/tidal
mkdir -p input/rivers/glofas
mkdir -p exps/EA12.COBALT/INPUT
mkdir -p exps/EA12.COBALT/RESTART
mkdir -p tools/grid
mkdir -p tools/initial
mkdir -p tools/boundary
mkdir -p tools/atmos
mkdir -p tools/rivers
mkdir -p tools/sponge

echo ""
echo "=== 정리 완료! 현재 구조 ==="
tree -d
