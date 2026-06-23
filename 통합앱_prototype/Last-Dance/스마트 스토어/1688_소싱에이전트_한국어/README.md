# 1688 Sourcing Agent

Codex Desktop에서 `@sourcing-agent-1688`로 1688 상품을 찾고, Chrome에 열린 상품 페이지를 분석하고, 이미지/영상 자료 저장까지 도와주는 소싱 에이전트입니다. Windows와 macOS 둘 다 같은 설치 명령을 사용합니다.

Chrome DevTools 연결로 사용자가 이미 로그인해서 쓰는 Chrome의 1688 화면, DOM, 네트워크 응답을 읽고 상품 정보, 판매자 정보, 이미지, 영상 후보, 상세 자료를 정리합니다.

## 설치

아래 명령 하나만 실행하세요.

```powershell
uvx --from git+https://github.com/Squirbie/sourcing-agent-1688.git sourcing-agent-1688 install-codex
```

이 명령은 Codex에 플러그인과 필요한 MCP 서버를 등록합니다.

설치가 끝나면 Codex Desktop을 완전히 종료한 뒤 다시 켜고, 새 채팅에서 `@sourcing-agent-1688`를 선택하세요.

설치 상태를 바로 확인하려면:

```powershell
uvx --from git+https://github.com/Squirbie/sourcing-agent-1688.git sourcing-agent-1688 doctor
```

Windows에서 Codex CLI가 `[WinError 5] 액세스가 거부되었습니다`로 막히면 직접 등록 모드로 설치하세요.

```powershell
uvx --from git+https://github.com/Squirbie/sourcing-agent-1688.git sourcing-agent-1688 install-codex --manual-windows-install --verify
```

## 처음 한 번: Chrome 연결

설치 직후 한 번만 Chrome 연결 허용이 필요할 수 있습니다. 이 연결은 Chrome DevTools 기반으로 동작하며, 기본값은 새 프로필이 아니라 평소 쓰는 로그인된 Chrome 세션입니다.

1. 평소 1688에 로그인해서 쓰는 Chrome 프로필에서 `chrome://inspect/#remote-debugging`을 엽니다.
2. Remote debugging 연결을 켭니다.
3. Codex Desktop을 다시 시작합니다.
4. 새 채팅에서 `@sourcing-agent-1688`를 부르고, Chrome이 허용창을 띄우면 `Allow`를 누릅니다.

상품 링크를 주면 Chrome에서 그 페이지를 열어 분석합니다. 키워드 검색을 요청하면 1688 탭이 없어도 Chrome에 검색 탭을 열고 후보를 찾습니다.

허용창을 못 봤거나 연결이 안 되면 아래처럼 설정 절차를 다시 확인할 수 있습니다.

```text
@sourcing-agent-1688 Chrome 연결 설정 다시 열어줘.
```

Windows에서 기존 Chrome 세션 연결이 계속 실패할 때만 전용 복구 Chrome 창을 직접 시작하세요. 이 방식은 별도 프로필이라 로그인/쿠키가 공유되지 않으므로 1688 실사용 소싱 기본값으로는 권장하지 않습니다.

```powershell
uvx --from git+https://github.com/Squirbie/sourcing-agent-1688.git sourcing-agent-1688 chrome-devtools start
```

이 명령은 `http://127.0.0.1:9222/json/version`이 실제로 응답할 때만 연결 준비 완료로 기록합니다.

PowerShell에서 `npx.ps1 cannot be loaded because running scripts is disabled on this system` 오류가 보이면, Windows 설치 cache의 `chrome-devtools` MCP 명령이 `npx.cmd`로 보정되어야 합니다. 위 설치 명령을 다시 실행한 뒤 `doctor`로 확인하세요.

## 이렇게 쓰면 됩니다

```text
@sourcing-agent-1688 지금 Chrome에 열어둔 1688 상품을 셀러 입장에서 분석해줘.
```

```text
@sourcing-agent-1688 이 상품의 이미지, 옵션, 판매자 정보, 영상 자료 확인해줘.
```

```text
@sourcing-agent-1688 1688에서 스마트폰 거치대 소싱 후보 찾아보고 비교해줘.
```

```text
@sourcing-agent-1688 1688에서 여행용품 후보 10개 찾아줘. 가격, 판매량, 회두율, 판매자, 원화 추정가를 같이 정리해줘.
```

```text
@sourcing-agent-1688 이 페이지 자료 저장하고 manifest 경로 알려줘.
```

## 플러그인이 하는 일

- 기존 Chrome 세션에서 1688 검색/상품 페이지 확인
- 상품명, 가격, 판매량, 옵션, 판매자 정보 추출
- 대표 이미지, 상세 이미지, 영상 URL 추출
- Chrome 네트워크 응답에서 추가 상품 데이터 확인
- 저장 요청 시 HTML, 이미지, 속성 JSON, manifest 저장
- 한국어 키워드를 1688 검색용 중국어 키워드로 확장

## 저장 위치

기본 저장 위치는 사용자 홈 아래입니다.

```text
~/.sourcing1688/
  assets/
  data/
  raw/
```

## 삭제

Codex 설정과 MCP 등록을 한 번에 지우려면:

```powershell
uvx --from git+https://github.com/Squirbie/sourcing-agent-1688.git sourcing-agent-1688 uninstall-codex
```

저장 데이터까지 같이 지우려면:

```powershell
uvx --from git+https://github.com/Squirbie/sourcing-agent-1688.git sourcing-agent-1688 uninstall-codex --remove-runtime
```
