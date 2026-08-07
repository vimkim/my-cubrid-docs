#!/bin/bash
# quiz-1 실행기: 버려도 되는 개발용 DB 이름을 인자로 받는다.
# 이 스크립트는 sx_quiz1_t 테이블만 만들고 지운다. 기존 객체는 건드리지 않는다.
set -eu
DB="${1:?사용법: bash run.sh <버려도-되는-DB이름>}"
cd "$(dirname "$0")"
csql -u dba "$DB" -i promote_quiz.sql
