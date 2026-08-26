#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <type_traits>
#include <utility>

#if !defined(PROBE_VARIANT)
#error "PROBE_VARIANT must be 1 (original), 2 (conditional), or 3 (forced)"
#endif

extern "C" void external_cleanup (std::uint64_t *value);

#if PROBE_VARIANT == 1

template<typename Callable>
class scope_exit final
{
  public:
    explicit scope_exit (Callable &&callable) noexcept
      : m_valid (true)
      , m_callable (std::is_lvalue_reference<decltype (callable)>::value ? callable : std::forward<Callable> (callable))
    {}

    scope_exit (scope_exit &&sg) noexcept
      : m_valid (sg.m_valid)
      , m_callable (sg.m_callable)
    {
      sg.m_valid = false;
    }

    ~scope_exit () noexcept
    {
      if (m_valid)
	{
	  m_callable ();
	}
    }

    void release () noexcept
    {
      m_valid = false;
    }

  private:
    using func_t = std::function<void (void)>;

    bool m_valid;
    func_t m_callable;

    scope_exit () = delete;
    scope_exit (scope_exit &) = delete;
    scope_exit &operator= (const scope_exit &) = delete;
    scope_exit &operator= (scope_exit &&) = delete;
};

#elif PROBE_VARIANT == 2 || PROBE_VARIANT == 3

template<class F>
class scope_exit
{
  public:
    using fun_t = std::decay_t<F>;

#if PROBE_VARIANT == 2
    explicit constexpr scope_exit (F &&f) noexcept (std::is_nothrow_constructible_v<fun_t, F &&>)
#else
    explicit constexpr scope_exit (F &&f) noexcept
#endif
      : active_ (true), f_ (std::forward<F> (f)) {}

    scope_exit (const scope_exit &) = delete;
    scope_exit &operator= (const scope_exit &) = delete;
    scope_exit &operator= (scope_exit &&) = delete;

#if PROBE_VARIANT == 2
    constexpr scope_exit (scope_exit &&other) noexcept (std::is_nothrow_move_constructible_v<fun_t>)
#else
    constexpr scope_exit (scope_exit &&other) noexcept
#endif
      : active_ (other.active_), f_ (std::move (other.f_))
    {
      other.release ();
    }

#if PROBE_VARIANT == 2
    ~scope_exit () noexcept (noexcept (std::declval<fun_t &> () ()))
#else
    ~scope_exit () noexcept
#endif
    {
      if (active_)
	{
	  f_ ();
	}
    }

    constexpr void release () noexcept
    {
      active_ = false;
    }

    [[nodiscard]] constexpr bool engaged () const noexcept
    {
      return active_;
    }

  private:
    bool active_ {false};
    fun_t f_;
};

template<class F>
scope_exit (F) -> scope_exit<std::decay_t<F>>;

#endif

struct cleanup_functor
{
  std::uint64_t *value;

  void operator() ()
  {
    external_cleanup (value);
  }
};

#if PROBE_VARIANT == 1
using representative_guard = scope_exit<std::function<void ()>>;
#else
using representative_guard = scope_exit<cleanup_functor>;
#endif

alignas (64) std::uint64_t g_hot_data[8] =
{
  0x9e3779b97f4a7c15ULL, 0xbf58476d1ce4e5b9ULL,
  0x94d049bb133111ebULL, 0x2545f4914f6cdd1dULL,
  0x369dea0f31a53f85ULL, 0xdb4f0b9175ae2165ULL,
  0xbb67ae8584caa73bULL, 0x3c6ef372fe94f82bULL
};

__attribute__ ((noinline)) std::uint64_t
guarded_work (std::uint64_t input)
{
  std::uint64_t result = input * 0x9e3779b97f4a7c15ULL;
#if PROBE_VARIANT == 1
  scope_exit<std::function<void ()>> guard (cleanup_functor {&result});
#else
  scope_exit guard (cleanup_functor {&result});
#endif
  result ^= result >> 29;
  return result;
}

__attribute__ ((noinline)) std::uint64_t
released_work (std::uint64_t input)
{
  std::uint64_t result = input + 17;
#if PROBE_VARIANT == 1
  scope_exit<std::function<void ()>> guard (cleanup_functor {&result});
#else
  scope_exit guard (cleanup_functor {&result});
#endif
  guard.release ();
  return result;
}

__attribute__ ((noinline, used)) std::uint64_t
hot_count (std::uint64_t iterations)
{
  std::uint64_t accumulator = 0;
  for (std::uint64_t i = 0; i < iterations; ++i)
    {
      accumulator += (i ^ g_hot_data[i & 7U]);
    }
  return accumulator;
}

int
main (int argc, char **argv)
{
  const std::uint64_t iterations = argc > 1 ? std::strtoull (argv[1], nullptr, 10) : 1000000ULL;
  const std::uint64_t answer = guarded_work (iterations) ^ released_work (iterations) ^ hot_count (iterations);
  std::printf ("variant=%d guard_size=%zu destructor_noexcept=%d result=%llu\n",
	      PROBE_VARIANT, sizeof (representative_guard),
	      noexcept (std::declval<representative_guard &> ().~representative_guard ()) ? 1 : 0,
	      static_cast<unsigned long long> (answer));
  return 0;
}
