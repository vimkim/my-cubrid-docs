Dump of assembler code for function log_get_undo_record(cubthread::entry*, log_page*, log_lsa, recdes*):
   0x00000000006d5520 <+0>:	push   %rbp
   0x00000000006d5521 <+1>:	mov    %rsp,%rbp
   0x00000000006d5524 <+4>:	push   %r15
   0x00000000006d5526 <+6>:	push   %r14
   0x00000000006d5528 <+8>:	push   %r13
   0x00000000006d552a <+10>:	push   %r12
   0x00000000006d552c <+12>:	mov    %rdi,%r12
   0x00000000006d552f <+15>:	push   %rbx
   0x00000000006d5530 <+16>:	mov    %rsi,%rbx
   0x00000000006d5533 <+19>:	sub    $0x4038,%rsp
   0x00000000006d553a <+26>:	mov    %rdx,-0x4048(%rbp)
   0x00000000006d5541 <+33>:	mov    %rcx,-0x4058(%rbp)
   0x00000000006d5548 <+40>:	call   0x204cc0 <log_get_append_lsa()@plt>
   0x00000000006d554d <+45>:	mov    (%rax),%rcx
   0x00000000006d5550 <+48>:	movzwl 0x6(%rax),%esi
   0x00000000006d5554 <+52>:	mov    -0x4048(%rbp),%rax
   0x00000000006d555b <+59>:	mov    %rcx,%rdx
   0x00000000006d555e <+62>:	shl    $0x10,%rax
   0x00000000006d5562 <+66>:	shl    $0x10,%rdx
   0x00000000006d5566 <+70>:	sar    $0x10,%rax
   0x00000000006d556a <+74>:	sar    $0x10,%rdx
   0x00000000006d556e <+78>:	cmp    %rdx,%rax
   0x00000000006d5571 <+81>:	jl     0x6d55b8 <log_get_undo_record(cubthread::entry*, log_page*, log_lsa, recdes*)+152>
   0x00000000006d5573 <+83>:	xor    -0x4048(%rbp),%rcx
   0x00000000006d557a <+90>:	movabs $0xffffffffffff,%rdx
   0x00000000006d5584 <+100>:	test   %rdx,%rcx
   0x00000000006d5587 <+103>:	jne    0x6d5595 <log_get_undo_record(cubthread::entry*, log_page*, log_lsa, recdes*)+117>
   0x00000000006d5589 <+105>:	movzwl -0x4042(%rbp),%edx
   0x00000000006d5590 <+112>:	cmp    %si,%dx
   0x00000000006d5593 <+115>:	jl     0x6d55bf <log_get_undo_record(cubthread::entry*, log_page*, log_lsa, recdes*)+159>
   0x00000000006d5595 <+117>:	lea    0x45cf7c(%rip),%rcx        # 0xb32518
   0x00000000006d559c <+124>:	mov    $0x2680,%edx
   0x00000000006d55a1 <+129>:	lea    0x459888(%rip),%rsi        # 0xb2ee30
   0x00000000006d55a8 <+136>:	lea    0x45cfb9(%rip),%rdi        # 0xb32568
   0x00000000006d55af <+143>:	call   0x206350 <__assert_fail@plt>
   0x00000000006d55b4 <+148>:	nopl   0x0(%rax)
   0x00000000006d55b8 <+152>:	movzwl -0x4042(%rbp),%edx
   0x00000000006d55bf <+159>:	lea    0x10(%rbx),%rdi
   0x00000000006d55c3 <+163>:	movswq %dx,%rcx
   0x00000000006d55c7 <+167>:	mov    0x6b15c2(%rip),%r13        # 0xd86b90
   0x00000000006d55ce <+174>:	add    $0x27,%edx
   0x00000000006d55d1 <+177>:	add    %rdi,%rcx
   0x00000000006d55d4 <+180>:	and    $0xfffffff8,%edx
   0x00000000006d55d7 <+183>:	mov    %rdi,-0x4060(%rbp)
