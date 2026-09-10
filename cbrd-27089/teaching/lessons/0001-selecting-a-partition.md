# Lesson 0001: Which partition receives the row?

Status: learner correctly selected p1 for id = 10. Insert-versus-search wording clarified; revisit later. [HTML lesson](0001-selecting-a-partition.html).

## One idea

For an insert, translate **partition pruning** as **selecting the partition that should receive this row**. The word pruning emphasizes ruling out destinations that do not match. It does not mean deleting stored rows or removing partitions.

Imagine a table with these rules, using non-NULL integer ids:

| Partition | Rule |
|---|---|
| p0 | id < 10 |
| p1 | id >= 10 |

A new row with id = 3 belongs in p0: 3 satisfies p0's rule and does not satisfy p1's rule. You insert through the table; the database selects the destination partition using the rules.

## Why this matters for the PR

Before discussing where the row's large values should live, we need to know where the row itself belongs. Do not introduce heap layout or OOS chunk format yet.

## Source anchor

In the [pinned `partition_prune_insert`](https://github.com/CUBRID/cubrid/blob/b871ea386d2c5419b7abae07dda58b9b7f36377a/src/query/partition.c#L3583), the comments describe `pruned_class_oid` as the partition to insert into. The function calls `partition_find_partition_for_record`. This is a source fact; the two numeric rules above are a teaching example.

## Check before advancing

A new row has id = 10. Which partition receives it, and what does pruning rule out here?

Answer in the conversation for immediate feedback. Ask a follow-up if any word is unclear; no source reading is required to answer this question.
