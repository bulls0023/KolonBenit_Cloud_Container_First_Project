# Kuspital — 온프레미스 기반 원무서비스 인프라 구축

> IaC · K8s 기반 고가용성 인프라 설계 및 CI/CD 자동화 구축
> 6인 팀 프로젝트 (2026-06-25 ~ 2026-07-23, 약 4주) · **GitLab-Jenkins-Harbor CI 연동 & 웹 프론트엔드 담당**

---

## 프로젝트 개요

병원 원무서비스(예약·진료·처방)를 가정한 온프레미스 인프라를 처음부터 설계하고 구축한 프로젝트다. 네트워크 계층(라우팅·망분리)부터 컨테이너 오케스트레이션(K8s), 배포 자동화(CI/CD), 모니터링까지 인프라 전 계층을 팀원 6명이 나눠 맡았다.

팀은 두 트랙으로 구성됐다.

- **인프라 기반 설계 & DevOps**: 네트워크 토폴로지, 방화벽/라우팅 정책, IaC(Ansible), CI/CD 파이프라인
- **클러스터 구축 & Back/Front 개발**: K8s 클러스터 배포, WAS(Flask)·DB·프론트엔드 개발

### 프로젝트 선정 이유

의료 데이터를 다루는 서비스라는 설정 아래, 국내 법령(의료법 제23조, 개인정보 보호법 제24·29조, 보건복지부 EMR 인증 고시, 전자금융감독규정 제15조)이 요구하는 **망분리·암호화·접근 통제** 요건을 실제 인프라 설계에 반영하는 것을 프로젝트 목표로 잡았다. 이 요건을 근거로 Web(1-Tier) · WAS(2-Tier) · DB(3-Tier)를 물리적으로 분리하고, 각 계층 사이에 방화벽으로 허용 포트/발신지를 제한하는 3-Tier 구조를 설계했다.

### 진행 순서

| 단계 | 내용 | 도구 |
|---|---|---|
| 1. 인프라 기반 설계 | 네트워크 토폴로지 선정, IP 서브넷팅, 방화벽/라우팅 정책 확정 | Cisco, pfSense |
| 2. IaC 구축 | 여러 노드의 OS 설정·패키지 설치를 코드로 일괄 자동화 | Ansible |
| 3. K8s 클러스터 구축 | 고가용성 마스터/워커 노드 아키텍처 배포 | Kubernetes, Docker, Harbor |
| 4. CI/CD 구축 | 컨테이너 무중단 배포 파이프라인 작성 | GitLab, Jenkins, ArgoCD |
| 5. 풀스택·모니터링 | 3-Tier 서비스 구성, 관측성 확보 | Nginx, Flask, MySQL, Grafana |

---

## 인프라 아키텍처

### 네트워크 설계

내부망은 OSPF + MPLS(Label Switching) 기반 백본으로 구성해 IP 대역을 외부에 노출하지 않도록 했고, 두 개의 AS(LER1/LER2)를 BGP로 연동했다. 외부 접점은 DMZ에 pfSense 방화벽과 Nginx를 두어 1차로 걸렀다.

```
[사용자] → DMZ(방화벽 + Nginx) → MPLS 백본(OSPF/BGP, Label Switching) → LAN
```

LAN 내부는 GitLab → Jenkins → Harbor → ArgoCD → K8s 순서로 CI/CD 도구 체인이 이어지고, K8s 클러스터 안에 WAS(Flask, 2개 인스턴스를 upstream으로 이중화) · DB(MySQL) · 정적 서비스가 배포되는 구조다.

### 물리 구성 (일부)

| 서버 | 역할 | IP |
|---|---|---|
| Ansible | IaC 실행 | 10.10.1.100 |
| K8s | 클러스터 노드 | 10.10.1.110 |
| DevOps | Docker, Harbor, Grafana | 10.10.1.120 |
| GitLab | 소스 저장소 | 10.10.1.125 |
| WAS ×2 | Flask 애플리케이션 (이중화) | 10.10.1.20 / 10.10.1.22 |
| DB | MySQL | 10.10.1.10 |
| Web | Docker, Nginx (DMZ) | 10.100.1.10 |

WAS를 2대로 이중화하고 앞단에서 upstream으로 분산시켜, 노드 하나가 죽어도 서비스가 끊기지 않도록 설계했다.

---

## 기술 스택

| 영역 | 도구 |
|---|---|
| 네트워크/인프라 | Cisco, pfSense |
| 가상화/OS | VMware, EVE-NG, Ubuntu |
| 자동화(IaC) | Ansible |
| 컨테이너 | Kubernetes, Docker, Flannel(CNI), Helm |
| DevOps/CI/CD | GitLab, Jenkins, Harbor, Trivy, ArgoCD |
| 서비스 | Nginx, Flask, MySQL |
| 모니터링 | Grafana, Loki, Prometheus |

---

## 담당 파트 — GitLab·Jenkins·Harbor 연동 & 프론트엔드

전체 CI/CD 체인(`GitLab → Jenkins → Harbor → ArgoCD → K8s`) 중 **앞단(소스~이미지 저장소)의 CI 연동**과, 파이프라인이 배포하는 대상인 **웹 프론트엔드 제작**을 담당했다. 뒷단의 ArgoCD 기반 K8s 배포 자동화(GitOps)는 클러스터 구축 담당 팀원의 영역이었다.

### 1. GitLab — Jenkins 연동

GitLab 저장소에 코드가 push되면 Jenkins가 이를 감지해 빌드를 트리거하도록 연동했다. Jenkins Credential에 GitLab 접근 정보를 등록하고, 웹훅 또는 폴링 방식으로 두 도구가 통신하도록 구성해 "커밋 → 자동 빌드 시작"까지의 흐름을 만들었다.

```
GitLab(소스 push) → Jenkins(감지 + 빌드) → Harbor(이미지 등록 + Trivy 스캔)
```

### 2. Jenkins — Harbor 연동

Jenkins 빌드 결과물(컨테이너 이미지)을 사내 레지스트리인 Harbor에 자동으로 push하도록 연동했다. Jenkins에 Harbor 인증 정보를 등록해 별도 수동 로그인 없이 이미지를 업로드할 수 있게 했고, Harbor에 등록된 이미지는 Trivy로 자동 스캔되어 CVE(취약점) 목록을 확인할 수 있는 상태로 이어지도록 만들었다.

### 3. 파이프라인 동작 검증

`git push` 한 번으로 GitLab → Jenkins → Harbor까지 자동으로 이어지는지 직접 시연으로 검증했다. 로컬에서 코드 일부(배포 시각을 남기는 문구)를 수정한 뒤 push하면, Jenkins가 즉시 빌드를 시작하고 새 이미지가 Harbor에 등록되는 전체 흐름을 눈으로 확인했다.

### 4. 웹 프론트엔드 제작

병원 원무서비스 화면(예약 조회, 진료 기록, 처방전 조회 등)의 프론트엔드를 제작했다. 정적 페이지 기반으로 구성해, 백엔드(Flask WAS)가 제공하는 API와 연동되는 형태로 만들었고, 이 프론트엔드가 곧 CI/CD 파이프라인을 통해 실제 배포되는 대상이었다.

---

## 성과 및 검증

- GitLab에 코드를 push하면 Jenkins가 자동으로 빌드를 시작하고, 결과 이미지가 Harbor에 등록되는 CI 흐름이 실제로 동작하는 것을 시연으로 확인했다.
- Harbor에 등록된 이미지에 대해 Trivy 취약점 스캔 결과(CVE 목록, CVSS 점수)를 조회해, 배포 전 이미지 상태를 점검할 수 있는 체계를 팀 차원에서 확보했다.
- 직접 제작한 프론트엔드가 이 파이프라인을 통해 실제로 배포되는 것까지 end-to-end로 확인했다.

---

## 향후 과제 (팀 논의 기준)

- 현재는 원무(Administrative) 영역만 단일 구성했으나, 진료(Clinical)·후방(back-office) 영역까지 확장해 서로 맞물리는 인프라로 발전시킬 필요가 있다.
- 현재 통신 구간에 SSL/HTTPS가 적용되지 않아, Let's Encrypt 인증서 발급이나 로드밸런서 단의 인증서 적용을 통해 HTTPS를 강제하는 작업이 남아 있다.
- 접속 로그 보관, 전자서명 연동, 환자정보 DB 암호화(AES-256 이상) 등 EMR 인증제·ISMS-P 수준의 보안 요건 반영이 다음 단계 과제로 남아 있다.

---

## 배운 점

네트워크 설정 하나, 게이트웨이 설정 하나가 전체 파이프라인을 멈출 수 있다는 것을 이번 프로젝트에서 직접 겪었다. CI/CD는 코드 배포 도구 몇 개를 연결하는 작업이 아니라, 그 아래 네트워크와 클러스터가 정상적으로 통신 가능해야 성립하는 구조라는 것을 체감했다. `git push` 한 번으로 빌드부터 배포까지 자동으로 이어지는 것을 확인했을 때, 인프라 전체가 유기적으로 연결되어 있다는 감각을 얻었다.
