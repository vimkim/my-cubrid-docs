# Lesson 0003: The heap's optional OOS file

Status: introduced; understanding check pending. HTML/SVG follows once settled.

In this PR's design, a heap has at most one associated OOS file, created when needed. It holds selected externalized attribute values; the heap row retains an OOS inline stub referring to each such value. This is a per-heap association, not a file per row or per value.

Teaching labels: p0 → H0 → optional OOS0; p1 → H1 → optional OOS1. If a row belongs in H0 and one attribute is stored out of row, that value belongs in OOS0 under this design. Many values from rows in H0 can use OOS0. A file can contain many pages; OOS0 is not one page.

Source: [heap_oos_find_vfid](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/storage/heap_file.c#L12433) uses the supplied heap identifier to look up or create its OOS file and records that file identifier in the heap header. This explains the current association; it does not establish that shared-file alternatives are impossible or slower.

Check: A row with id = 12 belongs to p1. If its large attribute is externalized, should it go into OOS0 or OOS1 under this design? Explain using the row's heap.
