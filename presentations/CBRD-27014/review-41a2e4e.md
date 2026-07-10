the performance comparison is quite disappointing.

OOS has been proven by manual performance test that it's heap efficiency reduces IO fetch and thus nice at select speed.


Write a more elaborated select cases, which shows advantages and disadvantages of OOS.


It must be

- when all records are in heap (in develop), and the records are about 14.5k in size. In this case, a few columns go OOS so the record size is about 4k in heap in oos branch.

- when all records are in overflow page (in develop), that measn the record sizes are above 16k.

---

and for above two DDL cases,

we must test

select sum(id)
select all id

and also ranged random non-oos column select for incurring IO read (OOS's best advantage)

For CUBRID, do not forget to add hints like

/*+ NO_MERGE RECOMPILE PARALLEL(0) HEAP_NO_PARALLEL_SCAN */ kinda hints
I don't remember how to disable parallel heap scan but anyway.
