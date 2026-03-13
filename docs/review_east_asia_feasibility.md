# CEFI-regional-MOM6 동아시아 지역 적용 가능성 검토

## 1. 결론 요약

**CEFI-regional-MOM6 프레임워크를 동아시아 지역에 적용하는 것은 기술적으로 가능합니다.**
다만, 기존 NWA12(북서대서양)나 NEP10(북동태평양) 설정을 그대로 사용할 수는 없으며,
동아시아 도메인에 맞는 새로운 설정 파일 및 입력 데이터를 생성해야 합니다.

---

## 2. 동아시아 도메인 정의 (예시)

| 항목 | 제안 값 |
|------|---------|
| 경도 범위 | 약 105°E ~ 160°E |
| 위도 범위 | 약 15°N ~ 52°N |
| 대상 해역 | 동중국해, 남중국해 북부, 황해, 동해(일본해), 쿠로시오 해류 영역 |
| 해상도 | 1/12° (~8km) 권장 (NWA12 기준) |
| 수직 층수 | 75층 (기존 설정 활용 가능) |

---

## 3. 재사용 가능한 기존 인프라

### 3.1 MOM6 소스 코드 및 빌드 시스템 - 그대로 사용 가능
- `src/` 디렉토리의 MOM6, SIS2, FMS, COBALT 소스 코드는 지역 독립적
- `builds/linux-build.bash` 빌드 시스템도 변경 없이 사용 가능
- 빌드 결과물(MOM6SIS2 실행 파일)은 어떤 지역이든 동일

### 3.2 입력 데이터 생성 도구 - 수정 후 사용 가능
| 도구 | 경로 | 동아시아 적용 가능성 |
|------|------|---------------------|
| 초기조건(IC) 생성 | `tools/initial/write_glorys_initial.py` | **가능** - GLORYS는 글로벌 데이터 |
| 경계조건(BC) 생성 | `tools/boundary/write_glorys_boundary.py` | **가능** - GLORYS는 글로벌 데이터 |
| 조석 경계조건 | `tools/boundary/write_tpxo_boundary.py` | **가능** - TPXO는 글로벌 데이터 |
| 대기 강제력 | `tools/atmos/` | **가능** - ERA5는 글로벌 데이터 |
| 하천 유출 | `tools/rivers/write_runoff_glofas.py` | **가능** - GloFAS는 글로벌 데이터 |
| BGC 초기/경계조건 | `tools/initial/write_bgc_initial.py`, `tools/boundary/write_bgc_boundary.py` | **가능** - WOA/COBALT 클리마톨로지는 글로벌 |
| 스펀지/넛징 | `tools/sponge/` | **가능** |

### 3.3 MOM_input 파라미터 - 대부분 재사용 가능
- 물리 파라미터(ALE regridding, EOS, mixing 등)는 지역 독립적
- `DT`, `DT_THERM` 등 시간 간격은 해상도에 따라 조정 필요

---

## 4. 새로 생성해야 하는 항목

### 4.1 수평 그리드 (ocean_hgrid.nc) - 신규 생성 필요
- ESMG Gridtools 또는 COSIMA regional-mom6 도구 사용
- 동아시아 도메인(105°E~160°E, 15°N~52°N)에 맞는 curvilinear 또는 rectilinear 그리드 생성
- 참고: `tools/grid/` 디렉토리의 `make_mosaic.sh`, `make_mask.sh`

### 4.2 해저지형 (ocean_topog.nc) - 신규 생성 필요
- GEBCO 또는 ETOPO 글로벌 수심 데이터에서 동아시아 영역 추출
- 기존 도구 활용 가능

### 4.3 경계 세그먼트 설정 - 신규 정의 필요
동아시아 도메인의 경우 개방 경계(Open Boundary)가 달라짐:

```yaml
# 제안: 동아시아 OBC 세그먼트
segments:
  - id: 1
    border: 'south'    # 남쪽 개방 경계 (남중국해/필리핀해)
  - id: 2
    border: 'north'    # 북쪽 개방 경계 (오호츠크해/북태평양)
  - id: 3
    border: 'east'     # 동쪽 개방 경계 (태평양)
  # 서쪽은 대부분 육지(중국/한반도 해안선)이므로 닫힘
```

> **주의**: 도메인 설정에 따라 서쪽 경계도 열어야 할 수 있음 (남중국해 서쪽 포함 시)

### 4.4 하천 BGC 데이터 - 신규 구축 필요
- 기존에 NWA, NEP, ARC 지역만 하천 BGC 스크립트가 존재 (`tools/rivers/bgc/`)
- 동아시아 주요 하천(양쯔강, 황하, 한강, 낙동강 등)의 영양염 데이터 필요
- GlobalNEWS2 데이터셋에서 동아시아 하천 추출 가능
- GloFAS 유량 데이터는 글로벌이므로 사용 가능

### 4.5 YAML 설정 파일 업데이트
- `glorys_obc.yaml`: 경계 세그먼트를 동아시아에 맞게 수정
- `glorys_ic.yaml`: 초기조건 파일 경로 수정
- `runoff_glofas.yaml`: 위경도 범위를 동아시아로 수정

```yaml
# runoff_glofas.yaml 동아시아 예시
latitude_range:
  start: 52
  end: 15
longitude_range:
  start: 105
  end: 160
```

### 4.6 MOM_input 주요 수정 항목

```fortran
! 동아시아 도메인 예시 (1/12° 해상도 기준)
NIGLOBAL = 660          ! (160-105) * 12 = 660 격자점
NJGLOBAL = 444          ! (52-15) * 12 = 444 격자점
NK = 75                 ! 수직 75층 유지
REENTRANT_X = False     ! 비주기적 경계
REENTRANT_Y = False
DT = 600.0              ! 동적 시간간격 (초)
DT_THERM = 1800.0       ! 열역학 시간간격 (초)
MAXIMUM_DEPTH = 6500.0  ! 최대 수심
MINIMUM_DEPTH = 9.5     ! 최소 수심
```

---

## 5. 동아시아 적용 시 고려사항 및 도전 과제

### 5.1 쿠로시오 해류
- 동아시아 해역의 지배적인 서안경계류
- 충분한 해상도(최소 1/12°)가 필요하며, 이상적으로는 1/25° 이상 권장
- 경계조건에서 쿠로시오의 정확한 표현이 중요

### 5.2 조석 영향
- 황해, 동중국해는 조석이 매우 강한 해역
- TPXO 기반 조석 경계조건의 정확한 설정이 핵심
- `write_tpxo_boundary.py` 도구로 생성 가능하나, 얕은 수심 영역에서 검증 필요

### 5.3 해빙 (SIS2)
- 동해/오호츠크해 북부에서 겨울철 해빙 발생
- SIS2 해빙 모듈이 이미 포함되어 있으므로 활용 가능
- 도메인이 오호츠크해를 포함하는 경우 해빙 초기조건도 필요

### 5.4 반폐쇄 해역 문제
- 황해, 동해는 반폐쇄 해역(semi-enclosed sea)
- 좁은 해협(대한해협, 대만해협, 쓰가루해협)의 해상도 표현이 중요
- 격자 해상도가 해협 폭보다 충분히 작아야 정확한 수송량 재현 가능

### 5.5 계산 자원
- NWA12(775x845x75) 기준으로 추정 시, 동아시아 도메인(~660x444x75)은
  약 45% 정도의 격자 수로, 계산 비용이 상대적으로 적음
- 40x40 레이아웃 대신 약 30x15 정도의 프로세서 레이아웃 가능

---

## 6. 필요 작업 단계 (워크플로우)

```
1단계: 도메인 정의 및 그리드 생성
   └─ 그리드 도구(ESMG/COSIMA)로 ocean_hgrid.nc 생성
   └─ GEBCO/ETOPO에서 ocean_topog.nc 생성
   └─ make_mosaic.sh, make_mask.sh 실행

2단계: 입력 데이터 준비
   └─ GLORYS 데이터 다운로드 (Copernicus Marine Service)
   └─ ERA5 대기 강제력 다운로드 (ECMWF)
   └─ TPXO 조석 데이터 준비

3단계: 초기/경계조건 생성
   └─ write_glorys_initial.py (IC 생성)
   └─ write_glorys_boundary.py (OBC 생성)
   └─ write_tpxo_boundary.py (조석 OBC 생성)
   └─ write_bgc_initial.py / write_bgc_boundary.py (BGC IC/OBC)

4단계: 하천 데이터 준비
   └─ GloFAS 유출 데이터 (write_runoff_glofas.py)
   └─ 동아시아 하천 BGC 데이터 구축 (신규 작업)

5단계: 설정 파일 구성
   └─ MOM_input, MOM_override (도메인/물리 설정)
   └─ input.nml, data_table, diag_table
   └─ field_table, COBALT_input (BGC 설정)
   └─ SIS_input (해빙 설정)

6단계: 테스트 실행 및 검증
   └─ 24시간 테스트 실행
   └─ 재시작(restart) 테스트
   └─ SST, 해류, 조석 검증
```

---

## 7. 최종 평가

| 평가 항목 | 결과 |
|-----------|------|
| 모델 프레임워크 적합성 | **적합** - MOM6는 지역 모델링에 최적화 |
| 소스 코드 수정 필요성 | **없음** - 설정 파일만 변경 |
| 글로벌 입력 데이터 가용성 | **양호** - GLORYS, ERA5, TPXO, GloFAS 모두 글로벌 커버리지 |
| 기존 도구 재사용성 | **높음** - YAML 파일 수정만으로 대부분 사용 가능 |
| 추가 개발 필요 항목 | **하천 BGC** - 동아시아 하천 영양염 데이터 구축 필요 |
| 난이도 | **중간** - 기존 NWA12/NEP10 설정을 참고하면 체계적으로 진행 가능 |

**결론: 이 CEFI-regional-MOM6 프레임워크는 동아시아 해역 모델링에 충분히 적용 가능하며,
기존 인프라(빌드 시스템, 데이터 도구, 물리 파라미터)를 대부분 재활용할 수 있습니다.
주요 작업은 그리드 생성, YAML 설정 파일 수정, 하천 BGC 데이터 구축입니다.**
