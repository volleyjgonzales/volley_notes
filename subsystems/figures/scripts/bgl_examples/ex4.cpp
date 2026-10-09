#include <boost/graph/adjacency_list.hpp>
#include <iostream>
#include <string>

struct Place {             // the data stored in every vertex (the vertex "bundle")
  std::string name;
  double x_m = 0.0;
  double y_m = 0.0;
};
struct Road {              // the data stored in every edge (the edge "bundle")
  double length_m = 0.0;
};
using Graph = boost::adjacency_list<boost::vecS, boost::vecS, boost::directedS, Place, Road>;

int main() {
  Graph g;
  auto a = boost::add_vertex(Place{"A", 0.0, 0.0}, g);
  auto b = boost::add_vertex(Place{"B", 3.0, 1.0}, g);
  auto c = boost::add_vertex(Place{"C", 2.0, 0.0}, g);
  auto d = boost::add_vertex(Place{"D", 6.0, 1.0}, g);
  boost::add_edge(a, b, Road{5.0}, g);
  boost::add_edge(a, c, Road{2.0}, g);
  boost::add_edge(c, b, Road{1.5}, g);
  boost::add_edge(b, d, Road{3.0}, g);
  boost::add_edge(c, d, Road{6.0}, g);
  g[c].name += " (renamed)";                          // write through g[vertex]
  for (auto [ei, end] = boost::edges(g); ei != end; ++ei) {
    std::cout << g[boost::source(*ei, g)].name << " -> " << g[boost::target(*ei, g)].name
              << " : " << g[*ei].length_m << " m\n";   // read through g[edge]
  }
}
