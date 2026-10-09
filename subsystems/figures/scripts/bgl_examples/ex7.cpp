#include "graph_abcd.hpp"
#include <boost/graph/astar_search.hpp>
#include <boost/graph/breadth_first_search.hpp>
#include <cmath>
#include <iostream>
#include <vector>

// A visitor: BGL calls these member functions at search events
struct PrintingBfsVisitor : boost::default_bfs_visitor {
  void discover_vertex(Vertex u, const Graph& g) const { std::cout << " discover " << g[u].name; }
  void finish_vertex(Vertex u, const Graph& g) const { std::cout << " finish " << g[u].name; }
};

// A* needs a heuristic h(v): here the straight-line distance to the goal
struct StraightLine : boost::astar_heuristic<Graph, double> {
  StraightLine(const Graph& g, Vertex goal) : g_(&g), goal_(goal) {}
  double operator()(Vertex v) const {
    return std::hypot((*g_)[v].x_m - (*g_)[goal_].x_m, (*g_)[v].y_m - (*g_)[goal_].y_m);
  }
  const Graph* g_; Vertex goal_;
};
struct FoundGoal {};                                   // thrown to stop the search early
struct GoalVisitor : boost::default_astar_visitor {
  explicit GoalVisitor(Vertex goal) : goal_(goal) {}
  void examine_vertex(Vertex u, const Graph& g) const {
    std::cout << " examine " << g[u].name;
    if (u == goal_) { throw FoundGoal{}; }
  }
  Vertex goal_;
};

int main() {
  Graph g = MakeAbcd();
  std::cout << "BFS from A:";
  boost::breadth_first_search(g, 0, boost::visitor(PrintingBfsVisitor{}));
  std::cout << "\n";

  std::vector<double> dist(boost::num_vertices(g));
  std::vector<Vertex> pred(boost::num_vertices(g));
  auto index = boost::get(boost::vertex_index, g);
  std::cout << "A* from A to D:";
  try {
    boost::astar_search(g, Vertex{0}, StraightLine{g, 3},
        boost::weight_map(boost::get(&Road::length_m, g))
            .distance_map(boost::make_iterator_property_map(dist.begin(), index))
            .predecessor_map(boost::make_iterator_property_map(pred.begin(), index))
            .visitor(GoalVisitor{3}));
    std::cout << "\n goal not reachable\n";
  } catch (const FoundGoal&) {
    std::cout << "\n reached D with d = " << dist[3] << "\n";
  }
}
