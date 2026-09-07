# DB 스키마 / 초기 데이터

`db-setup-overlay.zip`에서 가져온 SQL을 그대로 재사용합니다 (내용은 문제없었고,
설치 방식만 "Ansible로 노드에 직접 설치" → "K8s ConfigMap으로 MySQL 컨테이너에 주입"으로 변경).

- `schema.sql`: patients / doctors / appointments / records / prescriptions 테이블
- `init_data.sql`: 샘플 초기 데이터

## K8s에 반영하는 방법

```bash
kubectl create configmap mysql-initdb -n hospital \
  --from-file=schema.sql=docs/schema.sql \
  --from-file=init_data.sql=docs/init_data.sql
```

이렇게 만든 `mysql-initdb` ConfigMap을 `k8s/10-mysql-statefulset.yaml`의
`mysql-initdb` 볼륨이 그대로 참조합니다 (파일 이름 순서대로
`/docker-entrypoint-initdb.d/`에 마운트되어 MySQL 컨테이너 최초 기동 시 자동 실행됨).
