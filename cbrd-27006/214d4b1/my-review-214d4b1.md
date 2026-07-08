static int
heap_attrvalue_read (RECDES * recdes, HEAP_ATTRVALUE * value, HEAP_CACHE_ATTRINFO * attr_info, RECDES * prefetched_oos)
{
  OR_ATTRIBUTE *attrepr;
  
I don't understand the introduction of prefetched_oos

Explain why it is needed, and tell me what it looks like if I remove them.

What are the alternatives.


---

heap_attrinfo_read_dbvalues_internal()

  for (i = 0; ret == NO_ERROR && i < attr_info->num_values; i++)
    {
      ret = heap_attrvalue_read (recdes, &attr_info->values[i], attr_info, grouped ? &oos_raws[i] : NULL);
    }


This part looks awkward. What are the alternatives?

---

heap_attrinfo_read_dbvalues ()
heap_attrinfo_read_dbvalues_internal()

now no reason to separate the internal function right?

---

/
// *INDENT-OFF*
static SCAN_CODE
heap_attrinfo_insert_to_oos (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, int lob_create_flag,
			     std::vector<bool> * oos_columns, std::vector<OID> * oos_oids,
			     std::vector<DB_BIGINT> * oos_lengths)
// *INDENT-ON*


why is this in heap_file, not heap_oos.cpp?

Also, try to improve readabilities. Redesign.
