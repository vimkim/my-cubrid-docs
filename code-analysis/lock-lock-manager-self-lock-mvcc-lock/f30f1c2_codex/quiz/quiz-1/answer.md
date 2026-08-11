# Answer 1 — 잠금 지도와 한계

Locked read의 대상 class에는 IX, 선택 instance에는 X가 필요하며 owner는 같은 transaction이다. IX는 “하위에 exclusive 성격의 lock이 있다”는 의도이지 row의 X를 대신하지 않는다. 서로 다른 row의 두 X는 instance key가 달라 직접 충돌하지 않고 class IX끼리 호환된다.

같은 owner의 class S에 IX를 더하면 conversion table의 SIX가 필요하다. Conversion은 한 resource의 mode 변화이고 escalation은 여러 instance locks를 class S/X로 대체하는 정책이다. Escalation은 entry/lookup 비용을 줄이지만 더 넓은 class 범위의 concurrency를 잃을 수 있다.

한 실행의 dump는 모든 conversion/escalation branch나 starvation freedom을 증명하지 않는다. OID, `tran_index`, MVCCID를 같은 숫자 체계로 취급해서도 안 된다.

흔한 오답은 IX를 row lock 자체로 보는 것, `tran_index`를 OID/MVCCID와 같은 identity로 보는 것, 한 dump가 escalation overhead를 정량화했다고 보는 것이다. 이 Quiz는 conversion·escalation을 실행하지도, entry overhead를 측정하지도 않는다. OID와 dump order는 run마다 달라도 괜찮고 same-owner class IX/instance X 관계가 채점점이다.
