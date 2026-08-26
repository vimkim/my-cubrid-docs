#include <stdint.h>

volatile uint64_t g_cleanup_count;

void
external_cleanup (uint64_t *value)
{
  g_cleanup_count += *value & 1U;
}
