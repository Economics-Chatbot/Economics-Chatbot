# EconomyMate UI·Motion Design Specification (v2.0)

> **기준 화면**: Mobile 390 × 844px  
> **핵심 원칙**: 이미지 1, 2, 3, 4 스펙에 맞춰 캐릭터 표정, 장식 자산, 타이포그래피, 레이아웃을 통일하고 코딩의 정합성을 위해 중복/모순된 이전 스펙을 제거하고 명확히 정의한다.

---

## 1. 캐릭터 표정 및 상태 매핑 규칙

| 표정 레퍼런스 | 표정 상태 설명 | 사용 시점 | 자산 파일명 |
| :--- | :--- | :--- | :--- |
| **이미지 1** | 눈 감고 웃는 미소 표정 | 질문 전송 직후, 로딩/검색 진행, 스트리밍 완료 | `character-closed.png` / `character-complete.png` |
| **이미지 2** | 위를 올려다보는 생각 미소 표정 | 정보 불러오는 중 (검색·스트리밍 진행 중) | `character-thinking.png` |
| **이미지 3** | 동공 지진 / 찌그러진 당황 표정 | 검색 실패 (`failure`), 기술 오류 (`error`), `not_found` | `character-error.png` / `character-curious.png` |

> ⚠️ **원칙**: 정보를 불러올 때는 **이미지 1, 2 표정만 사용**하며, 오류나 실패 시에는 반드시 **이미지 3 표정만 사용**한다.

---

## 2. 시작 화면 (Home) 픽셀 & 레이아웃 명세 (이미지 4 기준)

### 2.1 상단 헤더 (`CHUNK_HEADER`)
- **뒤로가기 버튼**: `<` (좌측, 40×40px 터치 영역)
- **브랜드 로고**: `EconomyMate` (중앙 정렬, 딥 블루 폰트, `font-family: Fredoka`, 24px/30px)
- **정보 버튼**: `ⓘ` (우측, 40×40px 터치 영역, 파란색 원형 아이콘)

### 2.2 캐릭터 스테이지 & 3D/파스텔 장식 (`CHUNK_CHARACTER_STAGE`)
- **캐릭터 크기**: `184 × 184px` (중앙 정렬)
- **캐릭터 주변 신규 장식 자산**:
  1. **3D 물음표 (`?`)**: 하늘색/파란색 3D 물음표 칩 (우측 상단 위치)
  2. **구체 원 (`●`)**: 보라색, 하늘색, 주황색 파스텔 3D 구체 (좌/우 흩어짐)
  3. **십자 반짝이 별 (`✦`)**: 파란색/하늘색 반짝이 스파클 (좌측 상단 위치)

### 2.3 메인 타이틀 & 서브 설명 (`CHUNK_HOME_INTRO`)
- **메인 타이틀**: **`궁금한 경제용어,\n편하게 물어보세요`**
  - Font: `Pretendard` Bold 700
  - Size: `24px` / Line-height: `34px`
  - Color: `#172033` (기본 네이비)
  - Alignment: `center`
- **서브 설명**: `어려운 경제를 쉽고 친근하게 설명해드릴게요.`
  - Font: `Pretendard` Medium 500
  - Size: `14px` / Line-height: `22px`
  - Color: `#667085` (보조 그레이)

### 2.4 추천 질문 영역 (`CHUNK_HOME_SUGGESTIONS`)
- **섹션 라벨**: `이런 질문은 어때요?`
  - Size: `14px` / Weight: `600` / Color: `#2647D8` (딥 블루) / Alignment: `left`
- **추천 질문 칩 버튼 (알약 모양 Pill Shape)**:
  - Radius: `999px` (Pill Shape)
  - Background: `#FFFFFF`
  - Border: `1.5px solid #62B9F5` (파란색 라인)
  - Inner Padding: `10px 16px`
  - 아이콘 + 텍스트 구성:
    1. `📈` (상승 그래프 아이콘 칩) + `인플레이션이 뭐야?`
    2. `％` (퍼센트 금리 아이콘 칩) + `금리가 오르면 어떻게 돼?`
    3. `📊` (파이 차트 아이콘 칩) + `ETF를 쉽게 설명해줘`

### 2.5 하단 DOCK 입력창 (`CHUNK_INPUT_DOCK`)
- **Dock Container**: `width: 358px`, `height: 58px`, `radius: 29px` (Pill Shape), `background: #FFFFFF`, `border: 1px solid #E4EAF2`, `shadow: 0 6px 20px rgba(23,32,51,0.10)`
- **Placeholder**: `경제용어를 입력해 주세요` (Color: `#667085`)
- **전송 버튼**: 파란색 원형 버튼 (`#405DE6`, 46×46px) + 흰색 비행기/화살표 아이콘 (`➢`)

---

## 3. 질문 및 정보 로딩 / 결과 전환 모션 명세

### 3.1 정보 로딩 파이프라인 (이미지 1 & 2 표정)
1. **0ms (전송 시작)**: 이미지 1 (눈 감은 미소 표정 `character-complete.png`) 90ms 페이드 전환
2. **120ms (축소 이동)**: 캐릭터 크기 `184px → 132px` 축소 및 상단 이동 (`transform: translate3d(26px, -93px, 0) scale(0.717391)`)
3. **520ms (검색 중)**: 이미지 2 (위를 올려다보는 표정 `character-thinking.png`) 전환
4. **결과 수신 완료**: 이미지 1 (눈 감고 미소 짓는 표정)으로 최종 답변 표시

### 3.2 오류 / 실패 처리 파이프라인 (이미지 3 표정)
- `suggestions`, `failure`, `error`, `not_found` 상태 진입 시:
  - 캐릭터 표정을 **이미지 3 (동공 지진/당황 표정 `character-curious.png` / `character-error.png`)**으로 100% 즉시 전환.
  - 해당 상태 카드 UI 표시 및 다시 질문하기 / 재시도 버튼 활성화.

---

## 4. 디자인 토큰 정의

```css
:root {
  --color-main-blue: #405DE6;
  --color-deep-blue: #2647D8;
  --color-sky-blue: #62B9F5;
  --color-ice-blue: #DCEEFF;
  --color-soft-blue-bg: #F3F8FF;
  --color-white: #FFFFFF;
  --color-text-primary: #172033;
  --color-text-secondary: #667085;
  --color-border: #E4EAF2;

  --shadow-dock: 0 6px 20px rgba(23, 32, 51, 0.10);
  --shadow-float: 0 8px 24px rgba(38, 71, 216, 0.10);
  --focus-ring: 0 0 0 3px rgba(98, 185, 245, 0.30);

  --radius-pill: 999px;
  --radius-large: 22px;
  --radius-medium: 16px;
}
```
