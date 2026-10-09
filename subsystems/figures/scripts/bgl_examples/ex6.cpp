#include "graph_abcd.hpp"
#include <boost/graph/dijkstra_shortest_paths.hpp>
#include <algorithm>
#include <iostream>
#include <vector>

int main() {
  Graph g = MakeAbcd();
  const Vertex s = 0, t = 3;                                     // A and D
  std::vector<double> dist(boost::num_vertices(g));
  std::vector<Vertex> pred(boost::num_vertices(g));
  auto index = boost::get(boost::vertex_index, g);
  boost::dijkstra_shortest_paths(g, s,
      boost::weight_map(boost::get(&Road::length_m, g))                         // input: w(e)
          .distance_map(boost::make_iterator_property_map(dist.begin(), index))  // output: d(v)
          .predecessor_map(boost::make_iterator_property_map(pred.begin(), index)));  // output: p(v)
  for (Vertex v = 0; v < boost::num_vertices(g); ++v) {
    std::cout << "d(A, " << g[v].name << ") = " << dist[v] << ", predecessor " << g[pred[v]].name << "\n";
  }
  std::vector<Vertex> path;
  for (Vertex v = t; v != s; v = pred[v]) { path.push_back(v); }
  path.push_back(s);
  std::reverse(path.begin(), path.end());
  std::cout << "path:";
  for (Vertex v : path) { std::cout << " " << g[v].name; }
  std::cout << "\n";
}
