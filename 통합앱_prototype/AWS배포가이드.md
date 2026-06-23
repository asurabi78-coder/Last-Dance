# 스마트스토어 통합앱 — AWS Lightsail 배포 가이드

> 목표: 앱을 항상 켜진 서버에 올려 **어디서나 접속**. 비밀번호로 보호.
> 작성: 2026-06-23

---

## 0. 시작 전 꼭 알 점 (보안)

- 이 앱은 키만 누르면 **스마트스토어에 상품을 올리고 API 비용을 씁니다.** 공개 URL이 되므로 **반드시 `APP_PASSWORD`를 설정**해야 합니다(설정해야 로그인 화면이 뜸).
- **API 키는 절대 코드/이미지에 넣지 말고, 서버의 "환경변수"로만 주입**합니다. (`.dockerignore`가 `.env`를 제외하도록 이미 설정됨)
- 비용: Lightsail 컨테이너 서비스 Nano 기준 약 **월 $7**(변동 가능).

---

## 1. 내 PC에 필요한 것

1. **AWS 계정** (없으면 aws.amazon.com에서 가입)
2. **Docker Desktop** 설치 — docker.com/products/docker-desktop
3. **AWS CLI** 설치 후 `aws configure`로 액세스 키 등록 — aws.amazon.com/cli

---

## 2. 환경변수 목록 (배포 시 입력할 값)

서버에 아래 값을 환경변수로 넣습니다. 키 값은 기존 `.env` 파일에서 복사하세요.

```
APP_PASSWORD            ← 새로 정함(로그인 비밀번호)
NAVER_AD_ACCESS_LICENSE
NAVER_AD_SECRET_KEY
NAVER_AD_CUSTOMER_ID
NAVER_CLIENT_ID
NAVER_CLIENT_SECRET
OPENAI_API_KEY
ANTHROPIC_API_KEY
GEMINI_API_KEY
REMOVE_BG_API_KEY
DOMEGGOOK_API_KEY
NAVER_COMMERCE_CLIENT_ID
NAVER_COMMERCE_CLIENT_SECRET
```
(필요 시 `ANTHROPIC_MODEL=claude-sonnet-4-6` 도 추가)

---

## 3. 이미지 빌드 (내 PC, 프로젝트 폴더에서)

PowerShell에서 프로젝트 폴더로 이동 후:

```powershell
cd "C:\Users\user\Desktop\Last Dance\통합앱_prototype"
docker build -t smartstore-app .
```

빌드가 끝나면 로컬에서 한 번 테스트(비밀번호 포함):

```powershell
docker run -p 8501:8501 -e APP_PASSWORD=test123 smartstore-app
```

브라우저에서 `http://localhost:8501` → 로그인 화면이 뜨고 `test123`으로 들어가지면 정상. (Ctrl+C로 종료)

---

## 4. Lightsail 컨테이너 서비스 생성 & 배포

### 4-1. 컨테이너 서비스 만들기
- AWS 콘솔 → **Lightsail** → **Containers** → **Create container service**
- 리전: Seoul(ap-northeast-2) 권장, Power: **Nano**, Scale: 1
- 서비스 이름: 예) `smartstore`

### 4-2. 이미지 푸시 (PC에서)
```powershell
aws lightsail push-container-image --region ap-northeast-2 --service-name smartstore --label app --image smartstore-app
```
출력에 나오는 이미지 참조명(예: `:smartstore.app.1`)을 복사.

### 4-3. 배포 설정 (콘솔)
- 컨테이너 서비스 → **Deployments** → **Create your first deployment**
- Container 이름: `app`
- Image: 4-2에서 복사한 참조명
- **Open ports**: `8501` / HTTP
- **Environment variables**: 2번 목록의 키들을 하나씩 추가 (`APP_PASSWORD` 포함)
- **Public endpoint**: container `app`, port `8501`
- **Health check path**: `/healthz`
- Save & deploy

### 4-4. 접속
- 배포가 Running이 되면 상단에 **공개 HTTPS URL**(예: `https://smartstore.xxxx.ap-northeast-2.cs.amazonlightsail.com`)이 생깁니다.
- 그 주소로 어디서나 접속 → 로그인 → 사용.

---

## 5. 코드 수정 후 재배포

코드를 고쳤으면 다시:
```powershell
docker build -t smartstore-app .
aws lightsail push-container-image --region ap-northeast-2 --service-name smartstore --label app --image smartstore-app
```
그 뒤 콘솔에서 새 이미지 참조명으로 다시 Deploy.

---

## 6. 주의 / 팁

- **로그인 비밀번호(`APP_PASSWORD`)는 꼭 설정**하세요. 안 하면 게이트가 비활성이라 누구나 접근 가능합니다.
- 저장함(saved/)·사용량 로그는 컨테이너 안에 쌓이며, 재배포 시 초기화될 수 있습니다. 영구 보관이 필요하면 별도 스토리지(S3 등) 연동이 필요합니다(추후 작업).
- "24시간 자동 업로드"는 이 위에 스케줄러/워커를 더 얹어야 합니다. 그 전에 PC에서 **실제 업로드(3b) 1건 성공 확인**이 먼저입니다.

---

## 대안: 더 쉬운 무료 경로 (Streamlit Community Cloud)

서버 관리가 부담되면, 코드를 GitHub(비공개)에 올리고 **share.streamlit.io**에서 배포하면 무료로 "어디서나 접속"이 됩니다. 비밀키는 Streamlit **Secrets**에 넣고, `APP_PASSWORD`도 Secrets로 설정하면 동일하게 로그인 보호됩니다. 원하시면 이 경로 가이드도 따로 만들어 드립니다.
