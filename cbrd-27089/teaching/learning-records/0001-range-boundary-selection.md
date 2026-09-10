# Correct partition selection at the range boundary

The learner correctly selected p1 for id = 10 under p0: id < 10 and p1: id >= 10, and excluded p0. This supports moving to the selected partition's heap. They described the exclusion as avoiding a search; the teacher clarified that an insert selects a destination, but independent understanding of read-versus-write pruning remains unassessed.
