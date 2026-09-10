Dump of assembler code for function logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY):
/__w/cubrid/cubrid/cubrid/src/transaction/log_page_buffer.c:
2631	{
2632	  LOG_FLUSH_INFO *flush_info = &log_Gl.flush_info;
2633	  bool need_flush;
2634	#if defined(SERVER_MODE)
2635	  int rv;
2636	#endif /* SERVER_MODE */
2637	#if defined(CUBRID_DEBUG)
2638	  long commit_count = 0;
2639	  static struct timeval start_append_time = { 0, 0 };
2640	  struct timeval end_append_time = { 0, 0 };
2641	  static long prev_commit_count_in_append = 0;
2642	  double elapsed = 0;
2643	
2644	  gettimeofday (&end_append_time, NULL);
2645	#endif /* CUBRID_DEBUG */
2646	
2647	  assert (LOG_CS_OWN_WRITE_MODE (thread_p));
   0x000000000076cfa0 <+0>:	push   %rbp
   0x000000000076cfa1 <+1>:	mov    %rsp,%rbp
   0x000000000076cfa4 <+4>:	push   %r12
   0x000000000076cfa6 <+6>:	mov    %rdi,%r12
   0x000000000076cfa9 <+9>:	push   %rbx
   0x000000000076cfaa <+10>:	mov    %esi,%ebx
   0x000000000076cfac <+12>:	call   0x215a00 <_Z21LOG_CS_OWN_WRITE_MODEPN9cubthread5entryE@plt>
   0x000000000076cfb1 <+17>:	test   %al,%al
   0x000000000076cfb3 <+19>:	je     0x76d252 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+690>

2648	
2649	  logpb_log ("started logpb_next_append_page\n");
   0x000000000076cfb9 <+25>:	cmpb   $0x0,0x9efee0(%rip)        # 0x115cea0 <_ZL13logpb_Logging>
   0x000000000076cfc0 <+32>:	jne    0x76d108 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+360>

2650	
2651	  if (current_setdirty == LOG_SET_DIRTY)
   0x000000000076cfc6 <+38>:	cmp    $0x1,%ebx

2652	    {
2653	      logpb_set_dirty (thread_p, log_Gl.append.log_pgptr);
   0x000000000076cfc9 <+41>:	mov    0x8e2838(%rip),%rbx        # 0x104f808

2651	  if (current_setdirty == LOG_SET_DIRTY)
   0x000000000076cfd0 <+48>:	je     0x76d132 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+402>

2654	    }
2655	
2656	  log_Gl.append.log_pgptr = NULL;
   0x000000000076cfd6 <+54>:	mov    0x118(%rbx),%rax
   0x000000000076cfdd <+61>:	movq   $0x0,0x40(%rbx)

2657	
2658	  log_Gl.hdr.append_lsa.pageid++;
   0x000000000076cfe5 <+69>:	movabs $0xffffffffffff,%rdx
   0x000000000076cfef <+79>:	movabs $0xffff000000000000,%rcx
   0x000000000076cff9 <+89>:	mov    %rax,%rdi
   0x000000000076cffc <+92>:	and    %rcx,%rax
   0x000000000076cfff <+95>:	shl    $0x10,%rdi
   0x000000000076d003 <+99>:	add    $0x10000,%rdi
   0x000000000076d00a <+106>:	sar    $0x10,%rdi
   0x000000000076d00e <+110>:	and    %rdi,%rdx
   0x000000000076d011 <+113>:	or     %rdx,%rax
   0x000000000076d014 <+116>:	mov    %rax,0x118(%rbx)

2659	  log_Gl.hdr.append_lsa.offset = 0;
   0x000000000076d01b <+123>:	xor    %eax,%eax
   0x000000000076d01d <+125>:	mov    %ax,0x11e(%rbx)

2660	
2661	  /*
2662	   * Is the next logical page to archive, currently located at the physical
2663	   * location of the next logical append page ? (Remember the log is a RING).
2664	   * If so, we need to archive the log from the next logical page to archive
2665	   * up to the closest page that does not hold the current append log record.
2666	   */
2667	
2668	  if (LOGPB_AT_NEXT_ARCHIVE_PAGE_ID (log_Gl.hdr.append_lsa.pageid))
   0x000000000076d024 <+132>:	call   0x213810 <_Z24logpb_to_physical_pageidl@plt>
   0x000000000076d029 <+137>:	cmp    %eax,0x130(%rbx)
   0x000000000076d02f <+143>:	je     0x76d1e0 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+576>

2672	    }
2673	
2674	  /*
2675	   * Has the log been cycled ?
2676	   */
2677	  if (LOGPB_IS_FIRST_PHYSICAL_PAGE (log_Gl.hdr.append_lsa.pageid))
   0x000000000076d035 <+149>:	mov    0x118(%rbx),%rdi
   0x000000000076d03c <+156>:	shl    $0x10,%rdi
   0x000000000076d040 <+160>:	sar    $0x10,%rdi
   0x000000000076d044 <+164>:	call   0x213810 <_Z24logpb_to_physical_pageidl@plt>
   0x000000000076d049 <+169>:	cmp    $0x1,%eax
   0x000000000076d04c <+172>:	je     0x76d1f0 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+592>

2683	    }
2684	
2685	  /*
2686	   * Fetch the next page as a newly defined append page. Append pages are
2687	   * always new pages
2688	   */
2689	
2690	  log_Gl.append.log_pgptr = logpb_create_page (thread_p, log_Gl.hdr.append_lsa.pageid);
   0x000000000076d052 <+178>:	mov    0x118(%rbx),%rsi
   0x000000000076d059 <+185>:	mov    %r12,%rdi
   0x000000000076d05c <+188>:	shl    $0x10,%rsi
   0x000000000076d060 <+192>:	sar    $0x10,%rsi
   0x000000000076d064 <+196>:	call   0x211d50 <_Z17logpb_create_pagePN9cubthread5entryEl@plt>
   0x000000000076d069 <+201>:	mov    %rax,0x40(%rbx)

2691	  if (log_Gl.append.log_pgptr == NULL)
   0x000000000076d06d <+205>:	test   %rax,%rax
   0x000000000076d070 <+208>:	je     0x76d210 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+624>

2694	      /* This statement should not be reached */
2695	      return;
2696	    }
2697	
2698	  if (log_Gl.append.appending_page_tde_encrypted)
   0x000000000076d076 <+214>:	cmpb   $0x0,0x48(%rbx)
   0x000000000076d07a <+218>:	jne    0x76d188 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+488>

2703	    }
2704	
2705	  logpb_log ("logpb_next_append_page: append the new page (%lld), tde_algorithm = %s\n",
   0x000000000076d080 <+224>:	cmpb   $0x0,0x9efe19(%rip)        # 0x115cea0 <_ZL13logpb_Logging>
   0x000000000076d087 <+231>:	jne    0x76d148 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+424>

2706		     (long long int) log_Gl.append.log_pgptr->hdr.logical_pageid,
2707		     tde_get_algorithm_name (logpb_get_tde_algorithm (log_Gl.append.log_pgptr)));
2708	
2709	#if defined(CUBRID_DEBUG)
2710	  {
2711	    log_Stat.last_append_pageid = log_Gl.hdr.append_lsa.pageid;
2712	  }
2713	#endif /* CUBRID_DEBUG */
2714	
2715	  /*
2716	   * Save this log append page as an active page to be flushed at a later
2717	   * time if the page is modified (dirty).
2718	   * We must save the log append pages in the order that they are defined
2719	   * and need to be flushed.
2720	   */
2721	
2722	  rv = pthread_mutex_lock (&flush_info->flush_mutex);
   0x000000000076d08d <+237>:	lea    0x2f8(%rbx),%rdi
   0x000000000076d094 <+244>:	call   0x214790 <pthread_mutex_lock@plt>

2723	
2724	  flush_info->toflush[flush_info->num_toflush] = log_Gl.append.log_pgptr;
   0x000000000076d099 <+249>:	movslq 0x2ec(%rbx),%rdx
   0x000000000076d0a0 <+256>:	mov    0x40(%rbx),%rcx

2729	    {
2730	      need_flush = true;
2731	    }
2732	
2733	  pthread_mutex_unlock (&flush_info->flush_mutex);
   0x000000000076d0a4 <+260>:	lea    0x2f8(%rbx),%rdi

2724	  flush_info->toflush[flush_info->num_toflush] = log_Gl.append.log_pgptr;
   0x000000000076d0ab <+267>:	mov    0x2f0(%rbx),%rax
   0x000000000076d0b2 <+274>:	mov    %rcx,(%rax,%rdx,8)

2725	  flush_info->num_toflush++;
   0x000000000076d0b6 <+278>:	mov    0x2ec(%rbx),%eax
   0x000000000076d0bc <+284>:	add    $0x1,%eax
   0x000000000076d0bf <+287>:	mov    %eax,0x2ec(%rbx)

2726	
2727	  need_flush = false;
2728	  if (flush_info->num_toflush >= flush_info->max_toflush)
   0x000000000076d0c5 <+293>:	cmp    0x2e8(%rbx),%eax
   0x000000000076d0cb <+299>:	jge    0x76d0e8 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+328>

2729	    {
2730	      need_flush = true;
2731	    }
2732	
2733	  pthread_mutex_unlock (&flush_info->flush_mutex);
   0x000000000076d0cd <+301>:	call   0x209370 <pthread_mutex_unlock@plt>

2738	    }
2739	
2740	#if defined(CUBRID_DEBUG)
2741	  if (start_append_time.tv_sec != 0 && start_append_time.tv_usec != 0)
2742	    {
2743	      elapsed = LOG_GET_ELAPSED_TIME (end_append_time, start_append_time);
2744	    }
2745	
2746	  log_Stat.use_append_page_sec = elapsed;
2747	  gettimeofday (&start_append_time, NULL);
2748	
2749	  commit_count = log_Stat.commit_count - prev_commit_count_in_append;
2750	
2751	  prev_commit_count_in_append = log_Stat.commit_count;
2752	
2753	  log_Stat.last_commit_count_while_using_a_page = commit_count;
2754	  log_Stat.total_commit_count_while_using_a_page += log_Stat.last_commit_count_while_using_a_page;
2755	#endif /* CUBRID_DEBUG */
2756	
2757	  log_Stat.total_append_page_count++;
   0x000000000076d0d2 <+306>:	mov    0x8e1d4f(%rip),%rax        # 0x104ee28
   0x000000000076d0d9 <+313>:	addq   $0x1,(%rax)

2758	
2759	#if defined(CUBRID_DEBUG)
2760	  er_log_debug (ARG_FILE_LINE,
2761			"log_next_append_page: new page id(%lld) total_append_page_count(%ld)"
2762			" num_toflush(%d) use_append_page_sec(%f) need_flush(%d) commit_count(%ld)"
2763			" total_commit_count(%ld)\n", (int) log_Stat.last_append_pageid, log_Stat.total_append_page_count,
2764			flush_info->num_toflush, log_Stat.use_append_page_sec, need_flush,
2765			log_Stat.last_commit_count_while_using_a_page, log_Stat.total_commit_count_while_using_a_page);
2766	#endif /* CUBRID_DEBUG */
2767	}
   0x000000000076d0dd <+317>:	pop    %rbx
   0x000000000076d0de <+318>:	pop    %r12
   0x000000000076d0e0 <+320>:	pop    %rbp
   0x000000000076d0e1 <+321>:	ret
   0x000000000076d0e2 <+322>:	nopw   0x0(%rax,%rax,1)

2733	  pthread_mutex_unlock (&flush_info->flush_mutex);
   0x000000000076d0e8 <+328>:	call   0x209370 <pthread_mutex_unlock@plt>

2734	
2735	  if (need_flush)
2736	    {
2737	      logpb_flush_all_append_pages (thread_p);
   0x000000000076d0ed <+333>:	mov    %r12,%rdi
   0x000000000076d0f0 <+336>:	call   0x76f260 <logpb_flush_all_append_pages(THREAD_ENTRY*)>

2738	    }
2739	
2740	#if defined(CUBRID_DEBUG)
2741	  if (start_append_time.tv_sec != 0 && start_append_time.tv_usec != 0)
2742	    {
2743	      elapsed = LOG_GET_ELAPSED_TIME (end_append_time, start_append_time);
2744	    }
2745	
2746	  log_Stat.use_append_page_sec = elapsed;
2747	  gettimeofday (&start_append_time, NULL);
2748	
2749	  commit_count = log_Stat.commit_count - prev_commit_count_in_append;
2750	
2751	  prev_commit_count_in_append = log_Stat.commit_count;
2752	
2753	  log_Stat.last_commit_count_while_using_a_page = commit_count;
2754	  log_Stat.total_commit_count_while_using_a_page += log_Stat.last_commit_count_while_using_a_page;
2755	#endif /* CUBRID_DEBUG */
2756	
2757	  log_Stat.total_append_page_count++;
   0x000000000076d0f5 <+341>:	mov    0x8e1d2c(%rip),%rax        # 0x104ee28
   0x000000000076d0fc <+348>:	addq   $0x1,(%rax)

2758	
2759	#if defined(CUBRID_DEBUG)
2760	  er_log_debug (ARG_FILE_LINE,
2761			"log_next_append_page: new page id(%lld) total_append_page_count(%ld)"
2762			" num_toflush(%d) use_append_page_sec(%f) need_flush(%d) commit_count(%ld)"
2763			" total_commit_count(%ld)\n", (int) log_Stat.last_append_pageid, log_Stat.total_append_page_count,
2764			flush_info->num_toflush, log_Stat.use_append_page_sec, need_flush,
2765			log_Stat.last_commit_count_while_using_a_page, log_Stat.total_commit_count_while_using_a_page);
2766	#endif /* CUBRID_DEBUG */
2767	}
   0x000000000076d100 <+352>:	pop    %rbx
   0x000000000076d101 <+353>:	pop    %r12
   0x000000000076d103 <+355>:	pop    %rbp
   0x000000000076d104 <+356>:	ret
   0x000000000076d105 <+357>:	nopl   (%rax)

2649	  logpb_log ("started logpb_next_append_page\n");
   0x000000000076d108 <+360>:	xor    %eax,%eax
   0x000000000076d10a <+362>:	lea    0x4cb667(%rip),%rdx        # 0xc38778
   0x000000000076d111 <+369>:	mov    $0xa59,%esi
   0x000000000076d116 <+374>:	lea    0x4c9fd3(%rip),%rdi        # 0xc370f0
   0x000000000076d11d <+381>:	call   0x20ac60 <_er_log_debug@plt>

2650	
2651	  if (current_setdirty == LOG_SET_DIRTY)
   0x000000000076d122 <+386>:	cmp    $0x1,%ebx

2652	    {
2653	      logpb_set_dirty (thread_p, log_Gl.append.log_pgptr);
   0x000000000076d125 <+389>:	mov    0x8e26dc(%rip),%rbx        # 0x104f808

2651	  if (current_setdirty == LOG_SET_DIRTY)
   0x000000000076d12c <+396>:	jne    0x76cfd6 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+54>

2652	    {
2653	      logpb_set_dirty (thread_p, log_Gl.append.log_pgptr);
   0x000000000076d132 <+402>:	mov    0x40(%rbx),%rsi
   0x000000000076d136 <+406>:	mov    %r12,%rdi
   0x000000000076d139 <+409>:	call   0x21b840 <_Z15logpb_set_dirtyPN9cubthread5entryEP8log_page@plt>
   0x000000000076d13e <+414>:	jmp    0x76cfd6 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+54>
   0x000000000076d143 <+419>:	nopl   0x0(%rax,%rax,1)

2703	    }
2704	
2705	  logpb_log ("logpb_next_append_page: append the new page (%lld), tde_algorithm = %s\n",
   0x000000000076d148 <+424>:	mov    0x40(%rbx),%rdi
   0x000000000076d14c <+428>:	call   0x20b060 <_Z23logpb_get_tde_algorithmPK8log_page@plt>
   0x000000000076d151 <+433>:	mov    %eax,%edi
   0x000000000076d153 <+435>:	call   0x1ffdc0 <_Z22tde_get_algorithm_name13TDE_ALGORITHM@plt>
   0x000000000076d158 <+440>:	mov    0x40(%rbx),%rdx
   0x000000000076d15c <+444>:	mov    $0xa93,%esi
   0x000000000076d161 <+449>:	lea    0x4c9f88(%rip),%rdi        # 0xc370f0
   0x000000000076d168 <+456>:	mov    %rax,%r8
   0x000000000076d16b <+459>:	xor    %eax,%eax
   0x000000000076d16d <+461>:	mov    (%rdx),%rcx
   0x000000000076d170 <+464>:	lea    0x4cb629(%rip),%rdx        # 0xc387a0
   0x000000000076d177 <+471>:	call   0x20ac60 <_er_log_debug@plt>
   0x000000000076d17c <+476>:	jmp    0x76d08d <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+237>
   0x000000000076d181 <+481>:	nopl   0x0(%rax)

/__w/cubrid/cubrid/cubrid/src/base/system_parameter.h:
852	    assert (PRM_IS_INTEGER (GET_PRM (prm_id)) || PRM_IS_KEYWORD (GET_PRM (prm_id)));
   0x000000000076d188 <+488>:	mov    0x8e2249(%rip),%rcx        # 0x104f3d8
   0x000000000076d18f <+495>:	mov    0x9164(%rcx),%edx
   0x000000000076d195 <+501>:	test   %edx,%edx
   0x000000000076d197 <+503>:	je     0x76d1a2 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+514>
   0x000000000076d199 <+505>:	cmp    $0x3,%edx
   0x000000000076d19c <+508>:	jne    0x76d24d <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+685>

853	
854	#if defined (SERVER_MODE)
855	    if (PRM_SERVER_SESSION (prm_id))
   0x000000000076d1a2 <+514>:	mov    0x9160(%rcx),%edx
   0x000000000076d1a8 <+520>:	and    $0x904,%edx
   0x000000000076d1ae <+526>:	cmp    $0x104,%edx
   0x000000000076d1b4 <+532>:	je     0x76d238 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+664>

858	      }
859	#endif
860	    return PRM_GET_INT (GET_PRM (prm_id)->value);
   0x000000000076d1ba <+538>:	mov    0x9188(%rcx),%edx

/__w/cubrid/cubrid/cubrid/src/transaction/log_page_buffer.c:
2701	      logpb_set_tde_algorithm (thread_p, log_Gl.append.log_pgptr, tde_algo);
   0x000000000076d1c0 <+544>:	mov    %rax,%rsi
   0x000000000076d1c3 <+547>:	mov    %r12,%rdi
   0x000000000076d1c6 <+550>:	call   0x20b1d0 <_Z23logpb_set_tde_algorithmPN9cubthread5entryEP8log_page13TDE_ALGORITHM@plt>

2702	      logpb_set_dirty (thread_p, log_Gl.append.log_pgptr);
   0x000000000076d1cb <+555>:	mov    0x40(%rbx),%rsi
   0x000000000076d1cf <+559>:	mov    %r12,%rdi
   0x000000000076d1d2 <+562>:	call   0x21b840 <_Z15logpb_set_dirtyPN9cubthread5entryEP8log_page@plt>
   0x000000000076d1d7 <+567>:	jmp    0x76d080 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+224>
   0x000000000076d1dc <+572>:	nopl   0x0(%rax)

2671	      logpb_archive_active_log (thread_p);
   0x000000000076d1e0 <+576>:	mov    %r12,%rdi
   0x000000000076d1e3 <+579>:	call   0x76c2a0 <logpb_archive_active_log(THREAD_ENTRY*)>
   0x000000000076d1e8 <+584>:	jmp    0x76d035 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+149>
   0x000000000076d1ed <+589>:	nopl   (%rax)

2678	    {
2679	      log_Gl.hdr.fpageid += LOGPB_ACTIVE_NPAGES;
   0x000000000076d1f0 <+592>:	mov    %r12,%rdi
   0x000000000076d1f3 <+595>:	movslq 0x108(%rbx),%rax
   0x000000000076d1fa <+602>:	add    %rax,0x110(%rbx)

2680	
2681	      /* Flush the header to save updates by archiving. */
2682	      logpb_flush_header (thread_p);
   0x000000000076d201 <+609>:	call   0x216e90 <_Z18logpb_flush_headerPN9cubthread5entryE@plt>
   0x000000000076d206 <+614>:	jmp    0x76d052 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+178>
   0x000000000076d20b <+619>:	nopl   0x0(%rax,%rax,1)

2692	    {
2693	      logpb_fatal_error (thread_p, true, ARG_FILE_LINE, "log_next_append_page");
   0x000000000076d210 <+624>:	pop    %rbx
   0x000000000076d211 <+625>:	mov    %r12,%rdi
   0x000000000076d214 <+628>:	lea    0x4cd112(%rip),%r8        # 0xc3a32d

2758	
2759	#if defined(CUBRID_DEBUG)
2760	  er_log_debug (ARG_FILE_LINE,
2761			"log_next_append_page: new page id(%lld) total_append_page_count(%ld)"
2762			" num_toflush(%d) use_append_page_sec(%f) need_flush(%d) commit_count(%ld)"
2763			" total_commit_count(%ld)\n", (int) log_Stat.last_append_pageid, log_Stat.total_append_page_count,
2764			flush_info->num_toflush, log_Stat.use_append_page_sec, need_flush,
2765			log_Stat.last_commit_count_while_using_a_page, log_Stat.total_commit_count_while_using_a_page);
2766	#endif /* CUBRID_DEBUG */
2767	}
   0x000000000076d21b <+635>:	pop    %r12

2693	      logpb_fatal_error (thread_p, true, ARG_FILE_LINE, "log_next_append_page");
   0x000000000076d21d <+637>:	mov    $0xa85,%ecx
   0x000000000076d222 <+642>:	lea    0x4c9ec7(%rip),%rdx        # 0xc370f0
   0x000000000076d229 <+649>:	mov    $0x1,%esi

2758	
2759	#if defined(CUBRID_DEBUG)
2760	  er_log_debug (ARG_FILE_LINE,
2761			"log_next_append_page: new page id(%lld) total_append_page_count(%ld)"
2762			" num_toflush(%d) use_append_page_sec(%f) need_flush(%d) commit_count(%ld)"
2763			" total_commit_count(%ld)\n", (int) log_Stat.last_append_pageid, log_Stat.total_append_page_count,
2764			flush_info->num_toflush, log_Stat.use_append_page_sec, need_flush,
2765			log_Stat.last_commit_count_while_using_a_page, log_Stat.total_commit_count_while_using_a_page);
2766	#endif /* CUBRID_DEBUG */
2767	}
   0x000000000076d22e <+654>:	pop    %rbp

2693	      logpb_fatal_error (thread_p, true, ARG_FILE_LINE, "log_next_append_page");
   0x000000000076d22f <+655>:	jmp    0x20b210 <_Z17logpb_fatal_errorPN9cubthread5entryEbPKciS3_z@plt>
   0x000000000076d234 <+660>:	nopl   0x0(%rax)

/__w/cubrid/cubrid/cubrid/src/base/system_parameter.h:
857		return PRM_GET_INT_P (prm_get_value (prm_id));
   0x000000000076d238 <+664>:	mov    $0x136,%edi
   0x000000000076d23d <+669>:	call   0x215c20 <prm_get_value@plt>
   0x000000000076d242 <+674>:	mov    (%rax),%edx
   0x000000000076d244 <+676>:	mov    0x40(%rbx),%rax
   0x000000000076d248 <+680>:	jmp    0x76d1c0 <logpb_next_append_page(THREAD_ENTRY*, LOG_SETDIRTY)+544>
   0x000000000076d24d <+685>:	call   0x764a50 <prm_get_integer_value(PARAM_ID)>

/__w/cubrid/cubrid/cubrid/src/transaction/log_page_buffer.c:
2647	  assert (LOG_CS_OWN_WRITE_MODE (thread_p));
   0x000000000076d252 <+690>:	lea    0x4ceaa7(%rip),%rcx        # 0xc3bd00 <_ZZL22logpb_next_append_pagePN9cubthread5entryE12log_setdirtyE19__PRETTY_FUNCTION__>
   0x000000000076d259 <+697>:	mov    $0xa57,%edx
   0x000000000076d25e <+702>:	lea    0x4c9e8b(%rip),%rsi        # 0xc370f0
   0x000000000076d265 <+709>:	lea    0x4ca184(%rip),%rdi        # 0xc373f0
   0x000000000076d26c <+716>:	call   0x207c80 <__assert_fail@plt>
End of assembler dump.
