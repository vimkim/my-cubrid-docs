// One-off check for CBRD-27841: RV_fun[i].recv_index == i for every index, and RV_fun has
// exactly RV_LAST_LOGID + 1 entries. Linked against the installed server library.
#include "recovery.h"
#include <cstdio>
#include <cstdlib>

int
main (int argc, char **argv)
{
  // argv[1]: byte size of the RV_fun symbol from `nm -D -S`.
  size_t bytes = strtoul (argv[1], NULL, 0);
  size_t n = bytes / sizeof (struct rvfun);
  int bad = 0;
  for (size_t i = 0; i < n; i++)
    {
      if ((size_t) RV_fun[i].recv_index != i)
	{
	  printf ("MISMATCH at %zu: recv_index=%d (%s)\n", i, (int) RV_fun[i].recv_index, RV_fun[i].recv_string);
	  bad++;
	}
    }
  printf ("entries=%zu sizeof(rvfun)=%zu RV_LAST_LOGID=%d size_ok=%d mismatches=%d\n", n, sizeof (struct rvfun),
	  (int) RV_LAST_LOGID, (int) (n == (size_t) RV_LAST_LOGID + 1), bad);
  for (size_t i = 136; i < n; i++)
    {
      printf ("%zu %s\n", i, rv_rcvindex_string ((LOG_RCVINDEX) i));
    }
  bool ok = bad == 0 && n == (size_t) RV_LAST_LOGID + 1 && bytes % sizeof (struct rvfun) == 0;
  printf ("RESULT %s\n", ok ? "PASS" : "FAIL");
  return ok ? 0 : 1;
}
