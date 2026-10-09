#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/topological_sort.hpp>
#include <algorithm>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

using Dag = boost::adjacency_list<boost::vecS, boost::vecS, boost::bidirectionalS, std::string>;

int main() {
  Dag g;
  for (const char* task : {"lift tray", "drive to VRC", "ride VRC", "open bay", "drive to bay"}) { boost::add_vertex(task, g); }
  boost::add_edge(0, 1, g); boost::add_edge(1, 2, g); boost::add_edge(2, 4, g); boost::add_edge(3, 4, g);
  std::vector<boost::graph_traits<Dag>::vertex_descriptor> order;
  boost::topological_sort(g, std::back_inserter(order));   // writes the REVERSE of a topological order
  std::reverse(order.begin(), order.end());
  std::cout << "order:";
  for (auto v : order) { std::cout << " [" << g[v] << "]"; }
  std::cout << "\n";
  boost::add_edge(4, 0, g);                                 // create a cycle
  try { order.clear(); boost::topological_sort(g, std::back_inserter(order)); }
  catch (const boost::not_a_dag& e) { std::cout << "with a cycle: " << e.what() << "\n"; }
}
