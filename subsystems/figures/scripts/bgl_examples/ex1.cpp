#include <boost/graph/adjacency_list.hpp>
#include <iostream>

int main() {
  boost::adjacency_list<> g;            // all seven template parameters left at their defaults
  boost::add_edge(0, 1, g);             // vertices 0 and 1 are created on demand
  boost::add_edge(0, 2, g);
  boost::add_edge(2, 1, g);
  boost::add_edge(1, 3, g);
  boost::add_edge(2, 3, g);
  std::cout << "vertices: " << boost::num_vertices(g) << ", edges: " << boost::num_edges(g) << "\n";
  for (auto [ei, ei_end] = boost::edges(g); ei != ei_end; ++ei) {
    std::cout << "  " << boost::source(*ei, g) << " -> " << boost::target(*ei, g) << "\n";
  }
}
