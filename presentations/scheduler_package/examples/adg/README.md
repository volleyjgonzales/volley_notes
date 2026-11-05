# Space-time table to ADG

Companion code for doc 05, section "From a space-time table to an ADG: the algorithm".

```bash
g++ -std=c++20 -O2 -Wall -Wextra -o space_time_to_adg space_time_to_adg.cpp
./space_time_to_adg          # compare with expected_output.txt
```

Needs only the header-only part of Boost.Graph (`libboost-graph-dev`; C++20 for designated initializers; tested with Boost 1.83 and g++ 13).
It builds the ADG twice, with the pairwise rule of Hönig et al. (O(n^2)) and with a per-cell sweep
(O(n log n)), and checks that both give the same reachability. It also prints a topological order and
the depth levels, and shows that a three-robot rotation is rejected as a cycle.
