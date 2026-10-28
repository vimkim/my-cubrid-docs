#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstddef>
#include <cstring>

unsigned long hl_register_lea_heap();
void hl_unregister_lea_heap(unsigned long);
void *hl_lea_alloc(unsigned long, std::size_t);
void hl_lea_free(unsigned long, void *);
extern "C" std::size_t mspace_footprint(void *);

int main(int argc, char **argv)
{
  const int rows = argc > 1 ? std::atoi(argv[1]) : 1000;
  const char *mode = argc > 2 ? argv[2] : "overlap";
  const unsigned long heap = hl_register_lea_heap();
  void *ms = *reinterpret_cast<void **>(heap);
  const std::size_t seed_size = argc > 3 ? std::strtoul(argv[3], nullptr, 10) : 0;
  void *seed = seed_size != 0 ? hl_lea_alloc(heap, seed_size) : nullptr;
  void *guard = nullptr;
  void *literal = nullptr;
  if (std::strcmp(mode, "tree") == 0)
    {
      void *smaller = hl_lea_alloc(heap, 26000);
      guard = hl_lea_alloc(heap, 32);
      literal = hl_lea_alloc(heap, 32001);
      hl_lea_free(heap, smaller);
    }
  void *previous = nullptr;
  std::size_t peak = 0;
  const auto start = std::chrono::steady_clock::now();
  for (int i = 0; i < rows; ++i)
    {
      void *temporary = nullptr;
      if (std::strcmp(mode, "single") != 0)
        temporary = hl_lea_alloc(heap, 32008);
      if (previous != nullptr)
        hl_lea_free(heap, previous);
      previous = hl_lea_alloc(heap, 32001);
      if (temporary != nullptr)
        hl_lea_free(heap, temporary);
      const std::size_t footprint = mspace_footprint(ms);
      if (footprint > peak) peak = footprint;
    }
  hl_lea_free(heap, previous);
  const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
  std::printf("{\"mode\":\"%s\",\"rows\":%d,\"seed\":%zu,\"peak_footprint\":%zu,\"final_footprint\":%zu,\"seconds\":%.9f}\n",
              mode, rows, seed_size, peak, mspace_footprint(ms), seconds);
  if (seed != nullptr) hl_lea_free(heap, seed);
  if (guard != nullptr) hl_lea_free(heap, guard);
  if (literal != nullptr) hl_lea_free(heap, literal);
  hl_unregister_lea_heap(heap);
  const std::size_t limit = argc > 4 ? std::strtoul(argv[4], nullptr, 10) : 0;
  return limit != 0 && peak > limit ? 2 : 0;
}
