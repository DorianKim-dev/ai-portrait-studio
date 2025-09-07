# 🎭 AI 사진관 (AI Portrait Studio)

> 사진 한 장으로 여권/증명 규격부터 모델·여행·K‑pop·판타지·밈까지 실사 품질 초상 이미지를 즉시 생성합니다.

## ✨ 주요 기능

- 📸 **규격 사진**: 여권/증명 3:4, 얼굴·눈높이 자동 정렬 → 실사용 수준 결과
- 🎨 **25가지 테마**: Resume, Passport, Memory, Model, K‑pop, Actor, Travel, Activity, Profession, Wedding, Graduation, Traditional, Retro, Sports, Musician, Film, Lookbook, Makeover, Animal, Lifestage, TimeTravel, Cosmos, Fantasy(Real/Anime), Anime, Meme
- 📱 **편리한 UX**: 카메라/업로드, 젠더 표현 토글, 원클릭 생성, 갤러리/다운로드
- 🔧 **자동 프레이밍**: 전신/3/4/상반신/근접을 테마별 가중 랜덤, 결과 사이즈 자동 정규화

## 🚀 빠른 시작

### 필수 요구사항
- Python 3.8+
- Google Gemini API Key

### 1. 프로젝트 복제
```bash
git clone https://github.com/DorianKim-dev/ai-portrait-studio.git
cd ai-portrait-studio
```

### 2. 백엔드 설정
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. API 키 설정
```bash
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
```

### 4. 서버 실행
```bash
# 백엔드 서버 (터미널 1)
uvicorn server:app --reload --port 8001

# 프론트엔드 서버 (터미널 2)
python -m http.server -d frontend 5173
```

### 5. 웹 앱 접속
브라우저에서 `http://localhost:5173/?api=http://localhost:8001` 접속

## 🏗️ 프로젝트 구조

```
ai-portrait-studio/
├── backend/
│   ├── server.py          # FastAPI 메인 서버
│   ├── requirements.txt   # Python 의존성
│   └── uploads/          # 업로드된 이미지 저장소
├── frontend/
│   ├── index.html        # 메인 웹 페이지
│   ├── app.js           # 메인 애플리케이션 로직
│   ├── components.js    # UI 컴포넌트
│   └── styles.css       # 스타일시트
└── docs/
    └── Submission.md    # 프로젝트 제출 문서
```

## 🎯 사용법

1. **📷 사진 준비**: 카메라로 촬영하거나 이미지를 업로드하세요
2. **🎨 테마 선택**: 원하는 테마 버튼을 클릭하면 즉시 생성됩니다
3. **⬇️ 다운로드**: 결과 이미지를 다운로드하거나 갤러리에서 확인하세요

## 🤖 Nano Banana (Gemini 2.5 Flash) 활용

이 앱은 **Nano Banana (Gemini 2.5 Flash Image Preview)**를 핵심 이미지 생성기로 사용합니다. 사용자 사진과 테마별 프롬프트를 REST API로 전송하여 실사 품질의 초상화를 즉시 생성합니다.

### 주요 특징:
- 🎯 **정확한 신원 보존**: 원본 얼굴 특징 유지
- ⚡ **빠른 생성 속도**: 실시간 결과 제공
- 🎨 **다양한 스타일**: 25가지 테마별 맞춤 프롬프트
- 📏 **규격 자동 정렬**: 여권/증명 사진 3:4 비율 및 얼굴 위치 자동 조정

## 🛠️ 기술 스택

- **Backend**: FastAPI, Python, Pillow, OpenCV
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **AI**: Google Gemini 2.5 Flash Image Preview
- **Deployment**: Uvicorn, Python HTTP Server

## 📝 라이선스

이 프로젝트는 **CC BY 4.0** 라이선스 하에 공개됩니다 (상업적 이용 허용).

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 문의

프로젝트 관련 문의사항이 있으시면 [Issues](https://github.com/DorianKim-dev/ai-portrait-studio/issues)를 통해 연락해 주세요.

---

<div align="center">
  <strong>🎭 AI 사진관으로 당신만의 특별한 초상화를 만들어보세요! </strong>
</div>

