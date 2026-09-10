# Lesson 0002: A partition has a heap

Status: learner correctly explained id = 7 → p0 → H0. [HTML lesson](0002-partition-heap.html).

A partition's heap file holds its rows. For our example, p0 has heap H0 and p1 has heap H1; these names are teaching labels, not literal identifiers. The logical table groups the partitions, but the selected partition tells us which heap receives the row.

For id = 10: select p1, then store the row in H1. Here, heap means database row storage, not process memory allocated by malloc. A heap file consists of pages; we defer page details to avoid adding another concept now.

Source: [partition_find_partition_for_record](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3558) copies the selected partition's class_hfid into the output heap identifier. See also the existing foundations chapter and its evidence map.

Check: Under p0: id < 10 and p1: id >= 10, a new row has id = 7. Which heap receives it: H0 or H1? Explain the selection in one sentence.
