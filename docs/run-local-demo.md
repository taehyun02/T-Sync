# T-Sync 로컬 실행 가이드

## 1. 먼저 알아둘 점

### `db_pgdata`를 계속 써도 되나요?
네. `docker-compose.yml`에서 Postgres 볼륨은 외부 볼륨 `db_pgdata`를 사용하고 있으므로, 이미 적재한 데이터가 있으면 그대로 유지됩니다. 즉 컨테이너를 다시 올려도 볼륨을 삭제하지 않는 한 데이터는 남아 있습니다.

### 왜 importer를 한 번에 돌리지 않고 나눠서 실행하나요?
공공데이터 API는 호출량이 많아지면 `429 Too Many Requests`가 발생할 수 있습니다. 특히 `routes -> stations -> vehicles`를 한 번에 연속 호출하면 두 번째나 세 번째 단계에서 제한에 걸릴 가능성이 있습니다. 그래서 데모 준비 단계에서는 `routes`, `stations`, `vehicles`를 각각 나눠 실행하는 쪽이 더 안정적입니다.

## 2. 권장 실행 방식

### 백엔드/DB 컨테이너 실행
프로젝트 루트에서 아래 명령어를 실행합니다.

```powershell
docker compose up -d postgres backend
```

필요하면 importer도 단독 실행할 수 있지만, 데모 준비 중에는 아래처럼 `run --rm` 방식으로 필요한 적재만 실행하는 편이 좋습니다.

## 3. 데이터 적재 권장 순서

### 1단계. 노선 적재
```powershell
docker compose run --rm -e SYNC_TARGET=routes importer
```

### 2단계. 정류장 적재
```powershell
docker compose run --rm -e SYNC_TARGET=stations importer
```

### 3단계. 차량 위치 적재
```powershell
docker compose run --rm -e SYNC_TARGET=vehicles importer
```

## 4. 적재 확인

브라우저 또는 API 테스트 툴에서 아래를 확인합니다.

```text
http://localhost:8000/health
http://localhost:8000/routes
http://localhost:8000/vehicles
```

정상이라면 `/health`는 `{"status":"ok"}` 를 반환하고, `/routes` 와 `/vehicles` 는 데이터가 표시됩니다.

## 5. 프론트 실행

### 프론트 환경변수 설정
`frontend/.env.example`를 참고해서 `frontend/.env.local` 파일을 만들고 아래 값을 넣습니다.

```env
VITE_API_BASE_URL=http://localhost:8000
```

### 프론트 실행 명령
```powershell
cd frontend
npm install
npm run dev
```

기본 주소는 아래와 같습니다.

- 프론트: `http://localhost:5173`
- 백엔드: `http://localhost:8000`

## 6. 데모 점검 순서

프론트 화면에서 아래 순서로 테스트합니다.

1. 현재 탑승 노선 선택
2. 목표 환승 노선 선택
3. 차량 선택
4. 환승 정류장 선택
5. 이동 프로필 선택
6. 환승 성공 확률 계산 실행

정상이라면 성공 확률, 위험도, 환승 여유시간, 대안 전략이 함께 표시됩니다.

## 7. 429가 계속 날 때 팁

1. `routes` 적재 후 1~2분 쉬었다가 `stations` 실행
2. `stations` 적재 후 다시 쉬었다가 `vehicles` 실행
3. 한 번에 `docker compose up importer` 로 몰아서 처리하지 않기
4. 데모 직전에는 `vehicles`만 최신으로 다시 적재하기

## 8. 참고

현재 `docker-compose.yml`의 importer는 `SYNC_TARGET`을 외부 환경변수로 받도록 바꿨습니다. 그래서 필요할 때마다 `-e SYNC_TARGET=...` 로 명시해서 적재 대상을 바꿔 실행하면 됩니다.
