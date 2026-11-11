export const title = "바깥 참조 테이블 검사를 제거한 설계의 최단 반례";
export const state = (v) => {
  if (!v.overlapSafe) return "바깥 참조 테이블에 SP 쓰기를 허용함";
  const depth = Object.keys(v.active).length;
  if (v.event === "prepare") return depth ? "바깥 실행 중 SP SQL을 준비함" : "바깥 SQL을 준비함";
  if (!depth) return "활성 SQL이 없음";
  return depth === 1 ? "바깥 SQL을 실행 중" : "SP SQL을 실행 중";
};
export const step = (action) => ({
  Prepare: "SQL을 준비함",
  Execute: "준비한 SQL을 실행함",
  Return: "SQL 실행이 끝남",
  ErrorUnwind: "오류로 호출을 복귀함",
  Done: "실행을 마침",
}[action] ?? action);
export const group = (v) => v.overlapSafe ? "safe" : "broken";
export const colors = { safe: "blue", broken: "pink" };
