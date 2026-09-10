2658	  log_Gl.hdr.append_lsa.pageid++;
   0x00000000006e88cb <+75>:	movabs $0xffffffffffff,%rdx
   0x00000000006e88d5 <+85>:	movabs $0xffff000000000000,%rcx
   0x00000000006e88df <+95>:	mov    %rax,%rdi
   0x00000000006e88e2 <+98>:	and    %rcx,%rax
   0x00000000006e88e5 <+101>:	shl    $0x10,%rdi
   0x00000000006e88e9 <+105>:	add    $0x10000,%rdi
   0x00000000006e88f0 <+112>:	sar    $0x10,%rdi
   0x00000000006e88f4 <+116>:	and    %rdi,%rdx
   0x00000000006e88f7 <+119>:	or     %rdx,%rax
   0x00000000006e88fa <+122>:	mov    %rax,0x118(%rbx)

2659	  log_Gl.hdr.append_lsa.offset = 0;
