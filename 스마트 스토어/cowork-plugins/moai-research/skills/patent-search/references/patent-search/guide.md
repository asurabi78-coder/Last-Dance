# 특허 검색 가이드

## KIPRIS Plus REST API 호출

```
GET http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/freeSearchInfo
  ?word={검색어}
  &ServiceKey={KIPRIS_API_KEY}
```

## IPC 주요 분류코드

| 코드 | 분야 |
|------|------|
| A | 생활필수품 |
| B | 처리조작, 운수 |
| C | 화학, 야금 |
| G | 물리학 |
| H | 전기 |

## 검색 팁
- 키워드 + IPC 조합으로 정확도 향상
- 출원인 검색: 경쟁사 특허 포트폴리오 파악
- 등록번호 검색: 정확한 특허 1건 조회
