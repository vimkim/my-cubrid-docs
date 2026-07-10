ppt oos simplified 를 읽어보니

wide row 의 narrow head 이런 언어가 이해가 잘 안가. 쉽게 바꿔줘

---

AS-IS 에서, recdes 가 만약 하나의 DB page (보통 16K)보다 클 경우 overflow page 라는 특수한 페이지로 이동하는데,
페이지 당 하나의 recdes 만 들어갈 수 있으므로 (즉 하나의 recdes가 16K 크기의 여러 페이지 점유) 내부 단편화가 심한 문제를 지적해줘.

그리고 그러한 overflow page 에서 int 값 4byte 를 읽으려면 결국 모든 recdes를 다 가져와야 해서 모든 페이지를 다 읽어야 하므로 IO가 발생하는 것이 극단적인 나쁜 케이스임을 명시해줘.

---
