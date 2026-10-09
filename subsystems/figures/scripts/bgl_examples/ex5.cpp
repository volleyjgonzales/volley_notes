#include "graph_abcd.hpp"
#include <boost/property_map/property_map.hpp>
#include <iostream>
#include <vector>

int main() {
  Graph g = MakeAbcd();
  // Interior map: reads Road::length_m straight out of each edge's bundle
  auto length = boost::get(&Road::length_m, g);
  // The vertex index map: vertex -> 0..n-1 (the identity for vecS vertex storage)
  auto index = boost::get(boost::vertex_index, g);
  // Exterior map: a plain std::vector, addressed through the index map
  std::vector<int> visits(boost::num_vertices(g), 0);
  auto visit_map = boost::make_iterator_property_map(visits.begin(), index);

  for (auto [ei, end] = boost::edges(g); ei != end; ++ei) {
    Vertex t = boost::target(*ei, g);
    boost::put(visit_map, t, boost::get(visit_map, t) + 1);       // put / get on the exterior map
    std::cout << "edge into " << g[t].name << ": get(length, e) = " << boost::get(length, *ei)
              << ", index of target = " << boost::get(index, t) << "\n";
  }
  for (Vertex v = 0; v < boost::num_vertices(g); ++v) {
    std::cout << g[v].name << " has in-degree " << visits[v] << "\n";
  }
}
