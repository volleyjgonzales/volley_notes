// space_time_to_adg.cpp — build an action dependency graph (ADG) from a space-time table.
//
// Companion to doc 05 ("From a timed plan to an ADG"). Self-contained: C++17 and header-only Boost.Graph.
//   g++ -std=c++17 -O2 -Wall -Wextra -o space_time_to_adg space_time_to_adg.cpp && ./space_time_to_adg
//
// Input: a space-time table, table[robot][t] = the location (cell) robot occupies at integer time t.
// Output: the ADG. One vertex per action (a move between two different cells); Type 1 edges chain each
// robot's actions; Type 2 edges hand a cell over from the robot leaving it to the next robot entering it.
//
// Two Type 2 constructions are shown:
//   AddType2EdgesPairwise — the rule of Hönig et al. (RA-L 2019, Algorithm 1): compare every pair, O(n^2).
//   AddType2EdgesSweep    — per cell, sort the visits by time and link only consecutive visitors,
//                           O(n log n). It gives the same order (same reachability) with fewer edges.

#include <algorithm>
#include <iostream>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/topological_sort.hpp>

// ---------------------------------------------------------------------------------------------
// Types

using Cell = std::string;
using SpaceTimeTable = std::vector<std::vector<Cell>>;  // [robot][t] -> cell

struct Action {                 // vertex payload: a^i_k in the text
  int robot = 0;                // i
  int index = 0;                // k, counting from 1 in the robot's plan
  int start_time = 0;           // t^i_k: the move starts at t and arrives at t + 1
  Cell from;                    // s^i_k
  Cell to;                      // g^i_k
};

enum class EdgeType { kType1, kType2 };
struct Dependency {             // edge payload
  EdgeType type = EdgeType::kType1;
};

// vecS/vecS: vertices and out-edge lists in std::vector, so a Vertex is a std::size_t index.
// bidirectionalS: keep in-edges too, so in_degree()/in_edges() are cheap (predecessors = parents).
using Adg = boost::adjacency_list<boost::vecS, boost::vecS, boost::bidirectionalS, Action, Dependency>;
using Vertex = Adg::vertex_descriptor;

// ---------------------------------------------------------------------------------------------
// Step 1: table -> actions. A robot that stays in the same cell from t to t + 1 is waiting; waits are
// not vertices (they never need to be dispatched, and dependencies already make every real wait).

std::vector<std::vector<Action>> ExtractActions(const SpaceTimeTable& table) {
  std::vector<std::vector<Action>> actions(table.size());
  for(int i = 0; i < static_cast<int>(table.size()); ++i) {
    const auto& row = table[i];
    for(int t = 0; t + 1 < static_cast<int>(row.size()); ++t) {
      if(row[t] != row[t + 1]) {
        actions[i].push_back(Action {i, static_cast<int>(actions[i].size()) + 1, t, row[t], row[t + 1]});
      }
    }
  }
  return actions;
}

// Step 2: one vertex per action. ids[i][k - 1] is the vertex of a^i_k.
std::vector<std::vector<Vertex>> AddVertices(Adg& g, const std::vector<std::vector<Action>>& actions) {
  std::vector<std::vector<Vertex>> ids(actions.size());
  for(std::size_t i = 0; i < actions.size(); ++i) {
    for(const Action& a : actions[i]) {
      ids[i].push_back(boost::add_vertex(a, g));  // the bundle is copied into the graph
    }
  }
  return ids;
}

// Step 3: Type 1 edges, a^i_k -> a^i_{k+1}.
void AddType1Edges(Adg& g, const std::vector<std::vector<Vertex>>& ids) {
  for(const auto& chain : ids) {
    for(std::size_t k = 0; k + 1 < chain.size(); ++k) {
      boost::add_edge(chain[k], chain[k + 1], Dependency {EdgeType::kType1}, g);
    }
  }
}

// Step 4a: Type 2 edges by the pairwise rule:
//   a^i_k -> a^j_l  if  i != j,  s^i_k == g^j_l,  t^i_k <= t^j_l
void AddType2EdgesPairwise(Adg& g) {
  const auto [first, last] = boost::vertices(g);
  for(auto u = first; u != last; ++u) {
    for(auto v = first; v != last; ++v) {
      const Action& leave = g[*u];
      const Action& enter = g[*v];
      if(leave.robot != enter.robot && leave.from == enter.to && leave.start_time <= enter.start_time) {
        boost::add_edge(*u, *v, Dependency {EdgeType::kType2}, g);
      }
    }
  }
}

// Step 4b: Type 2 edges by a sweep per cell. A "visit" is one stay of one robot in one cell: it begins with
// the action that enters the cell (none for the robot's start cell) and ends with the action that leaves it
// (none if the robot never leaves). Sorted by arrival time, each visit must end before the next one by a
// different robot begins; that hand-over is exactly one Type 2 edge. Edges to later visitors are implied
// through the next visitor's own Type 1 chain, so they are not needed.
struct Visit {
  int arrival = -1;                   // -1: the robot starts here
  int robot = 0;
  std::optional<Vertex> enter;        // the action whose goal is this cell
  std::optional<Vertex> leave;        // the action whose start is this cell
};

void AddType2EdgesSweep(Adg& g, const SpaceTimeTable& table, const std::vector<std::vector<Vertex>>& ids) {
  std::map<Cell, std::vector<Visit>> visits;
  for(int i = 0; i < static_cast<int>(ids.size()); ++i) {
    Visit current {-1, i, std::nullopt, std::nullopt};
    Cell here = table[i].front();
    for(Vertex v : ids[i]) {
      current.leave = v;                                   // this action leaves `here`
      visits[here].push_back(current);
      here = g[v].to;
      current = Visit {g[v].start_time + 1, i, v, std::nullopt};  // ... and enters its goal at t + 1
    }
    visits[here].push_back(current);                       // the last stay never ends
  }
  for(auto& [cell, list] : visits) {
    std::sort(list.begin(), list.end(), [](const Visit& a, const Visit& b) {
      return std::tie(a.arrival, a.robot) < std::tie(b.arrival, b.robot);
    });
    for(std::size_t n = 0; n + 1 < list.size(); ++n) {
      const Visit& prev = list[n];
      const Visit& next = list[n + 1];
      if(prev.robot == next.robot) {
        continue;                                          // ordered by that robot's Type 1 chain
      }
      if(!prev.leave || !next.enter) {
        throw std::runtime_error("invalid plan: two robots occupy cell " + cell + " for good");
      }
      if(g[*prev.leave].start_time > g[*next.enter].start_time) {
        throw std::runtime_error("invalid plan: robots overlap in cell " + cell);
      }
      boost::add_edge(*prev.leave, *next.enter, Dependency {EdgeType::kType2}, g);
    }
  }
}

// Step 5: an ADG must be acyclic. boost::topological_sort throws boost::not_a_dag on a cycle; it writes
// vertices in reverse topological order, so reverse the result.
std::vector<Vertex> TopologicalOrder(const Adg& g) {
  std::vector<Vertex> order;
  boost::topological_sort(g, std::back_inserter(order));
  std::reverse(order.begin(), order.end());
  return order;
}

// ---------------------------------------------------------------------------------------------
// Helpers for the demonstration

std::string Name(const Adg& g, Vertex v) {
  const Action& a = g[v];
  return "a" + std::to_string(a.robot + 1) + "." + std::to_string(a.index) + " (" + a.from + "->" + a.to +
         " @" + std::to_string(a.start_time) + ")";
}

// reach[u][v] == true if there is a path u ~> v. Fine for small graphs; O(V * (V + E)).
std::vector<std::vector<bool>> Reachability(const Adg& g) {
  const std::size_t n = boost::num_vertices(g);
  std::vector<std::vector<bool>> reach(n, std::vector<bool>(n, false));
  for(Vertex v : [&] { auto o = TopologicalOrder(g); std::reverse(o.begin(), o.end()); return o; }()) {
    for(auto e : boost::make_iterator_range(boost::out_edges(v, g))) {
      const Vertex w = boost::target(e, g);
      reach[v][w] = true;
      for(std::size_t x = 0; x < n; ++x) {
        if(reach[w][x]) reach[v][x] = true;
      }
    }
  }
  return reach;
}

// depth(v) = number of edges on the longest path ending at v. Vertices of equal depth are pairwise
// unordered (an edge u -> v forces depth(v) > depth(u)), so each depth is a set that can run together.
std::vector<int> Depths(const Adg& g) {
  std::vector<int> depth(boost::num_vertices(g), 0);
  for(Vertex v : TopologicalOrder(g)) {
    for(auto e : boost::make_iterator_range(boost::in_edges(v, g))) {
      depth[v] = std::max(depth[v], depth[boost::source(e, g)] + 1);
    }
  }
  return depth;
}

void Print(const Adg& g, const std::string& title) {
  std::cout << title << ": " << boost::num_vertices(g) << " vertices, " << boost::num_edges(g) << " edges\n";
  for(auto e : boost::make_iterator_range(boost::edges(g))) {
    std::cout << "  " << (g[e].type == EdgeType::kType1 ? "Type 1  " : "Type 2  ")
              << Name(g, boost::source(e, g)) << "  ->  " << Name(g, boost::target(e, g)) << "\n";
  }
}

Adg Build(const SpaceTimeTable& table, bool pairwise) {
  Adg g;
  const auto actions = ExtractActions(table);
  const auto ids = AddVertices(g, actions);
  AddType1Edges(g, ids);
  if(pairwise) {
    AddType2EdgesPairwise(g);
  }
  else {
    AddType2EdgesSweep(g, table, ids);
  }
  TopologicalOrder(g);  // throws boost::not_a_dag if the plan needs synchronous moves
  return g;
}

int main() {
  // The example of doc 05, Figure 2. Columns are t = 0..4.
  const SpaceTimeTable table = {
      {"A", "B", "C", "C", "C"},  // AGV 1: A -> B at t=0, B -> C at t=1
      {"D", "D", "D", "B", "E"},  // AGV 2: waits, D -> B at t=2, B -> E at t=3
      {"C", "F", "F", "F", "F"},  // AGV 3: C -> F at t=0
  };

  const Adg pairwise = Build(table, /*pairwise=*/true);
  const Adg sweep = Build(table, /*pairwise=*/false);
  Print(pairwise, "Pairwise rule");
  Print(sweep, "Sweep");
  std::cout << "Same order (same reachability): " << std::boolalpha
            << (Reachability(pairwise) == Reachability(sweep)) << "\n";

  std::cout << "One topological order:";
  for(Vertex v : TopologicalOrder(sweep)) std::cout << "  " << Name(sweep, v);
  std::cout << "\nDepth levels (each level can run in parallel):\n";
  const auto depth = Depths(sweep);
  for(int d = 0; d <= *std::max_element(depth.begin(), depth.end()); ++d) {
    std::cout << "  level " << d << ":";
    for(Vertex v = 0; v < boost::num_vertices(sweep); ++v) {
      if(depth[v] == d) std::cout << "  " << Name(sweep, v);
    }
    std::cout << "\n";
  }

  // Three robots pass through cell B one after another. The pairwise rule also links the first robot to the
  // third (an implied edge); the sweep links only consecutive visitors. Same order, one edge fewer.
  const SpaceTimeTable corridor = {
      {"A", "B", "C", "C", "C"},  // R1: A -> B at t=0, B -> C at t=1
      {"D", "D", "B", "E", "E"},  // R2: D -> B at t=1 (enters as R1 leaves), B -> E at t=2
      {"F", "F", "F", "B", "G"},  // R3: F -> B at t=2, B -> G at t=3
  };
  const Adg corridor_pairwise = Build(corridor, /*pairwise=*/true);
  const Adg corridor_sweep = Build(corridor, /*pairwise=*/false);
  Print(corridor_pairwise, "Corridor, pairwise rule");
  Print(corridor_sweep, "Corridor, sweep");
  std::cout << "Same order (same reachability): "
            << (Reachability(corridor_pairwise) == Reachability(corridor_sweep)) << "\n";

  // A rotation: three robots move X->Y, Y->Z, Z->X at the same instant. The rule creates a cycle.
  const SpaceTimeTable rotation = {{"X", "Y"}, {"Y", "Z"}, {"Z", "X"}};
  try {
    Build(rotation, /*pairwise=*/true);
  }
  catch(const boost::not_a_dag&) {
    std::cout << "Rotation: not a DAG (the plan needs synchronous moves)\n";
  }
  return 0;
}
