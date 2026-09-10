"""Four Korean reviewer tours, with source citations supplied by build.py."""
def build_graphs(link):
    p='src/query/partition.c'; h='src/storage/heap_file.c'; l='src/transaction/locator_sr.c'
    q='src/query/query_executor.c'; t='unit_tests/oos/sql/test_oos_sql_show.cpp'
    def node(id,title,summary,details,files=(),hunk=None):
        n=dict(id=id,title=title,summary=summary,details=details,kind='구현 설명')
        if files:n['files']=[dict(path=f'{f}:{line}',url=link(f,line),note=note) for f,line,note in files]
        if hunk:n['links']=[dict(label=f'전체 diff와 설명 · H{hunk:02d}',url=f'review.ko.html#hunk-{hunk:02d}')]
        return n
    def graph(id,label,color,summary,nodes,edges,tours):
        for i,n in enumerate(nodes):
            n.update(x=(i%2)*420,y=(i//2)*245,width=340,height=160,summaryLines=5)
            if id=='system-overview':n.update(height=205,summaryLines=7,kind='기본 개념')
        return dict(id=id,label=label,color=color,summary=summary,nodes=nodes,
                    edges=[dict(source=a,target=b,label=c,**({'url':link(d,e)} if d else {})) for a,b,c,d,e in edges],
                    tour=[dict(nodeId=n['id'],title=n['title'],body=body) for n,body in zip(nodes,tours)])
    overview=[
      node('row','Heap record와 attribute','Heap은 row를 저장한다. 가변 attribute는 inline 값 또는 OOS inline stub으로 표현된다. Record의 HAS_OOS는 stub 존재를 나타낸다.', ['Row의 논리값과 heap에 저장되는 bytes는 다를 수 있다.','작은 heap record를 읽은 뒤 필요한 큰 값만 attribute layer에서 Resolve한다.']),
      node('partition','Root와 child heap','Partition root는 공통 schema와 routing 규칙을 제공한다. 실제 row는 선택된 child heap에 저장된다. Root와 child의 heap 식별자는 서로 다르다.', ['Partition expression의 결과를 RANGE·LIST·HASH 규칙에 적용한다.','Root를 대상으로 한 문장과 특정 child를 명시한 문장은 검증 조건이 다르다.']),
      node('chain','OOS file과 value chain','Heap 하나에 OOS file이 최대 하나 연결된다. 하나의 serialized attribute가 한 개 이상의 chunk record로 저장되며 stub이 head OOS OID를 가진다.', ['HFID는 heap, VFID는 file, OID는 object 주소다.','OOS locator bytes와 외부 BLOB/CLOB payload는 다른 저장 객체다.']),
      node('transform','준비와 직렬화','Assignment, default, 이전 record의 값을 모아 저장 형식으로 바꾼다. Type codec, pending increment, LOB locator copy가 이 경계와 결합되어 있다.', ['준비 과정은 memory allocation과 값의 상태 변경을 수반할 수 있다.','읽을 기준인 class identity와 실제 저장할 목적지는 별개의 역할이다.']),
      node('lifetime','Transaction과 vacuum','MVCC의 이전 version은 old reader에게 필요할 수 있다. Transaction rollback과 vacuum은 서로 다른 시점과 이유로 저장 객체의 수명을 처리한다.', ['Logical value를 읽는 것과 물리적 file 소유권을 검사하는 것은 다른 관찰이다.','SA 실행과 SERVER_MODE의 concurrent reader·vacuum 실행은 검증 범위가 다르다.'])]
    data=[
      node('intent','출발점: 소유권 일치','새 record의 child heap과 OOS chain의 owner heap이 같아야 한다.', ['이전 transform-first 경로는 root에 chain을 쓴 뒤 record를 child로 보낼 수 있었다.','이번 diff에는 변경된 spec 파일이 없다. 외부 JIRA와 accepted ADR은 배경 근거이며 최신 실행 순서는 HEAD 소스로 확인한다.'],[(l,7768,'Main write의 새로운 순서')],54),
      node('key','Key만 독립적으로 준비','Assignment·default·old key 중 실제 저장될 값을 복사본으로 만든다.', ['Pending INCR/DECR는 복사본에만 적용한다. 원본 state와 pending 연산은 실제 transform을 위해 남긴다.','Scalar codec write/read가 CHAR padding 등 저장 의미를 맞춘다. Old OOS key의 Resolve에는 I/O가 있을 수 있다.'],[(h,12117,'Effective key helper')],21),
      node('bind','Context의 stable slot에 바인딩','이전 key를 clear하고 readable slot에 effective key를 넣는다.', ['Expression cache는 context 소유 slot에 연결된다. 임시 stack DB_VALUE로 바꾸지 않는다.','Duplicate probe가 남긴 값을 제거하고 평가 뒤 value를 정리한다.'],[(p,3571,'Attrinfo adapter')],5),
      node('select','Expression으로 child를 선택','같은 evaluator가 기존 record route와 새 key route를 처리한다.', ['NULL은 PO_IS_NULL로 처리한다. 목적지가 정확히 하나여야 한다.','공통 wrapper가 explicit child와의 일치 및 context lifetime을 검증한다.'],[(p,3479,'Shared evaluator'),(p,3757,'INSERT adapter 선택')],9),
      node('owner','선택한 owner로 전체 row 변환','Source attrinfo를 유지하고 OOS file 선택에만 destination을 넘긴다.', ['Main path는 owner-aware first pass다. 전체 inline probe 후 rebuild가 아니다.','기존 bigone 거절, payload·LOB 준비, publication reset 경계를 유지한다.'],[(h,12927,'Owner-aware first pass'),(h,12888,'Physical owner 전달')],29),
      node('verify','Final record routing과 비교','직렬화된 record로 다시 고른 destination이 early owner와 일치해야 한다.', ['다르면 ER_GENERIC_ERROR로 반환한다. 이미 기록한 chain을 둔 채 record를 다른 heap으로 보내지 않는다.','Final route는 representation ID patch와 기존 validation을 유지한다.'],[(l,4996,'INSERT agreement'),(l,6021,'UPDATE agreement')],41),
      node('write','Heap/index 저장 또는 이동','같은 child이면 기존 UPDATE를, 다른 child이면 기존 move path를 사용한다.', ['Move helper는 destination insert 뒤 source delete를 수행한다. Source identity는 이 단계까지 필요하다.','오류를 반환하는 것과 즉시 모든 chain을 회수하는 것은 다르다. Logged 작업은 rollback 경로에 의존한다.'],[(l,6051,'Movement 선택'),(l,5402,'기존 move helper')],56),
      node('proof','물리적 관찰과 검증 한계','SQL 값과 root/child의 OOS chunk count를 함께 확인한다.', ['기존 review: 988a4d2에서 SQL 32/32 통과. 이번 문서 작성에서 engine test는 실행하지 않았다.','Rollback 뒤 실제 vacuum readback regression은 DISABLED 상태이며 full lifecycle acceptance는 열려 있다.'],[(t,437,'Root 0 / p0 1 / p1 0 oracle'),('unit_tests/oos/test_oos_real_vacuum_server.cpp',833,'Disabled lifecycle regression')],63),
    ]
    data[-1]['comments']=[dict(author='vimkim · 기존 review 요약',body='988a4d2 검토: 새 routing correctness defect는 확인되지 않았지만 SERVER_MODE lifecycle, control performance, integrated evidence는 미완료. 현재 HEAD는 rollback/vacuum regression을 DISABLED로 보관한다.',url='https://github.com/CUBRID/cubrid/pull/7600#issuecomment-5599750448')]
    dep=[
      node('locator','locator_sr.c · 순서와 합의','Early destination을 먼저 구하고 owner transform과 final force를 연결한다.', ['write_destination은 source class와 독립된 local 값이다.','Nonpartitioned와 기존 serialized-record caller는 NULL/default 인자로 이전 경로를 유지한다.'],[(l,7655,'Orchestration')],54),
      node('partition','partition.c · 공통 evaluator','Key와 record adapter가 같은 partition 의미를 사용한다.', ['Header는 두 by_attrinfo API를 노출한다.','Record decode와 representation patch는 record adapter에 남고 expression 평가만 공통화한다.'],[(p,3479,'Evaluator'),('src/query/partition_sr.h',122,'새 API 선언')],5),
      node('heap','heap_file.c · effective key와 transform','Key codec과 row serialization 경계가 실제 저장 의미를 제공한다.', ['heap_file.h는 effective key 및 transform mode를 선언한다.','Owner first pass와 retained second pass의 increment flag를 혼동하면 안 된다.'],[(h,12117,'Key codec'),('src/storage/heap_file.h',506,'API 선언')],21),
      node('oos','heap_oos.cpp · 기존 storage 경계','Class를 HFID/OOS VFID로 바꾸고 serialized values를 저장한다.', ['이 파일은 PR diff에 포함되지 않는 dependency다. Source identity를 바꾸지 않고 호출 인자의 owner만 바뀐다.','기존 publication reset과 transactional cleanup을 재사용한다.'],[(h,12888,'변경된 caller: owner 전달')],28),
      node('duplicates','query_executor.c · 임시 key probe','REPLACE·ODKU의 lookup image가 chain을 만들지 않게 한다.', ['Probe helper는 남아 있으며 main write의 early key route와 역할이 다르다.','FORCE_OUTLINE의 크기 gate 밖 경로도 suppression을 따라야 한다.'],[(q,11955,'REPLACE'),(q,12198,'ODKU')],16),
      node('sql','SQL 테스트와 timeout','28개 추가 테스트가 routing·source 보존·owner·실패 정리를 구별한다.', ['Direct test reference는 별도 attrinfo를 transform한다. Candidate와 공유하면 보존 검증이 약해진다.','Debug diagnostic 비용 때문에 test_oos_sql_show timeout을 300초로 조정한다.'],[(t,437,'추가 테스트 시작'),('unit_tests/oos/sql/CMakeLists.txt',57,'Timeout')],62),
      node('vacuum','Real-vacuum regression','기존 lifecycle 결함의 oracle을 DISABLED로 보존한다.', ['Committed delete witness를 기다린 뒤 원본을 다시 읽는다.','이 테스트는 partition 전용이 아니며 성공 결과도 아니다. 별도 lifecycle repair가 필요하다.'],[('unit_tests/oos/test_oos_real_vacuum_server.cpp',833,'DISABLED test')],63),
    ]
    dep[3]['links'].append(dict(label='변경되지 않은 dependency 소스',url='https://github.com/CUBRID/cubrid/blob/479cd960ec04196c92bf9789b1fc340af9046c2c/src/storage/heap_oos.cpp#L631'))
    user=[
      node('insert','SQL: 작은 forced INSERT','id=1과 64바이트 forced 값을 root table에 INSERT한다.', ['RANGE의 p0 경계는 10이다. 일반 큰 record 조건 없이도 FORCE_OUTLINE이 OOS를 선택한다.'],[(t,437,'최소 ownership 회귀')],62),
      node('observe','관찰: 값과 owner','값 비교가 true이고 p0에만 OOS file/chunk가 있어야 한다.', ['SELECT 성공만으로 소유권은 증명되지 않는다. SHOW ALL HEAP OOS가 root와 child를 구별한다.'],[(t,460,'논리값 확인과 물리 owner 순회')],62),
      node('move','SQL: 경계를 넘는 UPDATE','Root 대상으로 key를 9에서 10으로 옮겨 child가 달라진다.', ['Early key와 최종 stored key가 같은 destination을 선택해야 한다.','Child를 직접 명시했다면 밖으로 이동시키는 대신 검증 오류를 기대한다.'],[(t,589,'Expression·explicit partition·movement')],54),
      node('duplicate','SQL: REPLACE와 ODKU','Unique index를 먼저 찾는 임시 image는 저장되지 않는다.', ['Lookup용 image의 OOS demotion을 억제한다.','ODKU가 실제 UPDATE를 선택하면 main write가 별도로 destination을 구한다.'],[(q,11955,'Suppressed lookup'),(t,657,'복합 SQL 테스트')],18),
      node('error','SQL: 실패와 다음 write','목적지 없음·할당 실패·unique 충돌 뒤 abort하고 재시도한다.', ['명시적 abort 후 committed 값·owner count가 보존되는지 검사한다.','단순 error 반환만으로 즉시 모든 물리 정리가 끝났다고 판단하지 않는다.'],[(t,1002,'Publication failure matrix'),(t,1070,'LOB/index failure matrix')],62),
      node('later','시간이 지난 뒤: vacuum','Committed 원본이 rollback 뒤 vacuum을 거쳐도 읽혀야 한다.', ['별도 witness가 실제 vacuum 진행을 증명한다.','이 oracle의 과거 실패와 DISABLED 상태를 발표에서 명확히 구분한다.'],[('unit_tests/oos/test_oos_real_vacuum_server.cpp',833,'보관된 regression')],63),
    ]
    def seq(nodes,file,line):return [(a['id'],b['id'],'다음 확인',file,line) for a,b in zip(nodes,nodes[1:])]
    dg=seq(data,l,7768)
    for edge,label in zip(dg,['key 입력 준비','stable slot 채움','expression 평가','owner 전달','record 검증','일치하면 저장','결과 관찰']):
        dg[dg.index(edge)]=(edge[0],edge[1],label,edge[3],edge[4])
    deps=[('locator','partition','early/final route 호출',l,7787),('partition','heap','effective key 요청',p,3594),('locator','heap','owner transform 요청',l,7793),('heap','oos','selected class 전달',h,12888),('duplicates','locator','probe image 요청',q,11958),('sql','locator','SQL 및 직접 API 실행',t,1274),('vacuum','oos','value lifetime 관찰','unit_tests/oos/test_oos_real_vacuum_server.cpp',833)]
    return [
      graph('system-overview','System overview','#c0872a','기본 구조: record·partition·OOS·transform·lifetime',overview,[],[n['summary'] for n in overview]),
      graph('data-flow','Data flow graph','#34895c','Key에서 목적지 owner와 최종 record까지',data,dg,[n['summary']+' '+n['details'][0] for n in data]),
      graph('code-dependency','Code dependency graph','#2e5d9e','어떤 모듈이 어떤 계약을 제공하는가',dep,deps,[n['summary']+' '+n['details'][0] for n in dep]),
      graph('user-action','User action graph','#754dac','SQL과 물리적 관찰을 연결하는 발표 순서',user,seq(user,t,437),[n['summary']+' '+n['details'][0] for n in user])]
