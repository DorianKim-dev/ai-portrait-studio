# AI 사진관 (AI Portrait Studio) — 제출 문서

## 1) 프로젝트 개요
- 한 줄: 사진 한 장으로 여권/증명 규격부터 모델·여행·K‑pop·판타지·밈까지 실사 품질 초상 이미지를 즉시 생성합니다.
- 핵심 흐름: 업로드/촬영 → 테마 원클릭 → 실사 결과. 규격 테마는 자동 크롭·정렬(3:4, 눈높이/머리 비율) 적용.

## 2) 데모 링크
- 데모 영상(최대 2분): https://youtu.be/R3ckX0cq1AU
- 실행 데모: (라이브 웹 데모 미제공 시) GitHub 저장소 + 로컬 실행 가이드 사용
- 리포지토리: https://github.com/DorianKim-dev/ai-portrait-studio

## 2-2) Kaggle Writeup 최종 본문(복붙용)

- 프로젝트 제목
  - AI Portrait Studio: One‑Click Real‑World & Cinematic Portraits

- 문제 설명 (≤ 200 words, EN)
  - This app uses Nano Banana (Gemini 2.5 Flash Image Preview) as the core image generator/editor. We send a user photo with a compact, theme‑specific prompt via the REST generateContent endpoint and receive a PNG in inlineData. Prompts enforce photorealism, identity preservation, and strict “no text/logos/watermarks,” while specifying lighting, background, attire, and composition per theme (e.g., passport, resume, model, travel, sports, film). For regulated formats (passport/resume), the server post‑processes the output to a 3:4 canvas with face‑center alignment and eye‑line positioning to produce consistent, ready‑to‑use images. For creative themes, the server randomizes full/three‑quarter/half/close framing, then normalizes final size for a clean gallery. The system instruction further biases safe, realistic outputs and disallows unsafe or branded content. This combination demonstrates practical control of a fast multimodal model: it blends stylistic direction (lighting, tone, setting) with realistic constraints (identity, anatomy, color) and lightweight server policies. As a result, the demo is both useful (ID photos that fit conventions) and delightful (high‑variety themes), highlighting Nano Banana’s strengths in fast, controllable, photorealistic generation.

- 데모 영상(공개 URL)
  - https://youtu.be/R3ckX0cq1AU

- 공개 프로젝트 링크
  - GitHub: https://github.com/DorianKim-dev/ai-portrait-studio
  - (선택) 라이브 웹 데모 URL이 있으면 함께 첨부

- 특징 요약 (KO)
  - 규격 사진: 3:4, 얼굴·눈높이 자동 정렬(반신 프레이밍으로 어깨선/명치까지 보이게)
  - 실사 테마 다수: Model/Profession/Wedding/Traditional/Travel/Activity/Film/K‑pop/Retro/Musician/Anime/Fantasy/Meme 등
  - 매수 선택: 1–3장, 중복 방지(고유 샷만)
  - 안전/브랜드 정책: 텍스트·숫자·로고·워터마크 금지
  - 신원 일관성: 얼굴 클로즈업 참조를 함께 전달해 동일 인물 유지 강화

— 위 본문을 Kaggle “새 글 작성”에 그대로 붙여 넣고, 영상/링크를 확인 후 제출하세요.

## 2-1) 제출 가이드(What/How to Submit)
- Kaggle Writeup 작성·제출
  - 대회 페이지 → “새 글 작성” → 제목·본문 입력 후 저장 → 우측 상단 “제출”
  - 본문에 다음 3가지를 반드시 포함
    1) 프로젝트 요약(아래 200단어 설명을 활용) 2) 영상 링크(YouTube 등 공개, 로그인 불필요) 3) 실행 가능한 공개 링크(Web 또는 GitHub+실행 가이드)
  - 제출은 1건만 인정되지만, 제출 취소·수정·재제출은 마감 전까지 무제한 가능
- 비디오 데모(필수)
  - 2분 이내, 공개 접근(로그인 불필요) 링크를 글에 첨부
- 공개 프로젝트 링크(필수)
  - 웹 데모 URL(권장) 또는 GitHub 공개 저장소(+자세한 실행 가이드)
  - 로그인/결제 없이 접근 가능해야 함

## 3) 실행 방법 (로컬)
- Backend (FastAPI)
  1. `cd backend && python -m venv .venv && source .venv/bin/activate`
  2. `pip install -r requirements.txt`
  3. `export GEMINI_API_KEY="<YOUR_KEY>"`
  4. `uvicorn server:app --reload --port 8000`
- Frontend (Static)
  1. `python -m http.server -d frontend 5173`
  2. 브라우저에서 `http://localhost:5173/?api=http://localhost:8000` 접속

## 4) 주요 기능
- 규격 사진: 여권/증명 3:4, 얼굴·눈높이 자동 정렬 → 실사용 수준 결과.
- 실사 테마: Resume, Passport, Memory, Model, K‑pop, Actor, Travel, Activity, Profession, Wedding, Graduation, Traditional, Retro, Sports, Musician, Film, Lookbook, Makeover, Animal, Lifestage, TimeTravel, Cosmos, Fantasy(Real/Anime), Anime, Meme.
- 프레이밍: 전신/3/4/상반신/근접을 테마별 가중 랜덤, 결과 사이즈 자동 정규화.
- UX: 카메라/업로드, 젠더 표현 토글, 원클릭 생성, 갤러리/다운로드, 오류 메시지 및 경고 툴팁(이미지 미선택 시 표시).

## 5) Nano Banana(Gemini 2.5 Flash Image Preview) 활용 요약 (≤ 200 words)
This app uses Nano Banana (Gemini 2.5 Flash Image Preview) as the core image generator/editor. We send a user photo with a compact, theme‑specific prompt via the REST generateContent endpoint and receive a PNG in inlineData. Prompts enforce photorealism, identity preservation, and strict “no text/logos/watermarks,” while specifying lighting, background, attire, and composition per theme (e.g., passport, resume, model, travel, sports, film). For regulated formats (passport/resume), the server post‑processes the output to a 3:4 canvas with face‑center alignment and eye‑line positioning to produce consistent, ready‑to‑use images. For creative themes, the server randomizes full/three‑quarter/half/close framing, then normalizes final size for a clean gallery. The system instruction further biases safe, realistic outputs and disallows unsafe or branded content. This combination demonstrates practical control of a fast multimodal model: it blends stylistic direction (lighting, tone, setting) with realistic constraints (identity, anatomy, color) and lightweight server policies. As a result, the demo is both useful (ID photos that fit conventions) and delightful (high‑variety themes), highlighting Nano Banana’s strengths in fast, controllable, photorealistic generation.

## 6) 데이터/정책 준수
- 외부 자료: 공개적으로 접근 가능한 리소스만 사용. 유료/폐쇄 데이터 불사용.
- 안전/브랜드: 텍스트·숫자·로고·워터마크 금지 지시와 서버 정책 적용. 위험 행위/유해 표현 배제.

## 7) 라이선스/공개 (수상 시)
- 코드 및 산출물: CC BY 4.0 공개 동의(상업적 이용 허용).

## 8) 체크리스트
- [ ] 2분 영상 업로드(로그인 없이 공개) 및 URL 기입
- [ ] 실행 데모 URL 또는 설치/실행 가이드 제공
- [ ] Nano Banana 활용 설명(본 문서 200단어 섹션)
- [ ] 규격 사진 샘플 + 다양한 테마 샘플 스크린샷 첨부(선택)
- [ ] README에 환경 변수/모델 ID/로컬 실행 명시

---

## 부록 A) Kaggle 등 제출용 200단어 요약 (KO)
AI 사진관은 Nano Banana(Gemini 2.5 Flash Image Preview)를 핵심으로 사용하는 실사 초상 생성 앱입니다. 사용자는 사진 한 장을 업로드하거나 카메라로 촬영한 뒤, 테마 버튼을 누르기만 하면 결과를 즉시 얻을 수 있습니다. 규격이 필요한 여권/증명 사진은 서버 후처리로 3:4 비율, 얼굴 정렬, 눈높이 기준을 맞추어 실사용에 가까운 결과를 제공합니다. 모델/여행/스포츠/필름/전통/레트로/판타지/애니/밈 등 창의 테마는 조명·배경·의상·구도 가이드를 포함한 프롬프트로 실사 톤을 유지하면서도 높은 다양성을 확보합니다. 모든 프롬프트에는 신원 보존과 “텍스트/로고/워터마크 금지”가 포함되며, 서버 정책도 이를 강화합니다. 또한 프레이밍(전신/3/4/상반신/근접)을 테마별 가중 랜덤으로 구성하고, 결과 이미지는 일관된 해상도로 정규화하여 갤러리에서 깔끔하게 비교·다운로드할 수 있습니다. 본 프로젝트는 빠른 반응성과 제어 가능성을 강조하며, 실용(규격 사진)과 재미(다양 테마) 모두를 아우르는 경험을 제공합니다. 이를 통해 Nano Banana의 “빠른 생성, 실사 품질, 컨텍스트 제어” 장점을 효과적으로 시연합니다.

## 부록 B) 배포(권장)
- Backend(Cloud Run 등): 환경변수 `GEMINI_API_KEY` 설정, CORS 허용.
- Frontend(Vercel/정적 호스팅): `?api=<백엔드 URL>` 또는 `window.API_BASE` 주입.
