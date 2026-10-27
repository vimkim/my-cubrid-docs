/*
 * Copyright 2026 CUBRID Corporation
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
#define _GNU_SOURCE
#define _FILE_OFFSET_BITS 64
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

/* Linux little-endian host; Python writes <iIQQ records. Data FDs are inherited
 * from the manifest validator. This helper never opens a data path for writing.
 * Usage: probe schedule.bin normal|random|direct CPU latency.bin|- FD ...
 */
struct request
{
  int32_t fd;
  uint32_t kind;
  uint64_t offset;
  uint64_t size;
};
_Static_assert (sizeof (struct request) == 24, "unexpected request layout");

static void
fail (const char *what)
{
  perror (what);
  exit (1);
}

static uint64_t
nanoseconds (void)
{
  struct timespec value;
  if (clock_gettime (CLOCK_MONOTONIC, &value) != 0)
    fail ("clock_gettime");
  return (uint64_t) value.tv_sec * 1000000000ULL + value.tv_nsec;
}

static double
cpu_seconds (void)
{
  struct timespec value;
  if (clock_gettime (CLOCK_PROCESS_CPUTIME_ID, &value) != 0)
    fail ("process clock");
  return value.tv_sec + value.tv_nsec / 1e9;
}

static uint64_t
read_bytes (void)
{
  FILE *file = fopen ("/proc/self/io", "r");
  char line[256];
  uint64_t result = UINT64_MAX;
  if (file == NULL)
    fail ("/proc/self/io");
  while (fgets (line, sizeof (line), file) != NULL)
    if (sscanf (line, "read_bytes: %" SCNu64, &result) == 1)
      break;
  fclose (file);
  if (result == UINT64_MAX)
    {
      errno = EINVAL;
      fail ("read_bytes missing");
    }
  return result;
}

int
main (int argc, char **argv)
{
  if (argc < 7)
    {
      fprintf (stderr, "Usage: %s schedule normal|random|direct CPU latency|- FD ...\n", argv[0]);
      return 2;
    }
  const int direct = strcmp (argv[2], "direct") == 0;
  const int random = strcmp (argv[2], "random") == 0;
  if (!direct && !random && strcmp (argv[2], "normal") != 0)
    return 2;
  cpu_set_t cpus;
  CPU_ZERO (&cpus);
  const int cpu = atoi (argv[3]);
  if (cpu < 0 || cpu >= CPU_SETSIZE)
    return 2;
  CPU_SET (cpu, &cpus);
  if (sched_setaffinity (0, sizeof (cpus), &cpus) != 0)
    fail ("sched_setaffinity");

  for (int i = 5; i < argc; i++)
    {
      int fd = atoi (argv[i]);
      int flags = fcntl (fd, F_GETFL);
      struct stat st;
      if (flags < 0 || (flags & O_ACCMODE) != O_RDONLY || fstat (fd, &st) != 0
          || !S_ISREG (st.st_mode) || st.st_uid != getuid () || st.st_nlink != 1)
        {
          errno = EPERM;
          fail ("inherited descriptor is not an owned read-only regular file");
        }
      if (direct && fcntl (fd, F_SETFL, flags | O_DIRECT) != 0)
        fail ("enable O_DIRECT");
      if (!direct)
        {
          int error = posix_fadvise (fd, 0, 0, random ? POSIX_FADV_RANDOM : POSIX_FADV_NORMAL);
          if (error != 0)
            {
              errno = error;
              fail ("posix_fadvise");
            }
        }
    }

  FILE *schedule = fopen (argv[1], "rb");
  struct stat schedule_stat;
  if (schedule == NULL || fstat (fileno (schedule), &schedule_stat) != 0)
    fail ("open schedule");
  if (schedule_stat.st_size <= 0 || schedule_stat.st_size % sizeof (struct request) != 0)
    return 2;
  size_t count = schedule_stat.st_size / sizeof (struct request);
  struct request *requests = malloc (schedule_stat.st_size);
  if (requests == NULL)
    fail ("allocate requests");
  if (fread (requests, sizeof (*requests), count, schedule) != count)
    fail ("read schedule");
  fclose (schedule);
  size_t max_size = 0;
  uint64_t selected_bytes = 0;
  for (size_t i = 0; i < count; i++)
    {
      struct request *r = &requests[i];
      int allowed = 0;
      for (int j = 5; j < argc; j++)
        allowed |= r->fd == atoi (argv[j]);
      struct stat st;
      if (!allowed || fstat (r->fd, &st) != 0 || r->size == 0 || r->size > 1048576
          || r->offset % 16384 || r->size % 16384 || r->offset > (uint64_t) st.st_size
          || r->size > (uint64_t) st.st_size - r->offset)
        {
          errno = EINVAL;
          fail ("request outside allowed data");
        }
      if (r->size > max_size)
        max_size = r->size;
      selected_bytes += r->size;
    }
  void *buffer = NULL;
  int error = posix_memalign (&buffer, 4096, max_size);
  if (error != 0)
    {
      errno = error;
      fail ("aligned buffer");
    }
  const int instrumented = strcmp (argv[4], "-") != 0;
  uint64_t *durations = instrumented ? calloc (count, sizeof (*durations)) : NULL;
  if (instrumented && durations == NULL)
    fail ("allocate durations");
  struct rusage usage_before, usage_after;
  getrusage (RUSAGE_SELF, &usage_before);
  uint64_t before_bytes = read_bytes ();
  double before_cpu = cpu_seconds ();
  uint64_t start = nanoseconds ();
  uint64_t checksum = 0;
  for (size_t i = 0; i < count; i++)
    {
      uint64_t begin = instrumented ? nanoseconds () : 0;
      ssize_t size;
      do
        size = pread (requests[i].fd, buffer, requests[i].size, requests[i].offset);
      while (size < 0 && errno == EINTR);
      if (size != (ssize_t) requests[i].size)
        {
          if (size >= 0)
            errno = EIO;
          fail ("short/failed data read");
        }
      if (instrumented)
        durations[i] = nanoseconds () - begin;
      checksum += ((unsigned char *) buffer)[0] + ((unsigned char *) buffer)[size - 1];
    }
  uint64_t elapsed_ns = nanoseconds () - start;
  double elapsed_cpu = cpu_seconds () - before_cpu;
  uint64_t bytes = read_bytes () - before_bytes;
  getrusage (RUSAGE_SELF, &usage_after);
  if (instrumented)
    {
      FILE *output = fopen (argv[4], "wbx");
      if (output == NULL || fwrite (durations, sizeof (*durations), count, output) != count
          || fclose (output) != 0)
        fail ("write duration observations");
    }
  printf ("{\"elapsed_seconds\":%.9f,\"cpu_seconds\":%.9f,\"read_bytes\":%" PRIu64
          ",\"requests\":%zu,\"requested_bytes\":%" PRIu64 ",\"checksum\":%" PRIu64
          ",\"voluntary_switches\":%ld,\"involuntary_switches\":%ld,\"instrumented\":%s}\n",
          elapsed_ns / 1e9, elapsed_cpu, bytes, count, selected_bytes, checksum,
          usage_after.ru_nvcsw - usage_before.ru_nvcsw,
          usage_after.ru_nivcsw - usage_before.ru_nivcsw, instrumented ? "true" : "false");
  free (durations);
  free (buffer);
  free (requests);
  return 0;
}
