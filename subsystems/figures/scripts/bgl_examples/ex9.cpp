#include <boost/graph/adjacency_list.hpp>
#include <boost/property_map/vector_property_map.hpp>
#include <iostream>

struct Road { double length_m = 0.0; };
// Edge properties: a tagged edge_index (found by its tag) chained to the Road bundle (found by g[e])
using Graph = boost::adjacency_list<boost::vecS, boost::vecS, boost::bidirectionalS, boost::no_property,
                                    boost::property<boost::edge_index_t, std::size_t, Road>>;

int main() {
  Graph g;
  auto index = boost::get(boost::edge_index, g);              // interior tagged map: edge -> size_t
  std::size_t next = 0;
  for (auto [u, v, len] : {std::tuple{0, 1, 5.0}, {0, 2, 2.0}, {2, 1, 1.5}, {1, 3, 3.0}}) {
    auto [e, added] = boost::add_edge(u, v, {next, Road{len}}, g);   // {edge_index, Road}
    boost::put(index, e, next++);
  }
  // A vector-backed map indexed by edge_index: one slot per edge
  boost::vector_property_map<double, decltype(index)> doubled(boost::num_edges(g), index);
  for (auto [ei, end] = boost::edges(g); ei != end; ++ei) {
    boost::put(doubled, *ei, 2.0 * g[*ei].length_m);
    std::cout << "edge " << boost::get(index, *ei) << ": " << boost::source(*ei, g) << " -> "
              << boost::target(*ei, g) << ", g[e].length_m = " << g[*ei].length_m
              << ", doubled[e] = " << boost::get(doubled, *ei) << "\n";
  }
}
