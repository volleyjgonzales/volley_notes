#include <boost/graph/adjacency_list.hpp>
#include <iostream>

template <typename Graph>
void Describe(const char* name) {
  Graph g;
  boost::add_edge(0, 1, g); boost::add_edge(0, 2, g); boost::add_edge(2, 1, g);
  boost::add_edge(1, 3, g); boost::add_edge(2, 3, g);
  std::cout << name << ": edges = " << boost::num_edges(g) << "; out_edges(1) =";
  for (auto [ei, end] = boost::out_edges(1, g); ei != end; ++ei) { std::cout << " " << boost::target(*ei, g); }
  if constexpr (std::is_same_v<typename boost::graph_traits<Graph>::directed_category,
                               boost::bidirectional_tag>) {
    std::cout << "; in_edges(1) from";
    for (auto [ei, end] = boost::in_edges(1, g); ei != end; ++ei) { std::cout << " " << boost::source(*ei, g); }
  }
  std::cout << "\n";
}

int main() {
  Describe<boost::adjacency_list<boost::vecS, boost::vecS, boost::directedS>>("directedS     ");
  Describe<boost::adjacency_list<boost::vecS, boost::vecS, boost::undirectedS>>("undirectedS   ");
  Describe<boost::adjacency_list<boost::vecS, boost::vecS, boost::bidirectionalS>>("bidirectionalS");
}
