#include <boost/graph/adjacency_list.hpp>
#include <iostream>
#include <string>

int main() {
  // 1. Parallel edges: the out-edge container decides whether a repeated edge is kept
  boost::adjacency_list<boost::vecS, boost::vecS, boost::directedS> gv;
  boost::adjacency_list<boost::setS, boost::vecS, boost::directedS> gs;
  boost::add_edge(0, 1, gv); auto [ev, added_v] = boost::add_edge(0, 1, gv);
  boost::add_edge(0, 1, gs); auto [es, added_s] = boost::add_edge(0, 1, gs);
  std::cout << "vecS out-edges: second add_edge added=" << added_v << ", num_edges=" << boost::num_edges(gv) << "\n";
  std::cout << "setS out-edges: second add_edge added=" << added_s << ", num_edges=" << boost::num_edges(gs) << "\n";

  // 2. Removing a vertex renumbers the later ones when vertices are stored in a vecS
  boost::adjacency_list<boost::vecS, boost::vecS, boost::directedS, std::string> g;
  for (const char* name : {"A", "B", "C", "D"}) { boost::add_vertex(name, g); }
  auto cached = 3;                                   // "D", remembered by someone else
  std::cout << "before: vertex 3 is " << g[cached] << "\n";
  boost::clear_vertex(1, g);                         // drop B's edges first (none here)
  boost::remove_vertex(1, g);                        // remove "B"
  std::cout << "after removing vertex 1: vertices =";
  for (auto [vi, end] = boost::vertices(g); vi != end; ++vi) { std::cout << " " << *vi << ":" << g[*vi]; }
  std::cout << "; the cached index 3 is now out of range (num_vertices = " << boost::num_vertices(g) << ")\n";
}
