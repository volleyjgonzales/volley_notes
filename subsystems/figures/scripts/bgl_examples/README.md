# Boost.Graph primer examples

The complete programs shown in `boost-graph-primer.md` (Part I steps 1–10, and the Volley example of section 14).
Each one builds on its own with Boost 1.83 and a C++20 compiler:

```bash
for f in ex*.cpp; do g++ -std=c++20 -Wall -Wextra "$f" -o "${f%.cpp}" && "./${f%.cpp}"; done
```

`ex5`–`ex7` include `graph_abcd.hpp`, which builds the four-place example graph.
