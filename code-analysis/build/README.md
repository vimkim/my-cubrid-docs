# CUBRID build and tooling analyses

Created: 2026-10-21. Last modified: 2026-10-27 (Asia/Seoul).

This collection moved from `build-analysis/` on 2026-10-21. It covers build
performance, dependency reuse, and personal build coordination. Findings and
design proposals remain tied to each report's inspected revision and environment.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [debug-gcc-vs-clang-clean-build-analysis_2026-08-13.md](debug-gcc-vs-clang-clean-build-analysis_2026-08-13.md) | Clean-build compiler timings, experiments, and limitations | 2026-08-13 | 2026-10-21 | Assess ways to reduce debug_gcc build time |
| [cubrid-third-party-ci-cache-design_2026-09-22.md](cubrid-third-party-ci-cache-design_2026-09-22.md) | Kubernetes CI third-party cache alternatives and validation | 2026-09-22 | 2026-10-21 | Design reusable dependency builds across clean CI runs |
| [cubrid-build-coordinator-analysis_2026-10-20.md](cubrid-build-coordinator-analysis_2026-10-20.md) | Coordinator behavior, locking, and Python extraction proposal | 2026-10-20 | 2026-10-21 | Explain the existing script and its extraction boundary |
| [cubrid-ci-ccache-statistics-note_2026-10-21.md](cubrid-ci-ccache-statistics-note_2026-10-21.md) | PR별 ccache hit율 해석, 통계 기록 설정과 실제 로그 근거 | 2026-10-21 | 2026-10-21 | CI 담당자에게 실행별 캐시 통계 확인을 요청하기 위해 작성 |
| [ccache-per-build-stats-log-guide_2026-10-27.md](ccache-per-build-stats-log-guide_2026-10-27.md) | 빌드별 STATSLOG 사용법, NOSTATS 관계, 버전별 기능과 PR #8254 전환 조건 | 2026-10-27 | 2026-10-27 | PR #8254 승인 시 공식 통계 기능의 후속 검토 자료로 공유하기 위해 작성 |
| [cubrid-ci-compiler-cache-survey-plan_2026-10-27.md](cubrid-ci-compiler-cache-survey-plan_2026-10-27.md) | 현재 공유 캐시, 최신 ccache·sccache 대안, CBRD-27124 검증 공백과 후속 실험 계획 | 2026-10-27 | 2026-10-27 | 캐시 대안의 운영 적합성을 비교하기 위한 예비 조사로 작성 |
