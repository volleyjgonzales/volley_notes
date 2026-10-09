#include <boost/graph/adjacency_list.hpp>
#include <boost/property_map/vector_property_map.hpp>
#include <cstdint>
#include <iostream>
#include <unordered_map>
#include <vector>

// Stand-ins for interfaces/GaragePose and common_ros::Transition (same fields)
struct GaragePose { uint32_t node_id = 0; int16_t heading = 0; };
enum class TransitionType { LOCOMOTE, STRAFE, ROTATION, VRC_TRANSITION };
struct Transition { double length = 0.0; TransitionType type = TransitionType::LOCOMOTE; };

// The exact type used by common_ros::GarageGraph
using BoostPoseGraph = boost::adjacency_list<boost::vecS, boost::vecS, boost::bidirectionalS, GaragePose,
    boost::property<boost::edge_index_t, std::size_t, Transition>>;

int main() {
  // Poses in PoseGraph order (node id, then heading): node 1 = A, 2 = B, 3 = C
  const std::vector<GaragePose> poses = {
      {1u, -90},
      {1u, 90},
      {2u, -90},
      {2u, 0},
      {2u, 90},
      {2u, 180},
      {3u, 0},
      {3u, 180}};
  struct Neighbor { int src, dst; double length; TransitionType type; };
  // Non-empty neighbor slots, in GarageGraph's loop order (pose, then slot)
  const std::vector<Neighbor> slots = {
      {0, 2, 4.0, TransitionType::LOCOMOTE},
      {1, 4, 4.0, TransitionType::LOCOMOTE},
      {2, 0, 4.0, TransitionType::LOCOMOTE},
      {2, 5, 1.571, TransitionType::ROTATION},
      {2, 3, 1.571, TransitionType::ROTATION},
      {3, 6, 4.0, TransitionType::LOCOMOTE},
      {3, 2, 1.571, TransitionType::ROTATION},
      {3, 4, 1.571, TransitionType::ROTATION},
      {4, 1, 4.0, TransitionType::LOCOMOTE},
      {4, 3, 1.571, TransitionType::ROTATION},
      {4, 5, 1.571, TransitionType::ROTATION},
      {5, 7, 4.0, TransitionType::LOCOMOTE},
      {5, 4, 1.571, TransitionType::ROTATION},
      {5, 2, 1.571, TransitionType::ROTATION},
      {6, 3, 4.0, TransitionType::LOCOMOTE},
      {7, 5, 4.0, TransitionType::LOCOMOTE}};

  BoostPoseGraph g;
  for (const auto& p : poses) { boost::add_vertex(p, g); }              // vertex i = pose i
  auto edge_index = boost::get(boost::edge_index, g);
  for (const auto& n : slots) {
    std::size_t k = boost::num_edges(g);
    auto [e, added] = boost::add_edge(n.src, n.dst, {k, Transition{n.length, n.type}}, g);
    boost::put(edge_index, e, k);
  }
  std::cout << "num_vertices = " << boost::num_vertices(g) << ", num_edges = " << boost::num_edges(g) << "\n";
  const char* names[] = {"A", "B", "C"};
  const char* types[] = {"LOCOMOTE", "STRAFE", "ROTATION", "VRC_TRANSITION"};
  for (auto [vi, vend] = boost::vertices(g); vi != vend; ++vi) {
    const GaragePose& p = g[*vi];
    std::cout << "vertex " << *vi << " = " << names[p.node_id - 1] << "@" << p.heading
              << "  out-degree " << boost::out_degree(*vi, g) << ", in-degree " << boost::in_degree(*vi, g) << ":";
    for (auto [ei, eend] = boost::out_edges(*vi, g); ei != eend; ++ei) {
      std::cout << "  e" << boost::get(edge_index, *ei) << "->" << boost::target(*ei, g)
                << " (" << types[static_cast<int>(g[*ei].type)] << ", " << g[*ei].length << ")";
    }
    std::cout << "\n";
  }
}
