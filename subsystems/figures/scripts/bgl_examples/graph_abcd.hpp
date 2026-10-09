#pragma once
#include <boost/graph/adjacency_list.hpp>
#include <string>
struct Place { std::string name; double x_m = 0.0; double y_m = 0.0; };
struct Road { double length_m = 0.0; };
using Graph = boost::adjacency_list<boost::vecS, boost::vecS, boost::directedS, Place, Road>;
using Vertex = boost::graph_traits<Graph>::vertex_descriptor;
using Edge = boost::graph_traits<Graph>::edge_descriptor;
inline Graph MakeAbcd() {
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
  return g;
}
