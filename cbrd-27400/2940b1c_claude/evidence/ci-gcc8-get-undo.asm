Dump of assembler code for function _Z19log_get_undo_recordPN9cubthread5entryEP8log_page7log_lsaP6recdes:
/__w/cubrid/cubrid/cubrid/src/transaction/log_manager.c:
9836	{
9837	  LOG_RECORD_HEADER *log_rec_header = NULL;
9838	  LOG_REC_MVCC_UNDO *mvcc_undo = NULL;
9839	  LOG_REC_MVCC_UNDOREDO *mvcc_undoredo = NULL;
9840	  LOG_REC_UNDO *undo = NULL;
9841	  LOG_REC_UNDOREDO *undoredo = NULL;
9842	  LOG_REC_SUPPLEMENT *supplement = NULL;
9843	  int udata_length;
9844	  int udata_size;
9845	  char *undo_data;
9846	  LOG_LSA oldest_prior_lsa;
9847	  bool is_zipped = false;
9848	  char log_buf[IO_MAX_PAGE_SIZE + MAX_ALIGNMENT];
9849	  LOG_ZIP *log_unzip_ptr = NULL;
9850	  char *area = NULL;
9851	  SCAN_CODE scan = S_SUCCESS;
9852	  bool area_was_mallocated = false;
9853	
9854	  /* assert log record is not in prior list */
9855	  oldest_prior_lsa = *log_get_append_lsa ();
   0x0000000000753f90 <+0>:	push   %rbp
   0x0000000000753f91 <+1>:	mov    %rsp,%rbp
   0x0000000000753f94 <+4>:	push   %r15
   0x0000000000753f96 <+6>:	push   %r14
   0x0000000000753f98 <+8>:	push   %r13
   0x0000000000753f9a <+10>:	push   %r12
   0x0000000000753f9c <+12>:	mov    %rcx,%r12
   0x0000000000753f9f <+15>:	push   %rbx
   0x0000000000753fa0 <+16>:	mov    %rsi,%rbx
   0x0000000000753fa3 <+19>:	sub    $0x4038,%rsp
   0x0000000000753faa <+26>:	mov    %rdx,-0x4048(%rbp)
   0x0000000000753fb1 <+33>:	mov    %rdi,-0x4050(%rbp)
   0x0000000000753fb8 <+40>:	call   0x206570 <_Z18log_get_append_lsav@plt>

/__w/cubrid/cubrid/cubrid/src/transaction/log_lsa.hpp:
175	  return (pageid < olsa.pageid) || (pageid == olsa.pageid && offset < olsa.offset);
   0x0000000000753fbd <+45>:	mov    -0x4048(%rbp),%rdx

/__w/cubrid/cubrid/cubrid/src/transaction/log_manager.c:
9855	  oldest_prior_lsa = *log_get_append_lsa ();
   0x0000000000753fc4 <+52>:	mov    (%rax),%rcx

/__w/cubrid/cubrid/cubrid/src/transaction/log_lsa.hpp:
175	  return (pageid < olsa.pageid) || (pageid == olsa.pageid && offset < olsa.offset);
   0x0000000000753fc7 <+55>:	shl    $0x10,%rdx

/__w/cubrid/cubrid/cubrid/src/transaction/log_manager.c:
9855	  oldest_prior_lsa = *log_get_append_lsa ();
   0x0000000000753fcb <+59>:	mov    %rcx,%rsi
   0x0000000000753fce <+62>:	shl    $0x10,%rsi

/__w/cubrid/cubrid/cubrid/src/transaction/log_lsa.hpp:
175	  return (pageid < olsa.pageid) || (pageid == olsa.pageid && offset < olsa.offset);
   0x0000000000753fd2 <+66>:	cmp    %rdx,%rsi
   0x0000000000753fd5 <+69>:	jg     0x754020 <_Z19log_get_undo_recordPN9cubthread5entryEP8log_page7log_lsaP6recdes+144>

173	log_lsa::operator< (const log_lsa &olsa) const
   0x0000000000753fd7 <+71>:	xor    -0x4048(%rbp),%rcx
   0x0000000000753fde <+78>:	movabs $0xffffffffffff,%rdx
   0x0000000000753fe8 <+88>:	test   %rdx,%rcx
   0x0000000000753feb <+91>:	jne    0x753ffa <_Z19log_get_undo_recordPN9cubthread5entryEP8log_page7log_lsaP6recdes+106>
   0x0000000000753fed <+93>:	movzwl -0x4042(%rbp),%edx
   0x0000000000753ff4 <+100>:	cmp    0x6(%rax),%dx
   0x0000000000753ff8 <+104>:	jl     0x754027 <_Z19log_get_undo_recordPN9cubthread5entryEP8log_page7log_lsaP6recdes+151>

/__w/cubrid/cubrid/cubrid/src/transaction/log_manager.c:
9856	  assert (LSA_LT (&process_lsa, &oldest_prior_lsa));
   0x0000000000753ffa <+106>:	lea    0x4e119f(%rip),%rcx        # 0xc351a0 <_ZZ19log_get_undo_recordPN9cubthread5entryEP8log_page7log_lsaP6recdesE19__PRETTY_FUNCTION__>
