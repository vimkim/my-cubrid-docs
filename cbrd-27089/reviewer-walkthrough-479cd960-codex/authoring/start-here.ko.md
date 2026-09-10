# PR #7600: OOS 값을 쓰기 전에 파티션을 고른다

이 변경의 핵심은 하나다. **행이 들어갈 heap을 먼저 정하고, 그 heap의 OOS 파일에 값을 쓴다.** 행 하나를 따라가 보자. 전체 코드 설명은 마지막에 연결해 두었다.

## 1. 행 하나를 따라가 보자

파티션 테이블은 행을 여러 자식 테이블에 나누어 저장한다. 이 예제에서는 `id`가 10보다 작으면 `p0`에, 나머지는 `p1`에 넣는다.

각 자식 테이블에는 행을 저장하는 공간이 있다. 이를 **heap**이라고 한다.

컬럼 값은 행 밖에 따로 저장할 수도 있다. CUBRID는 이를 **OOS**라고 한다. 행 안에는 값 자체 대신 **값이 저장된 위치 정보**를 남긴다. 여기서 ‘참조를 따라 읽는다’는 말은 그 위치로 가서 값을 읽는다는 뜻이다. 따로 저장한 값은 해당 heap에 연결된 OOS 파일에 들어간다.

이제 `id = 1`인 행에 64바이트 값을 넣는다. 이 테스트는 작은 값도 OOS에 저장하도록 강제한다. 1은 10보다 작으므로 행이 들어갈 곳은 `p0`다.

<details><summary>예제 SQL 펼치기</summary>

```sql
CREATE TABLE t_oos_show_part (
  id INT, data_col BIT VARYING STORAGE FORCE_OUTLINE
) PARTITION BY RANGE (id) (
  PARTITION p0 VALUES LESS THAN (10),
  PARTITION p1 VALUES LESS THAN MAXVALUE
);
INSERT INTO t_oos_show_part VALUES (1, REPEAT(X'EE', 64));
COMMIT;
```

`STORAGE FORCE_OUTLINE`은 이 테스트에서 OOS를 사용하게 한다. `REPEAT(X'EE', 64)`는 저장할 테스트 값을 만든다.

</details>

## 2. 무엇이 잘못됐나?

기존 코드는 **`p0`를 고르기 전에** OOS 값을 쓸 수 있었다.

그때는 아직 root 테이블을 OOS 소유자로 사용했다. root는 INSERT 문에 적은 테이블이다. 그러면 저장 위치가 이렇게 나뉠 수 있다.

- 행: `p0`의 heap에 저장된다.
- OOS 값: root heap의 OOS 파일에 저장된다.

이 잘못된 상태에서 SELECT를 실행하면 어떻게 될까?

1. `p0`에서 `id = 1`인 행을 읽는다.
2. 행 안의 위치 정보를 읽는다. 이 정보는 root의 OOS 파일에 저장된 값을 가리키고 있다.
3. 그 위치에서 64바이트 값을 읽어 반환한다.

값을 읽을 때는 행에 기록된 위치로 찾아갈 수 있다. 따라서 **OOS 값을 root 쪽에 잘못 저장했어도, SELECT 결과는 맞을 수 있다.**

하지만 이 행은 `p0`에 들어갔다. 따라서 OOS 값도 **`p0` heap에 연결된 OOS 파일**에 저장해야 한다. 이 문서에서 ‘`p0`가 OOS 데이터를 소유한다’는 말은 이 저장 관계를 뜻한다.

오래된 데이터를 지우는 vacuum은 이 관계를 전제로 동작한다. `p0`의 행을 정리할 때는 `p0` heap에 연결된 OOS 파일을 찾는다. 그런데 이 예제에서는 OOS 값이 root 쪽에 있고, `p0`에는 OOS 파일조차 없다. 읽기에 성공한 행이라도 정리할 때 문제가 생기는 이유다.

## 3. PR은 무엇을 바꾸나?

이제 파티션 키로 목적지를 먼저 고른다. 이 예제의 파티션 키는 `id = 1`이다.

순서는 다음과 같다.

1. 키를 보고 `p0`를 고른다.
2. 행을 만들면서 `p0`를 소유자로 지정해 OOS 값을 쓴다.
3. 완성된 행으로 목적지를 다시 확인한 뒤, 행을 저장한다.

마지막 확인은 그대로 남는다. 두 번 고른 목적지가 다르면 오류를 반환한다. OOS 소유자를 정한 뒤에 행을 다른 heap으로 보내면 안 되기 때문이다.

## 4. 코드에서는 어디를 보면 되나?

처음에는 두 곳만 읽자. 모든 보조 함수를 먼저 알 필요는 없다.

**목적지를 고르는 곳:** `locator_attribute_info_force` 안의 `partition_prune_insert_by_attrinfo` 호출이 자식 테이블을 고르고 `write_destination`에 결과를 넣는다. 그 다음 행을 만드는 호출에 이 목적지를 전달한다. [해당 코드 읽기](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/transaction/locator_sr.c#L7775).

**그 목적지를 OOS 소유자로 쓰는 곳:** OOS 쓰기 호출은 다음 식으로 소유자를 고른다.

```cpp
oos_class_oid != NULL ? oos_class_oid : &attr_info->class_oid
```

뜻은 간단하다. 별도로 받은 OOS 소유자가 있으면 그것을 쓴다. 없으면 기존 속성 정보의 클래스를 쓴다. [해당 호출 읽기](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_file.c#L12888).

소유자를 별도로 전달하므로, 나머지 작업에 필요한 원래 클래스 정보도 유지할 수 있다.

## 5. 테스트는 이 버그를 어떻게 잡나?

테스트는 먼저 저장한 값이 그대로 읽히는지 확인한다. 그 다음 **어느 heap에 OOS 데이터가 있는지** 확인한다.

- Root: OOS 파일 없음. OOS chunk 0개.
- `p0`: OOS 파일 있음. OOS chunk 1개.
- `p1`: OOS 파일 없음. OOS chunk 0개.

여기서 chunk는 OOS에 저장된 데이터 조각이다. 이 검사는 값이 읽히는 것뿐 아니라, OOS 소유자가 올바른지도 확인한다. [테스트 읽기](https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/unit_tests/oos/sql/test_oos_sql_show.cpp#L437).

위 내용은 테스트 코드가 확인하는 조건이다. 이 안내서를 만들면서 엔진 테스트를 다시 실행하지는 않았다. 이 사례 하나가 모든 UPDATE, rollback, vacuum 경로를 증명하지는 않는다.

## 상세 코드로 가기 전에

**반환된 값이 맞는지 확인한 뒤에도, 왜 OOS 파일을 확인해야 할까?**

<details><summary>답 펼치기</summary>

SELECT는 **“저장한 64바이트 값이 다시 나오는가?”**를 확인한다. `p0`의 행이 root 쪽 값의 위치를 가리키고 있어도 이 검사는 통과할 수 있다.

그래서 테스트는 `SHOW ALL HEAP OOS`로 **“그 값이 들어 있는 OOS 파일은 root의 것인가, `p0`의 것인가?”**도 확인한다.

이 예제의 정답은 `p0`에 OOS 파일과 chunk 1개가 있고, root에는 없는 상태다. 값이 맞게 읽히는 것과, 값이 있어야 할 곳에 저장된 것을 각각 확인하는 것이다.

</details>

이 예제를 이해한 다음에는 [전체 참고 문서](review.ko.html)에서 UPDATE, effective-key 보조 함수, 중복 키 확인용 임시 행을 차례로 읽으면 된다. 전체 diff 63개 블록은 필요할 때 찾아보면 된다. 이 예제를 읽기 위한 선행 지식은 아니다.

소스 기준: `479cd960ec`. 비교 기준: `f4299ac0cd`.
