# EconomyMate UI·Motion Design Specification

> 문서 버전: 1.0  
> 기준 화면: Mobile 390 × 844px  
> 적용 범위: 시작 화면, 질문 전송, 검색·스트리밍, 답변 결과, 후보·실패·오류 상태  
> 핵심 원칙: 컬러 추출 보드의 색만 사용하고, 제공된 젤리 PNG를 수정하지 않으며, 질문 전송 시 젤리가 눈을 감은 뒤 자연스럽게 작아져 결과 화면으로 이어지게 한다.

---

## 1. 구현 목표와 제외 범위

### 1.1 구현 목표

1. 경제용어를 처음 접하는 사용자도 질문, 답변, 출처, 연관 용어의 순서를 한 번에 이해할 수 있어야 한다.
2. 시작 화면과 결과 화면이 서로 다른 제품처럼 보이지 않아야 한다.
3. 질문 전송 시 젤리는 `눈 감기 → 위로 이동하며 축소 → 생각 표정 → 답변 완료 표정 → 기본 표정` 순서로 연결되어야 한다.
4. `POST /api/answers`의 스트리밍 이벤트를 화면 상태와 1:1로 연결한다.
5. AI가 작성한 본문과 DB가 제공하는 용어명·출처·연관 검색어를 시각적으로 구분한다.
6. 390 × 844px 기준에서 모든 UI 요소의 이름, 좌표, 크기, 색상, 여백을 고정한다.

### 1.2 구현 목적에 포함되지 않는 디자인

다음 요소는 추가하지 않는다.

- 하단 내비게이션, 햄버거 메뉴, 프로필, 로그인, 설정, 알림
- `+`, 카메라, 마이크, 파일 첨부 버튼
- 캐릭터와 무관한 일러스트, 3D 아이콘, 스톡 이미지
- 글래스모피즘, 네온, 강한 블러, 과도한 그라데이션
- 대시보드형 카드 묶음, 차트, 통계, 인기 검색어 순위
- AI 별·반짝이·마법봉·로봇·회로 모양 아이콘
- “AI가 분석했어요”, “스마트 답변”, “생성형 AI” 같은 기술 과시 문구
- 캐릭터 바운스, 좌우 흔들기, 회전, 고무처럼 늘어나기
- 답변마다 프로필 이미지, 이름, 시각, 말풍선 꼬리를 반복 표시하는 메신저형 장식
- 목적 없는 그림자, 장식선, 배경 패턴, 장식용 카드
- 복수 용어 분리 UI와 복수 결과 탭: 다음 태스크로 연기

### 1.3 사람이 직접 정돈한 제품처럼 보이기 위한 원칙

- 한 화면에서 강조색은 `MAIN_BLUE` 한 가지를 중심으로 사용한다.
- 섹션 제목의 패턴, 패딩, 선 굵기를 반복해 일관성을 만든다.
- 문장형 안내 문구를 짧게 유지하고 과장된 카피를 쓰지 않는다.
- 이모지는 AI가 임의로 선택하지 않는다. 답변 섹션의 `📌`, `💡`, `🏠` 세 개만 고정 사용한다.
- 카드 안에 카드를 과도하게 중첩하지 않는다.
- 색상·간격·모서리 값은 이 문서의 토큰만 사용한다. 임의의 중간값을 만들지 않는다.
- 캐릭터는 기능 상태를 알려주는 역할만 한다. 화면을 계속 떠다니거나 사용자의 시선을 방해하지 않는다.

---

## 2. 명명 규칙

### 2.1 화면 이름

| 화면 상태 | Frame name | 역할 |
| --- | --- | --- |
| 시작 | `SCREEN_HOME_IDLE` | 최초 진입, 추천 질문 표시 |
| 입력 | `SCREEN_HOME_TYPING` | 입력창 포커스 또는 질문 작성 |
| 전환 | `SCREEN_QUERY_TRANSITION` | 눈 감기와 축소·이동 |
| 검색 | `SCREEN_SEARCHING` | 정확 검색 또는 벡터 검색 진행 |
| 스트리밍 | `SCREEN_ANSWER_STREAMING` | AI 본문을 조각 단위로 표시 |
| 답변 완료 | `SCREEN_ANSWER_DONE` | 답변, 출처, 연관 용어 표시 |
| 후보 | `SCREEN_SUGGESTIONS` | 0.55 이상 0.72 미만 후보 표시 |
| 실패 | `SCREEN_FAILURE` | 0.55 미만 검색 실패 |
| 오류 | `SCREEN_ERROR` | 네트워크·OpenAI 기술 오류 |

### 2.2 UI 청크 이름

- `CHUNK_HEADER`
- `CHUNK_HOME_INTRO`
- `CHUNK_CHARACTER_STAGE`
- `CHUNK_HOME_GUIDE`
- `CHUNK_HOME_SUGGESTIONS`
- `CHUNK_QUERY_BUBBLE`
- `CHUNK_ANSWER_VIEWPORT`
- `CHUNK_TERM_HEADER`
- `CHUNK_ANSWER_CONTENT`
- `CHUNK_SOURCE`
- `CHUNK_RELATED_TERMS`
- `CHUNK_INPUT_DOCK`
- `CHUNK_STATUS_FEEDBACK`

### 2.3 컴포넌트 이름

- `UI_HEADER_BACK_BUTTON`
- `UI_HEADER_BRAND`
- `UI_HEADER_INFO_BUTTON`
- `UI_CHARACTER_IMAGE`
- `UI_CHARACTER_SHADOW`
- `UI_USER_QUERY_BUBBLE`
- `UI_TERM_EYEBROW`
- `UI_TERM_NAME`
- `UI_ANSWER_SECTION_TITLE`
- `UI_ANSWER_SECTION_BODY`
- `UI_SOURCE_LABEL`
- `UI_SOURCE_VALUE`
- `UI_RELATED_TERM_BUTTON`
- `UI_TEXTAREA`
- `UI_SEND_BUTTON`
- `UI_STREAM_CARET`
- `UI_TYPING_DOTS`

코드의 class, data attribute, 디자인 레이어 이름도 위 이름을 소문자 kebab-case로 변환해 사용한다. 예: `UI_TERM_NAME` → `.ui-term-name`.

---

## 3. 색상 시스템

컬러 추출 보드의 다음 색만 브랜드 색으로 인정한다.

| Token name | 한글 명칭 | HEX | 사용처 |
| --- | --- | --- | --- |
| `COLOR_MAIN_BLUE` | 메인 블루 | `#405DE6` | 전송 버튼, 사용자 질문, 주요 강조 |
| `COLOR_DEEP_BLUE` | 딥 블루 | `#2647D8` | 로고, 제목, 선택 상태, 포커스 |
| `COLOR_SKY_BLUE` | 스카이 블루 | `#62B9F5` | 제한적 상태 강조, 로딩 점 |
| `COLOR_ICE_BLUE` | 아이스 블루 | `#DCEEFF` | 포커스 링, 약한 강조 배경 |
| `COLOR_SOFT_BLUE_BG` | 소프트 블루 배경 | `#F3F8FF` | 답변 카드, 추천 질문, 후보 영역 |
| `COLOR_WHITE` | 화이트 | `#FFFFFF` | 앱 배경, 입력창, 카드 내부 |
| `COLOR_TEXT_PRIMARY` | 기본 네이비 | `#172033` | 본문과 용어명 |
| `COLOR_TEXT_SECONDARY` | 보조 그레이 | `#667085` | 안내, 출처, 보조 문구 |
| `COLOR_BORDER` | 경계 그레이 | `#E4EAF2` | 카드·입력창 경계선 |
| `COLOR_LIME` | 라임 | `#C8F24A` | 향후 라임 젤리 전용 |
| `COLOR_YELLOW` | 옐로 | `#FFD84D` | 노란 젤리 보조 강조 |
| `COLOR_ORANGE` | 오렌지 | `#FF9F43` | 주황 젤리 보조 강조 |
| `COLOR_PINK` | 핑크 | `#FF6B9E` | 향후 핑크 젤리 전용 |
| `COLOR_PURPLE` | 퍼플 | `#8B6FF7` | 향후 퍼플 젤리 전용 |
| `COLOR_MINT` | 민트 | `#58D6B3` | 민트 젤리 보조 강조 |

### 3.1 파생 색상 사용 규칙

- 투명도는 기존 색상에 alpha만 적용할 수 있다.
- `SHADOW_FLOAT = 0 8px 24px rgba(38, 71, 216, 0.10)`
- `SHADOW_DOCK = 0 6px 20px rgba(23, 32, 51, 0.10)`
- `FOCUS_RING = 0 0 0 3px rgba(98, 185, 245, 0.30)`
- 눌림 배경: `rgba(220, 238, 255, 0.72)`
- 임의의 네이비, 청록, 회색을 새로 만들지 않는다.
- 메인 UI의 면적 비율은 `화이트 60% / 블루 계열 30% / 캐릭터 강조 10%`를 목표로 한다.
- 한 화면에서 캐릭터 강조색은 현재 표시 중인 젤리 색 한 가지만 사용한다.

### 3.2 상태 색상

- 로딩과 정상 상태는 블루 계열만 사용한다.
- 실패와 기술 오류도 강한 빨강을 사용하지 않는다. `COLOR_SOFT_BLUE_BG` 카드 안에 `COLOR_TEXT_PRIMARY`로 설명하고 재시도 버튼만 `COLOR_MAIN_BLUE`로 표시한다.
- 경제 정보 서비스이므로 색만으로 상태를 전달하지 않는다. 반드시 문구를 함께 표시한다.

---

## 4. 타이포그래피

### 4.1 폰트

- 영문 브랜드: `Fredoka`, fallback `"Arial Rounded MT Bold", sans-serif`
- 모든 한글·숫자·영문 본문: `Pretendard`, fallback `"Noto Sans KR", sans-serif`
- 명조, 손글씨, 장식체, 모노스페이스를 사용하지 않는다.

### 4.2 텍스트 토큰

| Token | Font / weight | Size | Line height | Letter spacing | Color |
| --- | --- | ---: | ---: | ---: | --- |
| `TYPE_BRAND_HOME` | Fredoka 700 | 30px | 36px | -0.6px | `DEEP_BLUE` |
| `TYPE_BRAND_RESULT` | Fredoka 700 | 24px | 30px | -0.4px | `DEEP_BLUE` |
| `TYPE_HOME_TITLE` | Pretendard 700 | 22px | 31px | -0.44px | `TEXT_PRIMARY` |
| `TYPE_TERM_EYEBROW` | Pretendard 600 | 13px | 20px | -0.16px | `DEEP_BLUE` |
| `TYPE_TERM_NAME` | Pretendard 700 | 28px | 38px | -0.56px | `TEXT_PRIMARY` |
| `TYPE_SECTION_TITLE` | Pretendard 700 | 17px | 24px | -0.3px | `DEEP_BLUE` |
| `TYPE_BODY` | Pretendard 400 | 15px | 24px | -0.15px | `TEXT_PRIMARY` |
| `TYPE_BODY_STRONG` | Pretendard 600 | 15px | 24px | -0.15px | `TEXT_PRIMARY` |
| `TYPE_SUPPORT` | Pretendard 400 | 13px | 20px | -0.1px | `TEXT_SECONDARY` |
| `TYPE_BUTTON` | Pretendard 600 | 15px | 22px | -0.2px | 상태별 지정 |
| `TYPE_INPUT` | Pretendard 400 | 15px | 22px | -0.2px | `TEXT_PRIMARY` |

본문은 한 줄에 한글 약 20~24자를 넘지 않게 한다. 답변 문단 사이 여백은 8px이며 불필요한 줄바꿈을 넣지 않는다.

---

## 5. 기준 프레임과 공통 레이아웃

### 5.1 앱 프레임

- Name: `FRAME_APP_MOBILE`
- 기준 크기: `390 × 844px`
- CSS: `width: min(100%, 390px); height: 100dvh; min-height: 640px`
- 배경: `COLOR_WHITE`
- x축 overflow: `hidden`
- body 외부 배경: `COLOR_SOFT_BLUE_BG`
- 390px보다 넓은 화면에서는 앱을 가운데 정렬한다.
- 콘텐츠 좌우 안전 여백: 20px
- 입력창 bottom: `max(16px, env(safe-area-inset-bottom))`
- 모든 요소: `box-sizing: border-box`

### 5.2 4px 간격 체계

허용 간격: `4, 8, 12, 16, 20, 24, 28, 32px`. 10px, 14px 등은 이 명세에 좌표로 지정된 경우에만 사용한다.

### 5.3 모서리 토큰

- `RADIUS_SMALL = 10px`
- `RADIUS_MEDIUM = 16px`
- `RADIUS_LARGE = 22px`
- `RADIUS_PILL = 999px`
- 카드에 서로 다른 임의의 radius를 사용하지 않는다.

---

## 6. 캐릭터 자산과 명칭

### 6.1 대표 캐릭터

- 제품 내 대표 명칭: `옐로 메이트`
- 코드 식별자: `jelly-yellow`
- 역할: 사용자의 질문 상태와 답변 진행 상태를 표정으로 안내한다.
- 첫 구현에서는 옐로 메이트만 사용한다. 한 화면에 여러 색 젤리를 동시에 배치하지 않는다.

### 6.2 확장 캐릭터 명칭

| 표시 명칭 | 코드 식별자 | Accent token | 사용 원칙 |
| --- | --- | --- | --- |
| 옐로 메이트 | `jelly-yellow` | `COLOR_YELLOW` | 기본 대표 캐릭터 |
| 민트 메이트 | `jelly-mint` | `COLOR_MINT` | 별도 테마 선택 시만 사용 |
| 오렌지 메이트 | `jelly-orange` | `COLOR_ORANGE` | 별도 테마 선택 시만 사용 |

민트·오렌지 캐릭터는 옐로 캐릭터와 같은 화면 규격과 상태 이름을 사용해야 한다. 색에 따라 크기나 기능을 달리하지 않는다.

### 6.3 표정 상태와 파일명

| State | 파일명 | 사용 규칙 및 시점 |
| --- | --- | --- |
| `CHARACTER_DEFAULT` | `character-default.png` | **[이미지 1]** 눈 감은 미소 표정: 초기, 질문 전송 시작, 스트리밍 완료 후 |
| `CHARACTER_THINKING` | `character-thinking.png` | **[이미지 2]** 위를 올려다보는 생각 표정: 백엔드 검색 및 정보 불러오는 중 전용 |
| `CHARACTER_ERROR` / `CURIOUS` | `character-curious.png` | **[이미지 3]** 동공 지진 / 당황 표정: `suggestions`, `failure`, `error`, `not_found` 오류·실패 전용 |

> ⚠️ **원칙**: 정보를 불러올 때는 **이미지 1, 2 표정만 사용**하며, 오류나 실패 발생 시에는 반드시 **이미지 3 표정만 사용**한다.

### 6.4 이미지 처리 규칙

- 포맷: 투명 배경 PNG, alpha channel 필수
- 캔버스: 네 이미지 모두 `1254 × 1254px`
- CSS: `object-fit: contain; object-position: center`
- 원본 색, 얼굴, 광택, 질감, 외곽을 수정하지 않는다.
- CSS filter, hue-rotate, drop-shadow, mix-blend-mode를 적용하지 않는다.
- 이미지 자체를 매 상태마다 새 DOM으로 삽입하지 않는다. 같은 프레임 안에 레이어를 겹치고 opacity로 교체한다.
- 모든 상태 이미지의 시각 중심이 2px 이상 어긋나면 자산 캔버스를 먼저 정렬한다. CSS 좌표를 상태마다 다르게 조정하지 않는다.
- 배경 제거 과정에서 흰 테두리, 파란 색 번짐, 직사각형 배경이 남아서는 안 된다.

---

## 7. 시작 화면 픽셀 명세

### 7.1 `CHUNK_HEADER`

- 영역: `x=20, y=20, w=350, h=44`
- `UI_HEADER_BRAND`: `x=86, y=22, w=218, h=38`
- 텍스트: `EconomyMate`
- 타입: `TYPE_BRAND_HOME`
- 정렬: center
- 시작 화면에서는 뒤로가기와 정보 버튼을 표시하지 않는다.

### 7.2 `CHUNK_HOME_INTRO`

- 영역: `x=30, y=360, w=330, h=64`
- 텍스트: `궁금한 경제용어,\n편하게 물어보세요`
- 타입: `TYPE_HOME_TITLE` (Pretendard Bold 700, 26px/36px, `#0f172a`)
- 정렬: center

### 7.3 `CHUNK_CHARACTER_STAGE` — 시작 상태 및 3D 파스텔 장식

- stage: `x=0, y=0, w=390, h=354`
- `UI_CHARACTER_IMAGE`: 시각 경계 `x=103, y=155, w=184, h=184`
- `UI_CHARACTER_SHADOW`: `x=123, y=320, w=144, h=14`
- **캐릭터 주변 3D 파스텔 장식 요소**:
  - 3D 물음표 1 (`?` 칩, 우측 상단 `top: 20px, right: 75px`)
  - 3D 물음표 2 (`?` 칩, 우측 중앙 `top: 85px, right: 60px`)
  - 파스텔 3D 보라색 입체 구체 (`deco-orb-purple-large`, `top: 110px, left: 55px`)
  - 파스텔 3D 하늘색/주황색 구체
  - 십자 반짝이 별 (`✦`, 좌측 상단 `top: 40px, left: 85px`)

### 7.4 `CHUNK_HOME_GUIDE`

- 영역: `x=30, y=442, w=330, h=20`
- 텍스트: `어려운 경제를 쉽고 친근하게 설명해드릴게요.`
- 타입: `TYPE_SUPPORT` (Pretendard Medium 500, 14px/20px, `#64748b`)
- 정렬: center

### 7.5 `CHUNK_HOME_SUGGESTIONS` (이미지 4 레퍼런스 100% 매칭 스펙)

- 영역: `x=24, y=490, w=342, h=210`
- 섹션 라벨: `이런 질문은 어때요?` (`TYPE_SECTION_TITLE`, Pretendard 600 13.5px, `#2563eb`, Left Aligned)
- 추천 질문 칩 버튼 (알약 모양 Pill Shape):
  - Width: `342px`, Height: `50px`, Radius: `RADIUS_PILL` (9999px)
  - Background: `#FFFFFF`
  - Border: `1.5px solid #2563eb` (메인 블루 라인)
  - Inner Padding: `0 18px`
  - 아이콘 동그라미 원 칩 (`width: 34px, height: 34px, radius: 50%, background: linear-gradient(135deg, #e0f2fe, #bae6fd)`) 내 SVG/아이콘 포함
- 고정 추천 질문 3개:
  1. `📈` (상승 그래프 벡터 아이콘) `인플레이션이 뭐야?`
  2. `％` (퍼센트 금리 벡터 아이콘) `금리가 오르면 어떻게 돼?`
  3. `📊` (파이 차트/그래프 벡터 아이콘) `ETF를 쉽게 설명해줘`

### 7.6 `CHUNK_INPUT_DOCK` — 공통

- outer: `x=16, y=770` (844px 하단 고정), `w=358, h=58`
- position: fixed / absolute
- bottom: `max(16px, env(safe-area-inset-bottom))`
- 배경: `COLOR_WHITE` (`#ffffff`)
- 경계: `1.5px solid #e2e8f0`
- radius: `29px`
- shadow: `SHADOW_DOCK` (`0 10px 25px -5px rgba(37, 99, 235, 0.12)`)
- z-index: 40

`UI_TEXTAREA`:

- `x=34, w=278, h=44`
- padding: `11px 0`
- placeholder: `경제용어를 입력해 주세요`
- placeholder color: `COLOR_TEXT_SECONDARY` (`#64748b`)
- 글자: `TYPE_INPUT`
- border, outline, background: none
- 최대 높이: 88px, 4줄을 넘으면 textarea 내부 스크롤

`UI_SEND_BUTTON`:

- `x=320, w=46, h=46`
- 배경: `COLOR_MAIN_BLUE` (`linear-gradient(135deg, #2563eb, #1d4ed8)`)
- radius: `RADIUS_PILL` (9999px)
- 화살표: 흰색 20 × 20px 종이비행기/화살표 SVG
- 빈 입력: opacity `0.38`, disabled
- 입력 있음: opacity `1`, enabled
- active: `transform: scale(0.96)`, duration 90ms

---

## 8. 질문 후 결과 화면 픽셀 명세

결과 화면은 전체 페이지를 교체하지 않고 동일한 `FRAME_APP_MOBILE` 안에서 전환한다. 캐릭터 DOM도 유지한다.

### 8.1 `CHUNK_HEADER` — 결과 상태

- 영역: `x=20, y=16, w=350, h=44`
- `UI_HEADER_BACK_BUTTON`: `x=20, y=20, w=40, h=40`
- back icon: `20 × 20px`, stroke 2px, `COLOR_DEEP_BLUE`
- `UI_HEADER_BRAND`: `x=86, y=20, w=218, h=36`, `TYPE_BRAND_RESULT`
- `UI_HEADER_INFO_BUTTON`: `x=330, y=20, w=40, h=40`
- info icon: `20 × 20px`, stroke 2px, `COLOR_MAIN_BLUE`
- 아이콘 버튼 배경: transparent
- 아이콘 버튼 focus: `FOCUS_RING`, radius 20px

### 8.2 `CHUNK_CHARACTER_STAGE` — 결과 상태

- `UI_CHARACTER_IMAGE` 시각 경계: `x=129, y=75, w=132, h=132` (헤더 아래 중앙 위치)
- stage hit/layout 영역: `x=0, y=44, w=390, h=148`
- `UI_CHARACTER_SHADOW`: `x=143, y=112, w=104, h=8`
- 그림자 색: `rgba(38, 71, 216, 0.08)`
- 캐릭터는 화면 스크롤 영역 밖에 고정한다.

### 8.3 `CHUNK_QUERY_BUBBLE`

- 기준 위치: `x=112, y=180, w=258, min-h=44` (캐릭터 발밑 우측 배치, 겹침 0%)
- 최대 너비: 258px
- 오른쪽 정렬: 20px (`right: 20px`)
- 패딩: `10px 16px`
- 배경: `COLOR_MAIN_BLUE` (`#2563eb`)
- 글자: `COLOR_WHITE`, Pretendard 600, 15px/22px
- radius: `18px 18px 4px 18px`
- 그림자: `0 4px 12px rgba(37, 99, 235, 0.2)`
- 긴 질문은 최대 4줄까지만 즉시 표시하고 그 이상은 자연스럽게 높이를 늘린다.

### 8.4 `CHUNK_ANSWER_VIEWPORT`

- viewport: `x=0, y=245, w=390, h=509` (질문 말풍선 아래 20px 간격 후 깔끔히 시작)
- 좌우 padding: 20px
- bottom padding: `90px + safe-area-inset-bottom`
- overflow-y: auto
- scrollbar: hidden
- overscroll-behavior: contain
- 새 `delta`가 추가될 때 사용자가 하단 80px 이내에 있으면 자동 스크롤한다.
- 사용자가 위로 스크롤했다면 강제로 아래로 끌어내리지 않는다.

### 8.5 `CHUNK_TERM_HEADER`

- card: `x=20, y=268, w=350, min-h=94`
- padding: `16px 16px 14px`
- 배경: `COLOR_SOFT_BLUE_BG`
- 경계: `1px solid COLOR_ICE_BLUE`
- radius: `RADIUS_LARGE`
- shadow: 없음

`UI_TERM_EYEBROW`:

- 문구: `한국은행 경제금융용어`
- `x=36, y=284, w=318, h=20`
- 타입: `TYPE_TERM_EYEBROW`

`UI_TERM_NAME`:

- 예시: `기준금리`
- `x=36, y=310, w=318, min-h=38`
- 타입: `TYPE_TERM_NAME`
- DB 검색 결과의 `term_name`을 사용한다. AI가 용어명을 만들지 않는다.

### 8.6 `CHUNK_ANSWER_CONTENT`

- card: term header 아래 12px
- 기준: `x=20, y=374, w=350, min-h=306`
- padding: `18px 16px`
- 배경: `COLOR_WHITE`
- 경계: `1px solid COLOR_BORDER`
- radius: `RADIUS_LARGE`
- shadow: `SHADOW_FLOAT`

각 섹션 공통:

- title row: `w=318, h=24`
- title: `TYPE_SECTION_TITLE`
- body margin-top: 8px
- body: `TYPE_BODY`
- 섹션 사이: `20px`
- 구분선: 첫 두 섹션의 하단에만 사용
- 구분선: `height=1px`, `background=COLOR_BORDER`, 위 16px, 아래 20px

섹션 순서와 고정 제목:

1. `📌 한 줄 정의`
2. `💡 쉬운 설명`
3. `🏠 생활 속 예시`

AI는 위 세 섹션의 Markdown `content`만 생성한다. 아이콘, 제목, 섹션 순서는 프론트에서 고정 렌더링해 답변마다 디자인이 달라지지 않게 한다.

### 8.7 스트리밍 표시

- `answer_start` 수신 즉시 term header와 빈 answer card를 만든다.
- `delta` 수신 시 현재 섹션 body에 텍스트를 이어 붙인다.
- 본문 끝에 `UI_STREAM_CARET`를 표시한다.
- caret: `w=2px, h=18px`, `COLOR_MAIN_BLUE`
- blink: 720ms, opacity 1 ↔ 0, steps(1,end)
- Markdown 파싱은 누적 버퍼 기준으로 하며 토큰마다 DOM 전체를 교체하지 않는다.
- 화면 업데이트는 `requestAnimationFrame`당 최대 1회로 묶는다.
- `answer_done` 수신 시 caret를 제거한다.

### 8.8 `CHUNK_SOURCE`

- 위치: answer card 아래 12px
- 영역: `x=24, w=342, min-h=20`
- label: `출처`
- label width: 36px, `TYPE_SUPPORT`, weight 600, color `TEXT_PRIMARY`
- value: 예시 `한국은행 경제금융용어 700선 · p.32`
- value: `TYPE_SUPPORT`
- 출처명과 페이지는 DB 검색 결과를 백엔드가 구성한다. AI 본문에서 추출하지 않는다.
- 페이지 값이 없으면 `· p.-`를 표시하지 않고 출처명만 표시한다.

### 8.9 `CHUNK_RELATED_TERMS`

- `answer_done` 이전에는 DOM을 만들지 않는다.
- card: source 아래 16px
- `x=20, w=350, min-h=104`
- padding: `16px`
- 배경: `COLOR_SOFT_BLUE_BG`
- 경계: `1px solid COLOR_ICE_BLUE`
- radius: `RADIUS_LARGE`
- title: `함께 보면 좋은 용어`, `TYPE_SECTION_TITLE`
- title 아래 간격: 12px
- button row: flex-wrap, gap 8px

`UI_RELATED_TERM_BUTTON`:

- 최소 높이: 44px
- 좌우 padding: 16px
- 최대 너비: 100%
- 배경: `COLOR_WHITE`
- 경계: `1px solid COLOR_ICE_BLUE`
- radius: `RADIUS_MEDIUM`
- 글자: `COLOR_DEEP_BLUE`, `TYPE_BUTTON`
- 클릭 시 해당 용어를 `POST /api/answers`로 즉시 전송한다.
- 직접 입력과 완전히 같은 요청·스트리밍 처리기를 사용한다.

---

## 9. 젤리 축소·표정 전환 모션 명세

### 9.1 핵심 구현 방식

`CHUNK_CHARACTER_STAGE`는 홈과 결과 화면에 각각 만들지 않는다. 앱 루트 바로 아래에 단 하나만 배치하고 화면 상태에 따라 transform과 표정 opacity만 변경한다.

기준 CSS 값:

```css
.ui-character-image {
  position: absolute;
  left: 103px;
  top: 155px;
  width: 184px;
  height: 184px;
  transform-origin: 50% 50%;
  will-change: transform, opacity;
  backface-visibility: hidden;
}

.app[data-screen="query-transition"] .ui-character-image,
.app[data-screen="searching"] .ui-character-image,
.app[data-screen="answer-streaming"] .ui-character-image,
.app[data-screen="answer-done"] .ui-character-image,
.app[data-screen="suggestions"] .ui-character-image,
.app[data-screen="failure"] .ui-character-image,
.app[data-screen="error"] .ui-character-image {
  transform: translate3d(26px, -82px, 0) scale(0.717391);
}
```

계산 근거:

- 시작 크기: 184px
- 결과 크기: 132px
- scale: `132 / 184 = 0.717391`
- 시작 좌표: `x=103, y=155`
- 결과 좌표: `x=129, y=75` (헤더 아래 중앙 위치)
- 이동량: `x +26px, y -82px`

transform으로만 이동·축소하므로 매 프레임 width, height, top, left를 변경하지 않는다. 이것이 레이아웃 재계산과 미세한 떨림을 줄인다.

### 9.2 질문 전송 타임라인

| 시간 | 캐릭터 | 화면 UI | easing |
| ---: | --- | --- | --- |
| 0ms | 현재 표정·크기 고정 | 전송 버튼 active | - |
| 0~90ms | 현재 표정 opacity 1→0, 눈 감은 표정 0→1 | 입력 dock scale 1→0.995→1 | `ease-out` |
| 90~150ms | 눈 감은 상태 유지 | 추천 질문과 안내 opacity 1→0 | `ease-out` |
| 120~520ms | `184→132px`, `x +26`, `y -93` 동시 변화 | 결과 header와 질문 말풍선 opacity 0→1 | `cubic-bezier(0.22, 1, 0.36, 1)` |
| 520~680ms | 눈 감은 표정 1→0, 생각 표정 0→1 | 검색 상태 문구 표시 | `ease-in-out` |
| 680ms~ | 생각 표정 100% 유지 | 스트림 대기 또는 수신 | - |

축소 duration은 정확히 `400ms`이다. 250ms 이하는 급작스럽고, 600ms 이상은 질문 전송이 느리게 느껴지므로 사용하지 않는다.

### 9.3 API 응답 속도와 모션 동기화

- POST 요청은 0ms에 즉시 시작한다. 애니메이션 종료까지 API 호출을 지연하지 않는다.
- `answer_start`가 680ms보다 빨리 도착하면 데이터를 버퍼에 보관하고 680ms부터 화면에 표시한다.
- `answer_start`가 늦게 도착하면 680ms 이후 생각 표정과 최소 로딩 문구를 유지한다.
- 검색 상태의 최소 표시 시간은 480ms, 최대 강제 시간은 두지 않는다.
- 네트워크가 빠르더라도 눈 감기와 축소 시퀀스는 한 번 완주한다.

### 9.4 답변 완료 타임라인

| 기준 시점 | 캐릭터 | UI |
| ---: | --- | --- |
| `answer_done + 0ms` | 생각 표정 유지 | caret 제거, 관련 용어 렌더링 |
| `+0~180ms` | 생각 표정 1→0, 기본 눈뜬 표정 0→1 | 관련 용어 opacity 0→1 |
| `+180~1080ms` | 기본 눈뜬 표정 유지 | 입력창 다시 활성화 |
| `+1080ms 이후` | 기본 표정 유지 | 추가 애니메이션 없음 |

질문에서 요구한 “눈을 감았다가 눈을 뜨는” 동작은 질문 전송 직후 닫고, 검색·스트리밍을 시작할 때 생각 표정의 열린 눈으로 전환하는 방식이다. 눈꺼풀을 CSS로 그리지 않고 실제 PNG 자산을 교차 페이드한다.

### 9.5 표정 교차 페이드

- 두 이미지가 같은 184 × 184px 원본 프레임을 공유한다.
- transition: `opacity 90ms ease-out` for close, `opacity 160ms ease-in-out` for reopen
- display를 즉시 `none`으로 바꾸지 않는다.
- crossfade 중 opacity 합이 1을 유지하도록 한다.
- 표정 교체와 축소 시작 사이에 최소 30ms를 둔다.
- 이미지 로딩 지연을 막기 위해 앱 시작 시 네 이미지를 preload한다.

### 9.6 모션 금지 사항

- spring, bounce, elastic easing 금지
- scale이 1보다 커지는 overshoot 금지
- 젤리 회전·기울임 금지
- 이동 경로를 곡선으로 만들지 않는다.
- 표정 변경 때 다른 크기나 좌표를 적용하지 않는다.
- shadow를 캐릭터 이미지 안에 합성하지 않는다.
- 로딩 중 반복적인 크기 변화, 호흡 효과, 둥둥 뜨기 금지

### 9.7 `prefers-reduced-motion`

```css
@media (prefers-reduced-motion: reduce) {
  .ui-character-image { transition-duration: 1ms !important; }
  .ui-character-expression { transition-duration: 1ms !important; }
  .ui-stream-caret { animation: none; opacity: 1; }
}
```

축소 전후 상태는 유지하되 중간 프레임을 생략한다.

---

## 10. 화면 전환 상태 머신

```text
HOME_IDLE
  ├─ input focus / suggestion click → HOME_TYPING + CURIOUS
  └─ submit(valid) → QUERY_TRANSITION + EYES_CLOSED

QUERY_TRANSITION
  └─ 680ms elapsed → SEARCHING + THINKING

SEARCHING
  ├─ answer_start → ANSWER_STREAMING
  ├─ suggestions → SUGGESTIONS
  ├─ failure → FAILURE
  └─ error → ERROR

ANSWER_STREAMING
  ├─ delta → append content
  ├─ answer_done → ANSWER_DONE + DEFAULT
  ├─ error → ERROR
  └─ done → close stream

ANSWER_DONE
  ├─ related term click → QUERY_TRANSITION
  ├─ new direct question → QUERY_TRANSITION
  └─ back → HOME_IDLE
```

중복 submit은 `QUERY_TRANSITION`, `SEARCHING`, `ANSWER_STREAMING` 상태에서 차단한다.

---

## 11. 검색 판정별 UI

### 11.1 답변 생성: 유사도 0.72 이상 또는 정확 일치

- 정상 결과 레이아웃을 사용한다.
- 정확 검색인지 벡터 검색인지는 사용자에게 별도 배지로 표시하지 않는다.
- 기술 용어 대신 공식 용어명과 출처를 우선 보여준다.

### 11.2 후보 안내: 0.55 이상 0.72 미만

- `CHUNK_STATUS_FEEDBACK`: `x=20, y=286, w=350, min-h=164`
- 배경: `COLOR_SOFT_BLUE_BG`
- 경계: `1px solid COLOR_ICE_BLUE`
- radius: `RADIUS_LARGE`
- padding: 20px
- 제목: `혹시 이 용어를 찾으셨나요?`, `TYPE_SECTION_TITLE`
- 설명: `질문과 가까운 용어를 골라주세요.`, `TYPE_SUPPORT`, margin-top 6px
- 후보 버튼: margin-top 16px, min-height 44px, gap 8px
- 후보 클릭 시 원문 질문을 재작성하지 않고 선택한 공식 용어로 동일 POST API를 호출한다.
- 캐릭터는 `CHARACTER_CURIOUS`를 표시한다.

### 11.3 검색 실패: 0.55 미만

- 제목: `관련 용어를 찾지 못했어요.`
- 설명: `용어 이름이나 약어를 조금 더 정확하게 입력해 주세요.`
- 보조 예시: `예: 기준금리, ESI, 고정금리부채권`
- 버튼: `다시 질문하기`
- 버튼 선택 시 입력창에 포커스를 이동하고 기존 질문은 선택 상태로 둔다.
- 캐릭터는 `CHARACTER_CURIOUS`를 표시한다.

### 11.4 기술 오류

- 제목: `답변을 불러오지 못했어요.`
- 설명: `잠시 후 다시 시도해 주세요.`
- 버튼: `다시 시도`
- 같은 요청을 자동 반복하지 않는다.
- 부분 스트리밍 본문이 있다면 삭제하지 않고 하단에 오류 안내를 붙인다.
- 캐릭터는 눈을 감은 상태로 180ms 전환 후 curious로 복귀한다.

---

## 12. POST 스트리밍 이벤트와 UI 연결

Endpoint: `POST /api/answers`  
Response Content-Type: `text/event-stream`

| Event | 필수 payload | UI 처리 |
| --- | --- | --- |
| `answer_start` | `term_name`, `source_name`, `source_page` | term header 생성, answer card 생성, 스트리밍 시작 |
| `delta` | `content` | 누적 Markdown 버퍼에 추가, caret 이동 |
| `answer_done` | `related_terms` | caret 제거, 관련 용어 표시, 캐릭터 눈뜸 |
| `suggestions` | `suggestions[]` | 후보 안내 화면 표시, 캐릭터 curious |
| `failure` | `message` | 실패 화면 표시 |
| `error` | `code`, `message` | 오류 화면과 재시도 표시 |
| `done` | 선택적 | reader 종료, 전송 잠금 해제 확인 |

### 12.1 프론트 처리 원칙

- 직접 입력과 연관 검색어 클릭은 동일한 `requestAnswer(query)` 함수를 사용한다.
- `fetch()` POST 후 `response.body.getReader()`로 읽는다.
- UTF-8 `TextDecoder`를 stream 모드로 사용한다.
- 이벤트 구분은 빈 줄 `\n\n`, 필드는 `event:`와 `data:`로 파싱한다.
- 한 네트워크 chunk에 여러 이벤트가 들어오거나 한 이벤트가 여러 chunk로 나뉘는 경우를 처리한다.
- `AbortController`를 요청마다 한 개 만든다.
- 뒤로가기 또는 새 요청 확정 시 기존 reader를 abort한다.
- `done`을 받기 전까지 전송 버튼을 disabled 처리한다.
- HTTP 오류와 stream 내부 `error` 이벤트를 분리 처리한다.

### 12.2 안전한 Markdown 렌더링

- 허용 요소: paragraph, strong, line break, unordered list
- HTML 원문은 렌더링하지 않고 escape한다.
- 외부 이미지, iframe, script, inline style을 허용하지 않는다.
- AI가 섹션 제목을 누락해도 프론트의 고정 섹션 구조는 유지한다.
- 용어명, 출처, 연관 검색어를 AI content에서 중복 표시하지 않는다.

---

## 13. 입력·키보드·스크롤 동작

- Enter: 전송
- Shift + Enter: 줄바꿈
- 빈 문자열 또는 공백만 있는 값: 전송 금지
- 전송 직전 앞뒤 공백만 제거한다. 화면에서 질문 문장을 임의로 고치지 않는다.
- 모바일 키보드가 열리면 `visualViewport.height`를 CSS 변수 `--viewport-height`에 반영한다.
- 입력 dock은 키보드 바로 위에 유지한다.
- 마지막 답변 하단에는 dock 높이 58px + 간격 24px + safe area만큼 padding을 둔다.
- 질문 전송 후 textarea는 비우지만 화면의 사용자 질문 말풍선은 유지한다.
- 스트리밍 중 입력창은 disabled 처리하되 opacity를 0.65 아래로 낮추지 않는다.
- 키보드가 열린 상태에서 전송해도 캐릭터 전환 좌표는 앱 viewport 기준으로 유지한다.

---

## 14. 반응형 규칙

### 14.1 390px 기준

이 문서의 좌표를 그대로 사용한다.

### 14.2 360~389px

- 앱 좌우 기준값을 `viewport width / 390` 비율로 통째로 축소하지 않는다.
- 좌우 콘텐츠 여백을 20px → 16px로 줄인다.
- 캐릭터 크기는 홈 176px, 결과 128px까지 축소 가능하다.
- 글자 크기는 유지한다.
- term card, answer card, input dock만 가용 너비에 맞춘다.

### 14.3 391px 이상

- 앱 프레임은 390px로 고정하고 가운데 정렬한다.
- 데스크톱용 추가 사이드 패널을 만들지 않는다.

### 14.4 높이 700px 미만

- 홈 추천 질문 영역을 스크롤 가능하게 한다.
- 캐릭터 홈 크기는 최소 156px까지 줄일 수 있다.
- 결과 화면은 header와 input dock만 고정하고 중앙 콘텐츠를 스크롤한다.

---

## 15. 접근성

- 모든 버튼의 최소 터치 영역: 44 × 44px
- 본문 대비: `TEXT_PRIMARY` on `WHITE` 또는 `SOFT_BLUE_BG`
- 버튼은 색 외에 텍스트·아이콘으로 목적을 표현한다.
- `UI_CHARACTER_IMAGE`는 장식 상태면 `alt=""`; 상태 안내가 필요하면 별도 `aria-live` 텍스트를 사용한다.
- 스트리밍 상태 aria-live: `polite`
- 오류 상태 aria-live: `assertive`
- 관련 용어 버튼은 `aria-label="{용어명} 다시 검색"`
- 포커스 표시를 outline none만으로 제거하지 않는다.
- back, info, send 아이콘은 SVG와 접근 가능한 label을 함께 사용한다.

---

## 16. 구현 구조 권장안

```text
AppShell
├─ Header
├─ CharacterStage                 # 화면 전체에서 한 번만 렌더링
│  ├─ CharacterExpressionLayers   # default/curious/closed/thinking
│  └─ CharacterShadow
├─ HomeView
│  ├─ Intro
│  ├─ Guide
│  └─ SuggestionButtons
├─ ResultView
│  ├─ UserQueryBubble
│  └─ AnswerViewport
│     ├─ TermHeader
│     ├─ AnswerContent
│     ├─ Source
│     ├─ RelatedTerms
│     └─ StatusFeedback
└─ InputDock
```

상태 예시:

```ts
type ScreenState =
  | 'home-idle'
  | 'home-typing'
  | 'query-transition'
  | 'searching'
  | 'answer-streaming'
  | 'answer-done'
  | 'suggestions'
  | 'failure'
  | 'error';

type CharacterState =
  | 'default'
  | 'curious'
  | 'eyes-closed'
  | 'thinking';
```

화면 레이아웃 상태와 캐릭터 표정 상태를 분리한다. 예를 들어 `answer-streaming` 화면에서 캐릭터는 `thinking`, `failure` 화면에서는 `curious`가 된다.

---

## 17. QA 검수 기준

### 17.1 픽셀·색상

- [ ] 기준 프레임이 390 × 844px인가?
- [ ] 모든 색상이 컬러 보드 토큰 또는 허용 alpha 값인가?
- [ ] 사용자 질문 배경이 `#405DE6`인가?
- [ ] 제목·로고 강조가 `#2647D8`인가?
- [ ] 기본 본문이 `#172033`인가?
- [ ] 보조 문구가 `#667085`인가?
- [ ] 카드 경계가 `#E4EAF2` 또는 지정된 `#DCEEFF`인가?
- [ ] 앱 좌우 여백이 결과 화면 20px, 홈 추천 영역 24px인가?
- [ ] 입력 dock이 358 × 58px이며 bottom 16px인가?

### 17.2 캐릭터

- [ ] 캐릭터 네 자산이 투명 PNG인가?
- [ ] 모든 표정이 같은 1254 × 1254px 캔버스인가?
- [ ] 질문 전송 90ms 안에 눈 감은 표정으로 바뀌는가?
- [ ] 캐릭터가 400ms 동안 184px에서 132px로 줄어드는가?
- [ ] 동시에 x +26px, y -93px 이동하는가?
- [ ] 축소 중 회전·바운스·overshoot가 없는가?
- [ ] 520~680ms에 생각 표정으로 자연스럽게 교차되는가?
- [ ] `answer_done` 후 180ms 안에 눈뜬 기본 표정으로 돌아오는가?
- [ ] 표정 변경 시 중심점이 2px 이상 흔들리지 않는가?

### 17.3 기능

- [ ] 추천 질문 클릭만으로 자동 전송되지 않는가?
- [ ] 직접 입력과 연관 용어가 같은 POST API를 쓰는가?
- [ ] `answer_start` 전에 빈 답변 카드가 나타나지 않는가?
- [ ] `delta`가 끊겨 도착해도 글자가 유실되지 않는가?
- [ ] `answer_done` 이후에만 연관 용어가 표시되는가?
- [ ] `suggestions`, `failure`, `error`가 각각 다른 문구와 동작을 갖는가?
- [ ] 스트리밍 중 중복 전송이 차단되는가?
- [ ] 사용자가 위로 스크롤한 경우 자동 스크롤이 방해하지 않는가?
- [ ] 뒤로가기 시 진행 중 reader가 중단되는가?

### 17.4 디자인 일관성

- [ ] 시작 화면과 결과 화면에서 같은 로고·폰트·입력창을 쓰는가?
- [ ] 카드 안의 카드가 2단계를 넘지 않는가?
- [ ] 불필요한 AI 아이콘·반짝이·그라데이션이 없는가?
- [ ] 답변 섹션이 항상 한 줄 정의 → 쉬운 설명 → 생활 속 예시 순서인가?
- [ ] 용어명·출처·연관 검색어가 AI content와 분리되어 있는가?
- [ ] 화면에 구현 목적과 무관한 버튼이나 메뉴가 없는가?

---

## 18. 완료 조건

다음 조건을 모두 만족하면 디자인 구현 완료로 본다.

1. 시작 화면에서 질문을 전송하면 옐로 메이트가 90ms 안에 눈을 감는다.
2. 눈을 감은 채 400ms 동안 결과 위치로 이동하며 184px에서 132px로 축소된다.
3. 축소가 끝나면 생각 표정으로 눈을 뜨고 검색·스트리밍 상태를 유지한다.
4. 스트리밍 완료 후 기본 눈뜬 표정과 관련 용어가 180ms 이내에 표시된다.
5. 화면의 모든 색상, 좌표, 크기, 시간값이 이 문서의 이름 있는 토큰 또는 컴포넌트 명세로 추적 가능하다.
6. 결과창이 시작 화면과 같은 화이트·블루·젤리 강조 체계를 유지한다.
7. `answer_start`, `delta`, `answer_done`, `suggestions`, `failure`, `error`, `done` 이벤트가 각각 정의된 UI 상태를 만든다.
8. 불필요한 AI 스타일 장식과 구현 목적 밖의 기능이 포함되지 않는다.

---

## 19. 모션 실행 로직 예시

아래 순서를 기준으로 구현한다. 타이머만 여러 개 흩어 놓지 않고 한 함수가 질문 전환을 소유해야 한다.

```ts
const MOTION = {
  closeEyesMs: 90,
  shrinkDelayMs: 120,
  shrinkMs: 400,
  thinkingStartMs: 520,
  thinkingFadeMs: 160,
  contentReleaseMs: 680,
  completeFadeMs: 180,
} as const;

let activeRequest: AbortController | null = null;
let earlyEvents: StreamEvent[] = [];
let canReleaseStream = false;

async function submitQuestion(rawQuery: string) {
  const query = rawQuery.trim();
  if (!query || isRequestLocked()) return;

  lockRequest();
  setUserQuery(query);
  setScreen('query-transition');
  setCharacter('eyes-closed');

  // API 요청과 화면 모션은 동시에 시작한다.
  activeRequest = new AbortController();
  const streamPromise = requestAnswerStream(query, activeRequest.signal, event => {
    if (!canReleaseStream) earlyEvents.push(event);
    else handleStreamEvent(event);
  });

  window.setTimeout(() => {
    document.documentElement.dataset.characterLayout = 'result';
  }, MOTION.shrinkDelayMs);

  window.setTimeout(() => {
    setScreen('searching');
    setCharacter('thinking');
  }, MOTION.thinkingStartMs);

  window.setTimeout(() => {
    canReleaseStream = true;
    earlyEvents.forEach(handleStreamEvent);
    earlyEvents = [];
  }, MOTION.contentReleaseMs);

  try {
    await streamPromise;
  } catch (error) {
    if (!isAbortError(error)) showTechnicalError();
  }
}

function handleStreamEvent(event: StreamEvent) {
  switch (event.type) {
    case 'answer_start':
      setScreen('answer-streaming');
      renderTermHeader(event.term_name, event.source_name, event.source_page);
      createAnswerContent();
      break;
    case 'delta':
      appendMarkdownDelta(event.content);
      break;
    case 'answer_done':
      finishAnswer();
      renderRelatedTerms(event.related_terms);
      setCharacter('default');
      setScreen('answer-done');
      break;
    case 'suggestions':
      renderSuggestions(event.suggestions);
      setCharacter('curious');
      setScreen('suggestions');
      break;
    case 'failure':
      renderFailure(event.message);
      setCharacter('curious');
      setScreen('failure');
      break;
    case 'error':
      renderError(event.code, event.message);
      setScreen('error');
      break;
    case 'done':
      unlockRequest();
      break;
  }
}
```

### 19.1 실제 transition 선언

```css
.ui-character-image {
  transition:
    transform 400ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 90ms ease-out;
}

.app[data-character-layout="result"] .ui-character-image {
  transform: translate3d(26px, -93px, 0) scale(0.717391);
}

.home-only {
  transition: opacity 150ms ease-out;
}

.app[data-screen="query-transition"] .home-only {
  opacity: 0;
  pointer-events: none;
}

.result-only {
  opacity: 0;
  transition: opacity 220ms ease-out 120ms;
}

.app:not([data-screen="home-idle"]):not([data-screen="home-typing"]) .result-only {
  opacity: 1;
}
```

### 19.2 이미지 preload

```html
<link rel="preload" as="image" href="assets/character-default.png">
<link rel="preload" as="image" href="assets/character-curious.png">
<link rel="preload" as="image" href="assets/character-thinking.png">
<link rel="preload" as="image" href="assets/character-complete.png">
```

preload가 실패해도 질문 전송 자체를 막지 않는다. 다만 첫 화면 렌더 전에 기본 이미지는 반드시 decode를 완료한다.

## 20. 2026-08-05 홈 상호작용 및 캐릭터 모션 개선 명세

### 20.1 추천 질문과 입력 Dock 사이 간격

- 홈 화면의 추천 질문 영역은 고정 `top` 좌표 대신 입력 Dock을 기준으로 배치한다.
- 마지막 추천 질문인 `ETF를 쉽게 설명해줘` 버튼 하단과 입력 Dock 상단 사이의 목표 간격은 `12px`이다.
- 입력 Dock의 높이 `58px`, 화면 하단 여백 `16px`, 추천 질문 하단 여백 `70px`을 기준으로 계산한다.
- `700px` 이하의 낮은 화면에서는 제목과 안내 문구를 위로 이동하고 추천 버튼 높이를 `44px`, 버튼 간격을 `6px`로 축소한다. 입력 Dock과 추천 질문이 겹치지 않는 것이 글자 크기 유지보다 우선한다.
- safe area가 있는 기기에서는 `env(safe-area-inset-bottom)`을 포함해 실제 터치 영역이 홈 인디케이터와 겹치지 않게 한다.

### 20.2 “이런 질문은 어때요?” 클릭 동작

- 추천 질문 버튼을 클릭하면 해당 문장을 입력창에 표시하는 동시에 동일 문장을 `submitQuestion(question)`에 전달한다.
- 추천 질문 클릭과 직접 입력 후 전송은 반드시 같은 요청 함수, 상태 전환, 오류 처리 경로를 사용한다.
- 클릭 직후 사용자 질문 말풍선에는 선택한 질문이 그대로 표시되어야 하며, 홈 화면에 머물지 않고 `query-transition`으로 이동한다.
- 중복 클릭 방지를 위해 `query-transition`, `searching`, `answer-streaming` 중에는 새 요청을 시작하지 않는다.
- 기존 요청이 있으면 해당 요청을 abort하고 남아 있는 표정/화면 전환 timer를 모두 해제한 뒤 새 요청을 시작한다.

### 20.3 연관 검색어 표시 방어 로직

- 정상 계약은 `related_terms: string[]`이지만, 과거 DB 데이터가 JSON 문자열(`"[\"기준금리\"]"`), PostgreSQL 배열 문자열(`"{기준금리,시장금리}"`), 쉼표 구분 문자열로 올 수 있다.
- 프런트엔드는 응답 직후 위 형식을 모두 `string[]`로 정규화한다. 빈 문자열과 공백 항목은 제거한다.
- 정규화된 배열만 본문 `관련 키워드`와 `함께 보면 좋은 용어` 버튼에 사용한다.
- 각 연관 검색어 버튼은 직접 질문과 동일한 `submitQuestion(term)`을 호출한다.
- 이 방어 처리는 표시 중 런타임 오류를 막기 위한 것이며, 원본 응답 스키마나 DB 저장 형식의 오류는 BE2에서 별도로 교정한다. `official_definition` 누락, RPC 실패, 잘못된 유사도 판정은 디자인 계층에서 해결하지 않는다.

### 20.4 첫 화면 기본 표정과 눈 깜빡임

- `character-default.png`를 눈을 뜬 기본 표정, `character-complete.png`를 눈을 감은 blink 프레임으로 사용한다.
- 첫 렌더는 눈을 뜬 상태에서 시작한다. `2.8~4.6초`의 불규칙한 간격 후 `150ms` 동안 눈을 감고 다시 기본 표정으로 돌아간다.
- 불규칙한 간격은 기계적인 반복감을 줄이되, 한 번의 blink 길이는 고정해 표정이 떨리는 것처럼 보이지 않게 한다.
- 홈 상태에서는 캐릭터 전체가 `3.2초` 주기로 최대 `3px` 상승하고 `0.8%` 확대되는 호흡 모션을 반복한다.
- 사용자가 질문을 전송하거나 홈을 벗어나면 blink timer를 즉시 해제해 로딩 표정 전환과 충돌하지 않게 한다.

### 20.5 질문·성공·실패 표정 상태표

| 상황 | 표정/자산 | 동작 |
|---|---|---|
| 홈 대기 | `default` ↔ `blink` | 불규칙한 눈 깜빡임과 미세 호흡 |
| 질문 전송 직후 | `blink` | 입력을 인지한 듯 눈을 감고 결과 위치로 축소 이동 |
| 검색 중 | `thinking` | 위를 바라보는 눈동자로 검색 상태 유지 |
| 답변 성공 | `default` | 기본 미소로 복귀하고 답변/연관 검색어 표시 |
| 후보/검색 결과 없음 | `error` | 당황 표정과 짧은 좌우 반응 1회 |
| 네트워크·API 오류 | `blink` → `error` | `140ms` 눈 감기 후 당황 표정으로 연결 |

### 20.6 답변을 불러오지 못했을 때의 움직임

- 오류가 확정되면 생각 표정에서 즉시 당황 표정으로 튀지 않고 `blink`를 `140ms` 거친다.
- 당황 표정이 나타날 때 캐릭터는 현재 결과 위치를 기준으로 좌우 `3px` 이내, scale `0.713~0.728` 범위에서 한 번만 반응한다.
- 반복 흔들기, 무한 진동, 큰 회전은 사용하지 않는다. 오류 메시지를 읽는 동안 캐릭터가 시선을 빼앗지 않아야 한다.
- 새 요청, 뒤로가기, 컴포넌트 unmount 시 abort controller와 모든 request timer를 해제한다. 이전 요청의 늦은 timer가 현재 화면의 표정을 덮어쓰면 안 된다.

### 20.7 접근성 및 모션 감소 설정

- `prefers-reduced-motion: reduce`에서는 호흡, 오류 반응, 장식 애니메이션을 중지하고 표정 교차 전환을 `1ms`로 줄인다.
- 표정 이미지는 장식 목적이지만 상태 의미를 보조하므로 각각 구체적인 한국어 대체 텍스트를 유지한다.
- 모션이 비활성화되어도 상태 문구, 오류 안내, 재시도 버튼만으로 전체 흐름을 이해할 수 있어야 한다.

### 20.8 QA 체크리스트

- [ ] 마지막 ETF 추천 질문과 입력 Dock 사이가 390 × 844 기준 약 `12px`인가?
- [ ] 추천 질문 클릭 한 번으로 선택 문장이 말풍선에 표시되고 검색이 시작되는가?
- [ ] 연관 검색어가 배열, JSON 문자열, PostgreSQL 배열 문자열일 때 모두 버튼으로 표시되는가?
- [ ] 첫 화면에서 눈을 뜬 상태로 시작해 자연스러운 간격으로 감았다 뜨는가?
- [ ] 검색 중에는 `thinking`, 성공 시에는 `default`, 실패 시에는 `error`가 표시되는가?
- [ ] API 오류 전환에서 blink 후 당황 표정과 짧은 1회 반응이 보이는가?
- [ ] 뒤로가기나 새 요청 후 이전 timer가 표정을 다시 변경하지 않는가?
- [ ] 모션 감소 설정에서 반복 애니메이션이 멈추는가?

## 21. 2026-08-06 결과 화면 레퍼런스 재분석 및 밀도 개선

> 이 절은 20절 이전의 홈/결과 좌표와 충돌할 경우 우선한다. 기준 이미지는 `852 × 1852px`, 구현 기준 viewport는 `390 × 844px`이다.

### 21.1 좌표 환산 기준

- 가로 환산 배율은 `390 / 852 = 0.457746`이다.
- 세로 환산 배율은 `844 / 1852 = 0.455724`이다.
- 레퍼런스의 좌표는 가로/세로 배율을 각각 적용한 뒤 1px 단위로 반올림한다.
- 레퍼런스가 약 `2.18x` 고밀도 캡처이므로 선 두께가 2px로 보이는 부분은 구현에서 대부분 `1px`을 사용한다.
- 결과 화면의 기준 좌표는 앱 프레임 내부 좌표이며 브라우저 창, 데스크톱 배경, 주소 표시줄은 포함하지 않는다.

### 21.2 레퍼런스 픽셀 측정표

| 요소 | 원본 이미지의 대략 범위(px) | 390px 환산 목표 | 구현값 |
|---|---:|---:|---:|
| 헤더 | `y 66~130` | `y 30~59` | `top 16`, `height 44` |
| 결과 캐릭터 | `x 282~567`, `y 196~438` | `x 129~260`, `y 89~200` | 원본 184px을 `0.717391` scale, `top 90` |
| 캐릭터 그림자 | `y 425~458` | `y 194~209` | `top 190`, blur 포함 약 14px |
| 질문 말풍선 | `x 518~822`, `y 476~572` | `x 237~376`, `y 217~261` | `top 218`, `right 20`, 콘텐츠 가변 폭 |
| 용어 카드 시작 | `x 41`, `y 604` | `x 19`, `y 275` | viewport `top 276`, 좌우 padding 20 |
| 용어 카드 폭 | `x 41~810` | `352px` | `350px` |
| 카드 외곽 radius | 약 `27px` | 약 `12px` | 시각 보정으로 `24px` 유지 |
| 출처 행 | `y 1437~1473` | `y 655~671` | 카드 직후 10px 간격, 콘텐츠 높이에 따라 흐름 배치 |
| 연관 용어 카드 | `y 1488~1662` | `y 678~757` | `padding 12`, 버튼 최소 높이 38px |
| 입력 Dock | `x 41~810`, `y 1685~1799` | `x 19~371`, `y 768~820` | `left 16`, `height 58`, `bottom 16` |

### 21.3 앱 전체 세로 길이와 흰 여백 제한

- `.frame-app-mobile` 높이는 `min(100dvh, 844px)`로 제한한다.
- 데스크톱 브라우저가 844px보다 높아도 앱 내부 UI가 함께 늘어나지 않는다. 추가 공간은 앱 바깥 회색 배경으로 남긴다.
- 모바일 화면이 844px보다 작을 때는 실제 `100dvh`를 사용한다. 최소 지원 높이는 640px이다.
- 첫 화면의 추천 질문 묶음은 입력 Dock 상단을 기준으로 배치해 마지막 ETF 버튼과 Dock 사이가 `12px`이 되도록 한다.
- 화면 높이가 커졌다는 이유로 캐릭터와 제목, 안내 문구, 추천 질문 사이 간격을 비례 확대하지 않는다.
- 흰 여백 축소는 요소를 무조건 위로 모으는 방식이 아니라 앱 최대 높이 제한과 Dock 기준 역방향 배치로 해결한다.

### 21.4 결과 캐릭터 위치

- 결과 상태에서도 캐릭터 DOM은 홈과 동일하게 유지한다.
- 홈 캐릭터 기준 박스는 `left 103px`, `top 155px`, `184 × 184px`이다.
- 결과 상태 transform은 `translate3d(26px, -82px, 0) scale(0.717391)`이다.
- 계산 결과 결과 캐릭터의 시각 기준 박스는 헤더 바로 아래 중앙인 약 `left 129px`, `top 75px`, `132 × 132px`이다.
- 결과 그림자는 `left 143px`, `top 112px`, `104 × 8px`로 캐릭터 하단 중앙에 맞춘다.

### 21.5 질문 말풍선과 답변/에러 피드백 카드 위치

- 질문 말풍선은 캐릭터 발밑 우측인 `top 180px`, `right 20px`, 최대 폭 `258px`이다.
- 답변 및 에러 피드백 스크롤 viewport는 `top 245px`에서 시작한다. 말풍선 하단과 에러/답변 카드 상단 사이 여백은 약 20px로 절대 겹치지 않는다.
- viewport 높이는 `calc(min(100dvh, 844px) - 245px)`이며 하단 입력 Dock을 피하도록 내부 bottom padding을 유지한다.
- 질문이 두 줄 이상이 되어 말풍선 높이가 늘어나면 답변 카드와 겹칠 수 있으므로 후속 개선에서 말풍선 실측 높이를 CSS 변수로 전달하는 방식을 고려한다. 현재 추천 질문과 일반적인 20자 내외 질문을 기준으로 한다.

### 21.6 답변 카드 내부 구조

- 답변 결과는 `chunk-term-card` 하나의 외곽 카드 안에 용어 헤더와 흰색 설명 카드를 배치한다.
- 외곽 카드: `350px` 폭, `padding 16px 12px 12px`, border `#A8C7FF 1px`, radius `24px`.
- 용어 헤더: 좌우 `4px`, 하단 `12px`; eyebrow 13px, 용어명 25px/34px.
- 흰 설명 카드: `326px` 폭, `padding 14px 12px`, radius `24px`.
- 설명 제목은 16px/22px, 본문은 14px/22px로 화면 높이 안에서 읽기성과 밀도를 함께 확보한다.
- `한 줄 정의`는 공식 정의의 첫 문장만 사용한다. 문장 종결 부호가 없으면 전체 정의를 사용한다.
- `쉬운 설명`은 현재 BE2가 제공하는 `official_definition`을 그대로 표시한다. BE3의 쉬운 설명 필드가 연결되면 이 영역만 교체한다.
- `함께 알아두기`는 연관 용어 최대 2개를 사용해 추가 탐색을 안내한다. 새로운 경제 사실을 프런트에서 생성하지 않는다.
- 각 설명 블록 사이 divider 여백은 위 `12px`, 아래 `14px`이다.

### 21.7 연관 용어 동작

- 응답의 `related_terms`는 화면 진입 전에 반드시 `string[]`로 정규화한다.
- 결과 카드 아래에는 최대 3개의 연관 용어를 표시한다. 390px 화면에서 2개일 때 두 버튼은 같은 폭으로 한 줄에 배치된다.
- 버튼 container는 `display:flex`, `flex-wrap:wrap`, gap `8px`이다.
- 각 버튼은 `flex: 1 1 120px`, 최소 높이 `38px`을 사용한다.
- 버튼 클릭 시 입력창에만 값을 넣지 않고 `submitQuestion(term)`을 즉시 호출한다.
- 클릭된 연관 용어는 새 `userQueryBubble`로 표시되고 기존 답변, 후보, 오류 메시지를 초기화한 뒤 `query-transition → searching → answer-done/suggestions/failure` 경로를 탄다.
- 새 연관 용어 요청을 시작할 때 기존 fetch는 abort하고 기존 request timer를 제거한다.
- 같은 용어가 중복 저장된 경우 추후 BE2에서 제거하는 것이 원칙이며, 프런트 key는 `${term}-${index}`로 충돌을 방지한다.

### 21.8 답변 데이터 경계

- 현재 결과 화면은 `/be2/vector-retrieve`의 `RetrievedTerm`을 사용한다.
- BE2가 제공하는 확정 데이터는 `term_name`, `official_definition`, `related_terms`이다.
- 레퍼런스의 `쉬운 설명`, `생활 속 예시`, 정확한 출처 페이지는 BE3 또는 원본 metadata가 제공해야 완전하게 채울 수 있다.
- 현 구현에서는 공식 정의를 한 줄 정의와 설명 영역에 안전하게 배치하고, 연관 용어 안내 문장 외의 새로운 사실을 만들지 않는다.
- BE3 연결 후 권장 응답 필드는 `one_line`, `easy_explanation`, `example`, `source_name`, `source_page`이며, 필드가 있으면 동일 레이아웃에 그대로 매핑한다.
- API 실패, 정의 누락, 잘못된 벡터 판정은 디자인 문제가 아니므로 오류 화면으로 분기한다.

### 21.9 결과 화면 QA 체크리스트

- [ ] 390 × 844에서 결과 캐릭터가 `top 90px` 부근에 위치하는가?
- [ ] 질문 말풍선이 `top 218px`, 답변 카드가 `top 276px`에서 시작하는가?
- [ ] 캐릭터, 말풍선, 카드가 서로 겹치지 않는가?
- [ ] 답변에 용어명, 한 줄 정의, 공식 설명, 출처가 표시되는가?
- [ ] 연관 용어 2개가 같은 폭의 버튼으로 한 줄에 배치되는가?
- [ ] 연관 용어 클릭 즉시 해당 용어 질문 말풍선과 새 검색 상태가 나타나는가?
- [ ] 844px보다 높은 화면에서도 앱 자체 높이와 내부 흰 여백이 늘어나지 않는가?
- [ ] 640~843px 화면에서는 답변 내용만 스크롤되고 헤더와 입력 Dock은 유지되는가?
- [ ] 긴 정의와 연관 용어 3개에서도 마지막 버튼이 입력 Dock 아래에 가려지지 않는가?
- [ ] 첫 화면 마지막 ETF 버튼과 입력 Dock 사이가 약 12px인가?

## 22. 2026-08-06 레퍼런스 사진 기준 844px 세로 높이 재확장 및 수직 요소 하향 배치 명세

### 22.1 레퍼런스 390 × 844px 세로 높이 기준 정밀 복원
- **기준 세로 높이**: `min(100dvh, 844px)`로 모바일 카드 프레임의 세로 높이를 원래의 풍성한 844px 규격으로 재확장한다.
- `EconomyMate` 헤더 브랜드를 포함한 상단 영역을 안정적으로 지지하고, 이하 요소를 레퍼런스 사진과 100% 동일하게 아래로 여유 있게 배치한다.

### 22.2 캐릭터, 타이틀, 추천질문 세션 하향 재배치
- **`CHUNK_CHARACTER_STAGE`**: 시각 박스를 `top: 155px, left: 103px` (크기 `184 × 184px`)에 위치시켜 젤리 캐릭터를 아래로 여유 있게 배치한다.
- **`CHUNK_HOME_INTRO`**: 메인 타이틀 `top: 360px` (크기 `26px/36px`, `#0f172a`), 서브 설명 `top: 442px`로 캐릭터 아래에 시각적 안정감을 부여한다.
- **`CHUNK_HOME_SUGGESTIONS`**: `top: 490px`로 추천 질문 영역을 전체적으로 아래로 내리고, 3개 알약 버튼 (`1.5px solid #2563eb`, 높이 `50px`, radius `9999px`)을 레퍼런스 사진과 동일한 비율로 배치한다.


