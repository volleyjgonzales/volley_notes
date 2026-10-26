# 05 — Action graph: from timed motions to the schedule

*Stage 5 of the pipeline: the scheduler turns CHUGG's timed motions into an action dependency graph (ADG), the order Dispatch executes. The tab builds the idea from first principles, then shows the action DAG the scheduler actually builds, and closes with a review of the whole pipeline before the proposal.*

A planner produces a *timed* plan: who moves where, and when. Robots never keep to those times exactly. An **action dependency graph** (ADG) keeps what matters for safety, the *order* in which robots use shared space, and drops the exact times. That lets a fleet execute a plan correctly while every robot runs early or late.

This tab builds on the `ContinuousState` timeline from the Motion planning tab. Part I (sections [1](#ad-why-a-timed-plan-is-not-enough)–[5](#ad-beyond-the-basic-adg)) builds the idea from scratch: the graph theory it needs, the construction rule, how a dispatcher executes an ADG and why that is safe, and how timing works on it. Part II (sections [6](#ad-the-adg-in-our-software)–[8](#ad-references)) shows that the scheduler's response, `PlanResponse.schedule`, is an ADG: how `ResponseFromTrajectories` builds it, and where that code follows the textbook rule and where it differs; it ends with review questions and the references for the whole tab. Part III (sections [8](#bg-faq-design-questions)–[9](#bg-known-limitations-and-reading-checkpoint)) looks back over the whole pipeline: design notes, known limitations and a checkpoint before the proposal. The mathematics is light: sets, relations and one recurrence.

## Why a timed plan is not enough

The motion planner (CHUGG, [section 21](#bg-motion-planning-and-the-response)) returns, for every AGV, a list of motions with start and end times, chosen so that no two footprints overlap at any moment. That guarantee holds only if every AGV is exactly on time. In practice an AGV is slowed by acceleration limits, a door, a lift, wheel slip or a late command acknowledgement. Others finish early.

[Figure 1](#ad-fig-84_adg_delay) shows the failure. Two AGVs cross the same cell `B`, AGV-1 first. If AGV-1's first move is late and each AGV starts its moves at the planned times, AGV-2 drives into `B` while AGV-1 is still there. The plan was collision-free; executing it by the clock is not.

![Why a timed plan needs an ADG](figures/84_adg_delay.svg)

**Timestamps versus dependencies.** Panel 1: the plan. Panel 2: AGV-1's first move takes 2.5 s instead of 1 s; executed by the clock, AGV-2 enters `B` while AGV-1 is still in it. Panel 3: executed by dependencies, AGV-2's move into `B` waits until AGV-1's move out of `B` has finished. The order is the plan's; only the times change.

There are three ways out:

- **Replan on every deviation.** Correct, but planning takes time (a `Plan()` call can take seconds), and robots must stop while it runs.
- **Pad the times.** Add margins so small delays do not matter. This wastes throughput all the time and still fails on a large delay.
- **Keep the order, not the times.** Record, for every place two robots share, which one goes first. Then let each robot start an action as soon as everything that must happen before it has happened. This is the ADG.

The third option needs no replanning for delays and no padding. It is safe for any amount of delay, provided the robots stay on their planned paths and report when they finish an action. Delays then only shift times; they never change the order.

## Graphs and orders, from scratch

The Background tab introduces DAGs for the event DAG ([section 13](#bg-directed-acyclic-graphs-then-scheduleeventdag)). This section restates the parts an ADG needs, with the definitions written out.

### Directed graphs and paths

A **directed graph** is a pair G = (V, E): a finite set of vertices V and a set of edges E \subseteq V \times V. An edge (u, v), written u \to v, points from u to v. In an ADG, u \to v means "u must finish before v may start".

- The **predecessors** of v are \mathrm{pred}(v) = \\u : u \to v\\, and its **successors** are \mathrm{succ}(v) = \\w : v \to w\\.
- A **path** from u to v is a sequence u = x_0 \to x_1 \to \dots \to x_n = v with n \ge 1. Write u \rightsquigarrow v if one exists: v is **reachable** from u.
- A **cycle** is a path from a vertex back to itself.

### DAGs are partial orders

A **directed acyclic graph** (DAG) has no cycle. Read u \rightsquigarrow v as "u happens before v" and write it u \prec v. In a DAG this relation is:

- **irreflexive**: no v \prec v, because that would be a cycle;
- **transitive**: u \prec v and v \prec w give u \prec w, by joining the paths.

Such a relation is a **strict partial order**. "Partial" is the important word: two vertices can be **unordered**, neither u \prec v nor v \prec u. Write that u \parallel v. Unordered actions may run in any order, or at the same time. That freedom is what an ADG gives a fleet: it fixes only the orders that safety needs and leaves everything else concurrent.

Conversely, a graph with a cycle cannot be read as "before": the cycle would say that something happens before itself.

### Topological orders

A **topological order** lists the vertices as v_1, v_2, \dots, v_n so that every edge points forward: v_i \to v_j \implies i \lt j. It is one way to serialise the partial order.

- **A topological order exists if and only if the graph is a DAG.** If there is a cycle, its vertices cannot all point forward. If there is none, Kahn's algorithm builds one: repeatedly output a vertex with no remaining predecessors and delete it. A finite DAG always has such a vertex (otherwise you could walk backwards forever, and with finitely many vertices you would revisit one: a cycle).
- **There are usually many.** Any two unordered vertices can be listed either way round. Which one an algorithm returns depends on its tie-breaking, which is why the refactor proposal pays attention to `AddEvent` order ([section 6.5](#pr-why-return-a-result-and-how-it-is-applied)).
- `DagBase::GetTopologicalOrdering` uses `boost::topological_sort` (a depth-first search) and returns `std::nullopt` if the graph has a cycle. That is how the scheduler detects one.

### Topological orders and parallelism

A topological order is a single sequence, so it is natural to worry that using one turns parallel work into serial work. It does not, because a topological order is a way to **list** a DAG, not a way to **run** it. Execution never follows the list; it follows the edges.

- **The list keeps every edge.** When a DAG is written out in topological order, each vertex carries its predecessors. `Schedule.nodes` does this with `parents`, indices that always point backwards in the array. Nothing is lost: the graph can be rebuilt exactly from the list.
- **Unordered actions can appear in either order.** In [Figure 2](#ad-fig-90_adg_topo_vs_parallel) the example ADG has two topological orders. a^1_1 and a^3_1 swap places between them because neither constrains the other. In general, u \parallel v exactly when some topological order puts u first and another puts v first. A partial order equals the intersection of all its topological orders (Szpilrajn, 1930). So the parallelism is visible in the *set* of topological orders, and any one of them is an arbitrary tie-break.
- **Execution is driven by readiness, not position.** The dispatcher starts every action whose predecessors are done, whatever its index. That is Kahn's algorithm run live: "remove a vertex" happens when a robot reports completion, and every vertex whose last predecessor has gone joins the *ready set*. The size of the ready set is the parallelism available at that moment. At t = 0 in the example it holds a^1_1 and a^3_1, and both robots move.
- **Running the array in index order would be wrong.** A consumer that ignored `parents` and executed `Schedule.nodes` one entry at a time would turn the example's makespan of 10 into 12 (the lower chart of [Figure 2](#ad-fig-90_adg_topo_vs_parallel)). It would be safe but needlessly slow, and it is a misreading of the format.

![Topological orders and parallelism](figures/90_adg_topo_vs_parallel.svg)

**Listing versus running.** (1) The example ADG; a^1_1 and a^3_1 are unordered. (2) Its two topological orders as arrays. Every dependency edge runs parent → child, so in a topological order the arrows always point forward (left to right). Each entry also stores `p`, the indices of its parents, which are always smaller than its own. The two unordered actions swap places between the orders. (3) Running by dependencies finishes at 10 with two robots moving at the start; running the array one entry at a time finishes at 12. (4) The ready set after each completion, which is what a dispatcher acts on.

**Edges point forward; the stored indices point back.** A dependency always runs from parent to child, so in a topological order every edge points forward. That is the definition. The *wire format* stores each edge at its child end: `ActionNode.parents` lists the indices of the node's parents, which are earlier in the array. This is a representation choice, not a different kind of edge. An edge list, a parent list or a child list all describe the same graph; Boost's `bidirectionalS` keeps both in-edges and out-edges for the same reason. Storing parents suits this format for three reasons:

- **Readiness is a question about parents.** "May this action start?" means "are all its parents finished?", so a node that carries its parents can answer by itself.
- **The array can be written and read in one pass.** When `BuildScheduledActionsArray` writes a node, its parents have already been written, so their indices are known (`action_node_to_index`). Child indices would be forward references to entries not yet written.
- **Acyclicity is checkable on receipt.** If every parent index is smaller than the node's own index, the graph cannot contain a cycle.

A dispatcher that wants the other direction ("which actions might become ready when this one finishes?") inverts the parent lists into child lists once, in O(\|V\| + \|E\|).

So what is a single topological order *for*? Every use is about processing the graph, never about executing it:

- **Checking for cycles.** If no order exists, the graph has a cycle.
- **One-pass computations.** Any value that depends only on predecessors (earliest start, the reachability matrix in `Reduce()`, depth levels) can be computed in a single sweep in topological order, because every predecessor has been handled before the vertex itself.
- **Serialising.** `Schedule.nodes` is written in topological order so that a receiver can rebuild the graph in one pass, with every parent already seen.
- **Deciding in a fixed order.** Tray assignment and CHUGG walk the *event* DAG in topological order. That is the order they make decisions in, one event at a time, not the order robots move in. CHUGG plans events strictly one after another in that order ([section 21.1](#bg-inside-solvesequential)) but gives them times that overlap whenever the footprints allow, and the action DAG built from those times keeps the overlap.

Another serialisation that does show the parallelism is the **depth level**. Let \mathrm{depth}(v) be the number of edges on the longest path ending at v. An edge u \to v forces \mathrm{depth}(v) \gt \mathrm{depth}(u), so vertices of equal depth are pairwise unordered and can run together. Listing level by level gives a topological order grouped into parallel batches. The C++ example in [section 3.5](#ad-from-a-space-time-table-to-an-adg) prints them.

### Transitive reduction

Many edge sets give the same order. If u \to v \to w, adding u \to w changes nothing: it is **implied**. The **transitive reduction** G^- of a DAG is the graph with the same reachability and as few edges as possible. For a finite DAG it is **unique**: it is exactly the set of edges u \to v for which no other path from u to v exists (Aho, Garey and Ullman, 1972).

E^- = \\(u, v) \in E : \text{there is no path } u \rightsquigarrow v \text{ that avoids the edge } (u, v)\\

Two consequences matter here:

- **A builder may add implied edges freely** and reduce at the end; the order is the same. The scheduler's action DAG builder does exactly this.
- **Two DAGs on the same vertices have the same order if and only if their reductions are equal.** That makes the reduced graph a good thing to compare in parity tests.

`DagBase::Reduce()` computes it in three passes. It first takes a topological order. It then builds a reachability matrix by walking that order backwards, giving each vertex the union of its successors' reachable sets. Finally it drops an edge u \to v when another successor w of u already reaches v. The cost is O(\|V\| \cdot \|E\|) time and \|V\|^2 bits of memory: trivial for a few hundred actions, but worth knowing.

## From a timed plan to an ADG

The construction below is the one in Hönig, Kiesel, Tinka, Durham and Ayanian, "Persistent and Robust Execution of MAPF Schedules in Warehouses" (IEEE RA-L, 2019). That paper introduced the name. The idea goes back to the *temporal plan graph* of Hönig et al. (ICAPS 2016).

### Plans and actions

Each robot i has a plan, a sequence of timed actions:

p^i = \big( (t^i_1, a^i_1, s^i_1, g^i_1), \\ (t^i_2, a^i_2, s^i_2, g^i_2), \\ \dots, \\ (t^i\_{n_i}, a^i\_{n_i}, s^i\_{n_i}, g^i\_{n_i}) \big)

Read each symbol like this:

| Symbol       | Meaning                                                                                                                                      | In the example of [Figure 2](#ad-fig-85_adg_construction) |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| i, j         | Which robot                                                                                                                                  | AGV-1, AGV-2, AGV-3                                       |
| k, l         | Which of that robot's actions, counting from 1 in plan order                                                                                 | AGV-1 has two actions, so k \in \\1, 2\\                  |
| a^i_k        | **a** for *action*: the k-th action of robot i. Superscript = robot, subscript = position in its plan. It is a name, not a number or a power | a^1_2 is AGV-1's second action                            |
| s^i_k, g^i_k | The action's **s**tart location and **g**oal location (cells of the map)                                                                     | s^1_2 = \mathrm{B}, g^1_2 = \mathrm{C}                    |
| t^i_k        | The action's planned start time                                                                                                              | t^1_2 = 1                                                 |
| p^i, n_i     | Robot i's whole plan, and the number of actions in it                                                                                        | n_1 = 2, n_3 = 1                                          |

So the vertex drawn as a^1_2 with "B -\> C, t = 1" underneath means: *AGV-1's second action moves it from cell B to cell C, and the plan starts it at time 1*. Consecutive actions connect, g^i_k = s^i\_{k+1}: AGV-1's first action ends in B, where its second starts. Map cells are written with capital letters (A to F) so they cannot be confused with the action symbol a.

The ADG has one vertex per action, V = \\a^i_k\\, and two kinds of edge.

### Type 1 edges: each robot's own order

The first kind of edge records the order in which each robot carries out its own plan, independently of every other robot.

E_1 = \\ (a^i_k, \\ a^i\_{k+1}) : 1 \le k \lt n_i \\

A robot does its actions in order. These edges form one chain per robot.

### Type 2 edges: handing a location over

The second kind of edge coordinates robots: it orders two actions of different robots that use the same location. The definition below is followed by its meaning in words, a worked example in the figure, and a table that checks the rule pair by pair.

E_2 = \\ (a^i_k, \\ a^j_l) : i \ne j, \\\\ s^i_k = g^j_l, \\\\ t^i_k \le t^j_l \\

Robot i's action a^i_k *leaves* location s^i_k. Robot j's action a^j_l *enters* the same location, later in the plan. The edge says that the leaving action must finish before the entering action may start: a robot moves into a location only after the previous robot has completely moved out.

![Building an action dependency graph](figures/85_adg_construction.svg)

**Construction on a small example.** (1) A map of six cells (garage nodes) A to F and three AGVs' timed plans: AGV-1 drives A → B → C, AGV-2 drives D → B → E, AGV-3 drives C → F. (2) How to read one vertex: a^1_2 is AGV-1's second action, from start cell B to goal cell C, planned to start at time 1. (3) Step through the construction: one vertex per action, then the Type 1 chains, then the two pairs that satisfy the Type 2 rule (the plan rows involved are outlined). (4) The last step shows three robots rotating around a triangle at the same instant: the rule then gives a cycle.

Checking the rule on [Figure 2](#ad-fig-85_adg_construction) by hand. Each action that leaves a location is compared with every other AGV's action that enters it:

| Leaves                             | Enters the same location | t condition      | Edge?                                                                |
|------------------------------------|--------------------------|------------------|----------------------------------------------------------------------|
| a^3_1: leaves `C` at 0             | a^1_2: enters `C` at 1   | 0 \le 1          | yes: a^3_1 \to a^1_2                                                 |
| a^1_2: leaves `B` at 1             | a^2_1: enters `B` at 2   | 1 \le 2          | yes: a^1_2 \to a^2_1                                                 |
| a^2_2: leaves `B` at 3             | a^1_1: enters `B` at 0   | 3 \le 0 is false | no: AGV-1 was in `B` first, and that order is already the edge above |
| a^1_1 leaves `A`; a^2_1 leaves `D` | nobody enters `A` or `D` | —                | no                                                                   |

The construction compares every pair of actions, so it takes O(\|V\|^2) time. Faster constructions skip pairs that cannot give an edge (see [section 6](#ad-beyond-the-basic-adg)).

### From a space-time table to an ADG: the algorithm

Multi-agent planners usually return a **space-time table**: one row per robot, one column per time step, and in each cell the location the robot occupies at that moment. Time is discrete. A robot that changes cell between columns t and t + 1 makes one move starting at t; a robot that stays put is waiting. The example of [Figure 3](#ad-fig-85_adg_construction) as a table:

| Robot | t = 0 | t = 1 | t = 2 | t = 3 | t = 4 | Actions extracted                    |
|-------|-------|-------|-------|-------|-------|--------------------------------------|
| AGV-1 | A     | B     | C     | C     | C     | a^1_1: A → B at 0; a^1_2: B → C at 1 |
| AGV-2 | D     | D     | D     | B     | E     | a^2_1: D → B at 2; a^2_2: B → E at 3 |
| AGV-3 | C     | F     | F     | F     | F     | a^3_1: C → F at 0                    |

The algorithm has five steps. Waits are not turned into actions: they never need to be dispatched, and the dependencies already make every real wait happen. Step 4 has two versions. The **pairwise** version is the rule exactly as written in [section 3.3](#ad-type-2-edges). The **sweep** version links only consecutive visitors of each cell and gives the same order with fewer edges.

``` text
input:  table[i][t] = cell occupied by robot i at time t,   t = 0 .. T
output: ADG G = (V, E), or "cycle" if the plan needs synchronous moves

1. Extract actions
   for each robot i:
     k = 0
     for t = 0 .. T-1:
       if table[i][t] != table[i][t+1]:            # a move; equal cells are a wait
         k = k + 1
         a[i][k] = (t, from = table[i][t], to = table[i][t+1])

2. Vertices: one per action                        V = { a[i][k] }

3. Type 1 edges
   for each robot i, for k = 1 .. n_i - 1:   add a[i][k] -> a[i][k+1]

4a. Type 2 edges, pairwise (Hönig et al.)          O(|V|^2)
   for each pair of actions (u of robot i, v of robot j), i != j:
     if u.from == v.to and u.t <= v.t:   add u -> v   # u leaves the cell v enters, no later than v starts

4b. Type 2 edges, sweep per cell                   O(|V| log |V|)
   for each robot, split its timeline into visits:
     visit = (cell, arrival time, entering action or none, leaving action or none)
   for each cell:
     sort its visits by arrival time
     for each consecutive pair (prev, next) of different robots:
       if prev never leaves or next never enters:  error "two robots stay in the cell"
       if prev.leave.t > next.enter.t:              error "robots overlap in the cell"
       add prev.leave -> next.enter

5. Topological sort; if it fails, the plan contains a cycle (synchronous moves)
```

**Why the sweep gives the same order.** Take three robots that pass through cell B in turn: visits v_1, v_2, v_3. The pairwise rule adds \mathrm{leave}(v_1) \to \mathrm{enter}(v_2), \mathrm{leave}(v_2) \to \mathrm{enter}(v_3) and \mathrm{leave}(v_1) \to \mathrm{enter}(v_3). The sweep adds only the first two. The third is implied:

\mathrm{leave}(v_1) \to \mathrm{enter}(v_2) \to \dots \to \mathrm{leave}(v_2) \to \mathrm{enter}(v_3)

The middle part is robot 2's own Type 1 chain, since it must enter B before it can leave. By induction, every pairwise edge is implied by consecutive hand-overs, so both versions have the same reachability. The two error checks also validate the plan: a correct space-time table never has two robots in one cell at once.

**The C++ version.** The file `examples/adg/space_time_to_adg.cpp` in this repository builds with nothing but C++20 and header-only Boost.Graph. C++20 is needed only for designated initializers (`Action {.robot = i, .index = k, ...}`), which name every field at the point of construction:

``` bash
g++ -std=c++20 -O2 -Wall -Wextra -o space_time_to_adg examples/adg/space_time_to_adg.cpp && ./space_time_to_adg
```

The graph type is the same shape as the scheduler's `DagBase`, with an `Action` bundle on each vertex and a `Dependency` bundle on each edge (the modern bundled-property style, the [Background](#doc-background) tab, [reading the type](#bg-reading-the-boost-adjacency-list-type)):

``` cpp
// examples/adg/space_time_to_adg.cpp (excerpt; the file also has Step 2, AddVertices, and a demo main)
using Cell = std::string;
using SpaceTimeTable = std::vector<std::vector<Cell>>;  // [robot][t] -> cell

struct Action {                 // vertex payload: a^i_k in the text
  int robot = 0;                // i
  int index = 0;                // k, counting from 1 in the robot's plan
  int start_time = 0;           // t^i_k: the move starts at t and arrives at t + 1
  Cell from;                    // s^i_k
  Cell to;                      // g^i_k
};

enum class EdgeType { kType1, kType2 };
struct Dependency {             // edge payload
  EdgeType type = EdgeType::kType1;
};

// vecS/vecS: vertices and out-edge lists in std::vector, so a Vertex is a std::size_t index.
// bidirectionalS: keep in-edges too, so in_degree()/in_edges() are cheap (predecessors = parents).
using Adg = boost::adjacency_list<boost::vecS, boost::vecS, boost::bidirectionalS, Action, Dependency>;
using Vertex = Adg::vertex_descriptor;

std::vector<std::vector<Action>> ExtractActions(const SpaceTimeTable& table) {
  std::vector<std::vector<Action>> actions(table.size());
  for(int i = 0; i < static_cast<int>(table.size()); ++i) {
    const auto& row = table[i];
    for(int t = 0; t + 1 < static_cast<int>(row.size()); ++t) {
      if(row[t] != row[t + 1]) {
        actions[i].push_back(Action {
            .robot = i,
            .index = static_cast<int>(actions[i].size()) + 1,
            .start_time = t,
            .from = row[t],
            .to = row[t + 1],
        });
      }
    }
  }
  return actions;
}

// Step 3: Type 1 edges, a^i_k -> a^i_{k+1}.
void AddType1Edges(Adg& g, const std::vector<std::vector<Vertex>>& ids) {
  for(const auto& chain : ids) {
    for(std::size_t k = 0; k + 1 < chain.size(); ++k) {
      boost::add_edge(chain[k], chain[k + 1], Dependency {.type = EdgeType::kType1}, g);
    }
  }
}

// Step 4a: Type 2 edges by the pairwise rule:
//   a^i_k -> a^j_l  if  i != j,  s^i_k == g^j_l,  t^i_k <= t^j_l
void AddType2EdgesPairwise(Adg& g) {
  const auto [first, last] = boost::vertices(g);
  for(auto u = first; u != last; ++u) {
    for(auto v = first; v != last; ++v) {
      const Action& leave = g[*u];
      const Action& enter = g[*v];
      if(leave.robot != enter.robot && leave.from == enter.to && leave.start_time <= enter.start_time) {
        boost::add_edge(*u, *v, Dependency {.type = EdgeType::kType2}, g);
      }
    }
  }
}

// Step 4b: Type 2 edges by a sweep per cell. A "visit" is one stay of one robot in one cell: it begins with
// the action that enters the cell (none for the robot's start cell) and ends with the action that leaves it
// (none if the robot never leaves). Sorted by arrival time, each visit must end before the next one by a
// different robot begins; that hand-over is exactly one Type 2 edge. Edges to later visitors are implied
// through the next visitor's own Type 1 chain, so they are not needed.
struct Visit {
  int arrival = -1;                   // -1: the robot starts here
  int robot = 0;
  std::optional<Vertex> enter;        // the action whose goal is this cell
  std::optional<Vertex> leave;        // the action whose start is this cell
};

void AddType2EdgesSweep(Adg& g, const SpaceTimeTable& table, const std::vector<std::vector<Vertex>>& ids) {
  std::map<Cell, std::vector<Visit>> visits;
  for(int i = 0; i < static_cast<int>(ids.size()); ++i) {
    Visit current {.arrival = -1, .robot = i, .enter = std::nullopt, .leave = std::nullopt};
    Cell here = table[i].front();
    for(Vertex v : ids[i]) {
      current.leave = v;                                   // this action leaves `here`
      visits[here].push_back(current);
      here = g[v].to;
      current = Visit {.arrival = g[v].start_time + 1, .robot = i, .enter = v, .leave = std::nullopt};  // goal at t+1
    }
    visits[here].push_back(current);                       // the last stay never ends
  }
  for(auto& [cell, list] : visits) {
    std::sort(list.begin(), list.end(), [](const Visit& a, const Visit& b) {
      return std::tie(a.arrival, a.robot) < std::tie(b.arrival, b.robot);
    });
    for(std::size_t n = 0; n + 1 < list.size(); ++n) {
      const Visit& prev = list[n];
      const Visit& next = list[n + 1];
      if(prev.robot == next.robot) {
        continue;                                          // ordered by that robot's Type 1 chain
      }
      if(!prev.leave || !next.enter) {
        throw std::runtime_error("invalid plan: two robots occupy cell " + cell + " for good");
      }
      if(g[*prev.leave].start_time > g[*next.enter].start_time) {
        throw std::runtime_error("invalid plan: robots overlap in cell " + cell);
      }
      boost::add_edge(*prev.leave, *next.enter, Dependency {.type = EdgeType::kType2}, g);
    }
  }
}

// Step 5: an ADG must be acyclic. boost::topological_sort throws boost::not_a_dag on a cycle; it writes
// vertices in reverse topological order, so reverse the result.
std::vector<Vertex> TopologicalOrder(const Adg& g) {
  std::vector<Vertex> order;
  boost::topological_sort(g, std::back_inserter(order));
  std::reverse(order.begin(), order.end());
  return order;
}
```

Its output for the example, plus a corridor that three robots cross in turn and the three-robot rotation:

``` text
Pairwise rule: 5 vertices, 4 edges
  Type 1  a1.1 (A->B @0)  ->  a1.2 (B->C @1)
  Type 1  a2.1 (D->B @2)  ->  a2.2 (B->E @3)
  Type 2  a1.2 (B->C @1)  ->  a2.1 (D->B @2)
  Type 2  a3.1 (C->F @0)  ->  a1.2 (B->C @1)
Sweep: 5 vertices, 4 edges
  Type 1  a1.1 (A->B @0)  ->  a1.2 (B->C @1)
  Type 1  a2.1 (D->B @2)  ->  a2.2 (B->E @3)
  Type 2  a1.2 (B->C @1)  ->  a2.1 (D->B @2)
  Type 2  a3.1 (C->F @0)  ->  a1.2 (B->C @1)
Same order (same reachability): true
One topological order:  a3.1 (C->F @0)  a1.1 (A->B @0)  a1.2 (B->C @1)  a2.1 (D->B @2)  a2.2 (B->E @3)
Depth levels (each level can run in parallel):
  level 0:  a1.1 (A->B @0)  a3.1 (C->F @0)
  level 1:  a1.2 (B->C @1)
  level 2:  a2.1 (D->B @2)
  level 3:  a2.2 (B->E @3)
Corridor, pairwise rule: 6 vertices, 6 edges
  Type 1  a1.1 (A->B @0)  ->  a1.2 (B->C @1)
  Type 1  a2.1 (D->B @1)  ->  a2.2 (B->E @2)
  Type 1  a3.1 (F->B @2)  ->  a3.2 (B->G @3)
  Type 2  a1.2 (B->C @1)  ->  a2.1 (D->B @1)
  Type 2  a1.2 (B->C @1)  ->  a3.1 (F->B @2)
  Type 2  a2.2 (B->E @2)  ->  a3.1 (F->B @2)
Corridor, sweep: 6 vertices, 5 edges
  Type 1  a1.1 (A->B @0)  ->  a1.2 (B->C @1)
  Type 1  a2.1 (D->B @1)  ->  a2.2 (B->E @2)
  Type 1  a3.1 (F->B @2)  ->  a3.2 (B->G @3)
  Type 2  a1.2 (B->C @1)  ->  a2.1 (D->B @1)
  Type 2  a2.2 (B->E @2)  ->  a3.1 (F->B @2)
Same order (same reachability): true
Rotation: not a DAG (the plan needs synchronous moves)
```

Four things to notice in the output:

- For the example, both rules give the same four edges: each cell there has at most two visitors.
- For the corridor, the pairwise rule adds a^1_2 \to a^3_1, which the sweep omits. The reachability check confirms the orders are identical.
- The depth levels show the parallelism directly: level 0 holds a^1_1 and a^3_1.
- The rotation fails the topological sort.

**How this maps to the scheduler.** `BuildActionDagFromMotions` ([section 7.2](#ad-how-the-action-dag-is-built)) is the pairwise rule, generalised in three ways:

- Its input is CHUGG's continuous-time motions rather than a table.
- The visits are kept in a `GarageOccupancyChecker` keyed by pose and by motion-graph edge, not by cell.
- "Same cell" becomes "conflicting footprints", via the collision table.

Because occupancy is never cleared, every earlier occupant becomes a predecessor, as in step 4a, and `Reduce()` removes the implied edges afterwards. A sweep version would add fewer edges and make `Reduce()` cheaper. It is harder there, though, because a footprint conflicts with a *set* of locations, so "the previous visitor" has to be tracked per conflict set rather than per cell.

### Cycles mean "only with perfect timing"

Suppose three robots rotate around a triangle at the same instant: \mathrm{X} \to \mathrm{Y}, \mathrm{Y} \to \mathrm{Z}, \mathrm{Z} \to \mathrm{X}, all at t = 0. Each action leaves a location another one enters at the same time, and t \le t holds, so the rule adds three edges that form a cycle. Each robot waits for another to leave. The plan is only safe if all three move in perfect lockstep, which real robots cannot guarantee. Hönig et al. call such transitions unsafe, and point out that they show up as cycles in the ADG. A planner whose output must run on an ADG must therefore avoid them. In the scheduler, a cycle in the action DAG makes `GetTopologicalOrdering()` fail, and the response reports "Failed to get final ordering for action DAG!".

## Executing an ADG

An ADG states which actions must precede which, but not when each action is sent to its robot. This section gives the rule a dispatcher uses to release actions, shows why that rule keeps robots apart and always finishes, and derives the timing quantities (earliest start, critical path and slack) and the parallelism that the graph implies.

### Statuses and the dispatch rule

Each vertex has a status: **staged** (not yet sent), **enqueued** (sent to the robot's command queue) or **finished** (the robot reported completion). Hönig et al. enqueue an action a^j_l when two conditions hold:

\underbrace{\mathrm{status}(a^j\_{l-1}) \in \\\text{enqueued}, \text{finished}\\}\_{\text{Type 1 predecessor}} \\\\\wedge\\\\ \underbrace{\forall\\ u \in \mathrm{pred}\_2(a^j_l):\\ \mathrm{status}(u) = \text{finished}}\_{\text{Type 2 predecessors}}

![Executing an ADG: statuses over time](figures/88_adg_statuses.svg)

**Executing the example ADG.** Top: the three statuses and who moves an action between them. The dispatcher sends a staged action when the enqueue rule holds, and the robot marks it finished when it reports completion. The closest `ActionNode` status values are shown under each. Below: step through five moments while the example of [Figure 2](#ad-fig-85_adg_construction) runs, with the colour of every vertex and each robot's command queue.

Walking through [Figure 3](#ad-fig-88_adg_statuses) shows why the rule has two parts.

- **Type 2 waits for *finished*.** At the start, a^1_2 (AGV-1 drives into C) is held back because AGV-3, which must first leave C, has not reported.
- **Type 1 only waits for *enqueued*.** As soon as a^3_1 is reported, a^1_2 is sent even though AGV-1 is still busy with a^1_1. The robot holds it in its queue and starts it the moment the first move ends, with no round trip to the dispatcher.
- **Each report can release several actions.** When AGV-1 reports a^1_2, both of AGV-2's actions are released: a^2_1 because its Type 2 predecessor is now finished, and a^2_2 because its only predecessor, a^2_1, is now enqueued.

Here a^j\_{l-1} is the same robot's previous action (its Type 1 predecessor), and \mathrm{pred}\_2(a^j_l) is the set of actions with a Type 2 edge into a^j_l. The Type 1 predecessor only needs to be *enqueued*, because the robot executes its own queue in order. Sending the next action early lets it start without a round trip to the dispatcher. Type 2 predecessors belong to other robots, so they must be *finished*. A vertex becomes finished when its robot reports it.

Some later work uses a single rule instead: an action may start once all its predecessors are finished. Berndt et al. (2020) use the statuses *staged*, *in progress* and *completed*. The two rules give the same safety guarantee.

### Why it is safe

The argument needs four assumptions, all from Hönig et al.: robots stay on their planned paths, every started action eventually finishes, robots report completion promptly, and the plan itself was collision-free.

**Claim.** Two robots are never in the same location at the same time during execution.

**Sketch.** Take a location x and list, in the plan's time order, the actions that enter it. For each pair of consecutive visitors i then j:

- robot i leaves x with some action a^i_k;
- robot j enters it with a^j_l, and t^i_k \le t^j_l, because the plan was collision-free.

So (a^i_k, a^j_l) \in E_2. Robot j cannot start entering until robot i has finished leaving, whatever the delays. Hönig's rule also adds edges from *earlier* visitors to later ones, but those are implied: they follow from chains of these consecutive hand-overs and Type 1 edges.

### Why it finishes

**Claim.** If the ADG is acyclic and every enqueued action eventually finishes, every action eventually finishes.

**Proof.** Suppose some actions never finish, and let U be the set of them. U is a finite set of vertices of a DAG, so it has a minimal element v: one with no predecessor in U (walking predecessors backwards inside U must stop, otherwise it would repeat a vertex and form a cycle). Every predecessor of v is therefore finished. So v's enqueue condition holds, v is enqueued, and by assumption it finishes. That contradicts v \in U, so U is empty. \blacksquare

With a cycle, the minimal element need not exist, and the robots on the cycle wait for each other forever: a deadlock.

### Timing: earliest start, critical path and slack

The ADG drops the planned times, but timing can be recomputed from it. Give each action a duration d(v). If the dispatcher starts every action as soon as it is allowed, then:

S(v) = \max\_{u \in \mathrm{pred}(v)} C(u) \quad (\text{or } 0 \text{ if } v \text{ has no predecessor}), \qquad C(v) = S(v) + d(v)

Here S(v) is the start time and C(v) the completion time. Evaluating the recurrence in any topological order gives every value in O(\|V\| + \|E\|). The **makespan**, \max_v C(v), equals the weight of the longest path, counting each vertex's duration. That path is the **critical path**.

Running the recurrence backwards from the makespan gives the latest finish L(v) that does not delay the end:

L(v) = \min\_{w \in \mathrm{succ}(v)} \big( L(w) - d(w) \big) \quad (\text{or the makespan if } v \text{ has no successor}), \qquad \mathrm{slack}(v) = L(v) - C(v)

![Earliest start, critical path and slack](figures/86_adg_critical_path.svg)

**Timing on the example ADG.** The durations are invented. The recurrence gives S and C for every action and a makespan of 10. The critical path a^1_1 \to a^1_2 \to a^2_1 \to a^2_2 has no slack. a^3_1 has a slack of 1: it can run up to 1 s late without moving the end.

What this says about delays:

- A delay of \delta on action u can only affect actions reachable from it (u \rightsquigarrow v), and it delays each of them by at most \delta.
- The makespan grows by \max(0, \delta - \mathrm{slack}(u)).

Delays on critical actions hurt one-for-one. Delays on actions with slack are absorbed up to the slack. Unordered actions never affect each other.

**Two things the ADG cannot do.** It cannot make a schedule faster than its order allows: if the order the planner chose was poor, the ADG keeps it. That is what switchable ADGs address ([section 5](#ad-beyond-the-basic-adg)). And it does not recover from a robot leaving its path or failing outright; that needs a replan.

### Where the parallelism comes from

Robots move in parallel only where the graph branches, at several roots or at a vertex with several children. If the graph is one chain, one root and one child after another down to a single leaf, every action waits for the one before it and nothing runs at the same time. Two refinements make this precise.

**The rule.** Two actions can be in progress at the same time only if they are *unordered* (u \parallel v, [section 2.2](#ad-dags-are-partial-orders)). If u \prec v, there is a path u \to x_1 \to \dots \to v, and every edge on it forces "finish before start". A Type 1 edge allows the next action to be *queued* early, but the robot still runs its queue one action at a time. So v starts after u has finished, whatever the delays. Unordered actions *may* overlap; whether they do depends on durations and delays.

**Refinement 1: judge the reduced graph, not the edges as built.** All actions are mutually ordered (a *total order*, a strict sequence) exactly when the transitive reduction is a single path. A vertex with two children is not enough to give parallelism if one child reaches the other: in panel 4 of [Figure 5](#ad-fig-89_adg_parallelism), a has edges to b and to c, but a \to c is implied by a \to b \to c. The scheduler's builder adds many such implied edges on purpose ([section 7.2](#ad-how-the-action-dag-is-built)), so look at the schedule *after* `Reduce()`.

**Refinement 2: branches can start anywhere.** Several roots is one way to start parallel work: branches that begin at time 0. A fork at any vertex (out-degree 2 or more in the reduced graph) starts parallel branches later, and a join (in-degree 2 or more) ends them. Panel 2 has one root and one leaf, but its middle runs in parallel. Put together: the reduced ADG allows parallelism exactly when it is not a single path, that is, when it has two or more roots, or some vertex with two or more parents or children.

![Where parallelism comes from](figures/89_adg_parallelism.svg)

**Shape decides parallelism.** (1) One chain over two AGVs: they take turns, the span equals the total work, width 1. (2) One root and one leaf, but a fork and a join: p and q run at the same time. (3) Two independent chains (two roots, no shared space): the AGVs never wait for each other. (4) a appears to have two children, but the extra edge is implied, so the graph is a chain. Each panel shows the earliest-start schedule, the work W, the span L, their ratio and the width.

**How much parallelism.** Three numbers describe it:

- **Work** W = \sum_v d(v): the total time of all actions.
- **Span** L: the length of the critical path, which is the earliest-start makespan ([section 4.4](#ad-timing-critical-path-and-slack)). Always L \le W, with equality exactly for a chain: in a chain the makespan is the sum of all durations.
- **Width** \omega: the largest number of pairwise unordered actions, an upper bound on how many can be in progress at once. By Dilworth's theorem, \omega is also the smallest number of chains that cover all the vertices.

The ratio W / L is the average parallelism. It is 1 for a chain and grows with the number of actions that genuinely overlap. One bound follows directly from Type 1 edges: each robot's actions form a chain, so those chains cover the graph, and \omega \le the number of robots. An ADG never asks one robot to do two things at once. For the example of [Figure 4](#ad-fig-86_adg_critical_path), W = 12, L = 10 and \omega = 2. The only overlap is at the start, where a^1_1 and a^3_1 run together; everything after that is a chain through cell B and cell C.

**What a chain still gives you.** Even with no parallelism, the ADG keeps execution safe under delays: each action waits for its predecessor's completion instead of a clock. A long chain across several robots usually means the plan itself is sequential, for example every route passes one narrow aisle, one VRC or one bay. The ADG does not add parallelism the plan does not have; it only stops the clock from destroying the parallelism that is there.

**In the scheduler.** Parallel actions in `Schedule.nodes` come from AGVs, bays and VRCs whose motions neither overlap in footprint nor are linked through the event DAG. Things that serialise them:

- **Shared space.** Every pair of actions with conflicting footprints is ordered, however far apart in time. That is required for safety, not a flaw.
- **Event-level edges.** Each event-DAG edge orders *all* of one event's actions before *all* of the next one's. Edges added for CHUGG's benefit (`AddNodeArrivalDeps`, `EnsureAgvMovePathsClear`) therefore also serialise execution.
- **The VECS chain quirk.** All VECS commands are chained into one sequence ([section 7.3](#ad-our-edges-versus-type-1-and-type-2)).
- **The committed schedule.** Actions in `base_schedule` keep running in parallel with the new plan, but their AGVs and nodes are excluded from it ([section 7.5](#ad-persistent-planning-base-schedule-and-the-split)).

**Measuring it.** These numbers are cheap to compute from every `PlanResponse`, and worth recording next to the timing benchmarks in the [Verification](#doc-verification) tab:

- W is the sum of `duration`.
- L comes from the recurrence over `parents`, in array order, since the array is topological.
- \omega comes from Dilworth's theorem: \omega = \|V\| - \|M\|, where M is a maximum matching in the bipartite graph with an edge (u, v) for every u \prec v. That is a few milliseconds for a few hundred actions.

A refactor that leaves assignments unchanged should leave all three unchanged. A solver change that improves W / L is one that genuinely lets more robots move at once.

## Beyond the basic ADG

The ADG described so far has been extended in several directions since it was introduced. The list below summarises the main variants and notes the scheduler's closest counterpart where one exists.

- **Temporal plan graph** (Hönig, Kumar, Cohen, Ma, Xu, Ayanian and Koenig, ICAPS 2016). The same two edge types, used to post-process a multi-agent path-finding (MAPF) plan into one that respects velocity limits and safety distances. The ADG is its execution-time use.
- **Persistent execution** (Hönig et al., 2019). New plans are appended to a running ADG, so a warehouse can keep planning while robots move. The scheduler's `base_schedule` plays a similar role ([section 7.4](#ad-persistent-planning-base-schedule-and-the-split)).
- **Switchable ADG** (Berndt, van Duijkeren, Palmieri and Keviczky, 2020; receding-horizon version 2023). Each Type 2 dependency between two robots that have not yet started either action may be *reversed*, letting the other robot go first. A mixed-integer linear program chooses the direction of every switchable pair to minimise the sum of the robots' completion times, given the delays observed so far.
- **Streamlined construction** (Dunkel, 2024). Wait actions can be dropped from the ADG without affecting correctness, which the scheduler already does. Type 2 edges can be built in O(n \log n) by skipping pairs that cannot produce a non-redundant edge.
- **Planning in order space** (Wu, Veerapaneni, Li and Likhachev, 2024). A variant of conflict-based search that outputs a temporal plan graph directly instead of a timed plan.

## The action DAG in the scheduler

Of the two DAGs in the pipeline ([section 1](#bg-motion-planning-and-the-response)), only the action DAG is an ADG. `ResponseFromTrajectories(ctx, final_state)` builds it, as stage 5 of the pipeline, from the `ContinuousState` CHUGG returns ([section 4](#bg-continuousstate-the-timeline)).

### Two DAGs, two jobs

The scheduler's pipeline holds two DAGs, both built on `DagBase`, and only one of them is an ADG. The table compares the event DAG and the action DAG row by row: what a vertex is, what an edge means, which times each carries, and which stage builds and consumes each graph.

|               | Event DAG                                                                                          | Action DAG (the ADG)                                                                      |
|---------------|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| Type          | `ScheduleEventDag` (`DagBase<ScheduleEvent>`), in `ctx->events`                                    | `DagBase<ActionNodeMsg>`, local `final_actions_dag`; sent as `Schedule.nodes`             |
| A vertex is   | A planner event: `AgvMove`, `TrayMove`, `BayTransition`, …                                         | One command to one entity: an AGV move, lift or lower; a bay, VECS or VRC command         |
| An edge means | "this event must be planned after that one" (job logic and assignment)                             | "this command may start only after that one has finished" (physical safety and job logic) |
| Times         | None                                                                                               | Derived from CHUGG's trajectories, then dropped; only `ActionNode.duration` is kept       |
| Built by      | Job expansion, tray assignment, AGV assignment ([section 13.6](#bg-how-the-dag-grows-during-plan)) | `ResponseFromTrajectories`, after motion planning                                         |
| Consumed by   | CHUGG, as the order to plan in                                                                     | The dispatcher, as the order to execute in                                                |

### How the action DAG is built

`ResponseFromTrajectories` turns CHUGG's timed trajectories into the action DAG through a fixed sequence of calls. The abridged code shows that sequence; the numbered list after it explains each step and identifies which of the scheduler's edges correspond to Type 1 and Type 2 edges.

``` cpp
// src/scheduler.cpp — Scheduler::ResponseFromTrajectories (abridged)
std::set<Motion, MotionScheduleOrder> all_motions;              // by start time, then event, then hash
CollectAndCollapseTrajectoryMotions(final_state, *layout_, all_motions);  // drop waits, merge floor runs
volley::DagBase<ActionNodeMsg> final_actions_dag;
volley::GarageOccupancyChecker<std::shared_ptr<ActionNodeMsg>> freeing_moves(table_, gg_);
BuildActionDagFromMotions(all_motions, ctx, final_actions_dag, freeing_moves, event_start_end, logger_);
final_actions_dag.Reduce();
TransferEventDagDepsToActionDag(ctx, event_start_end, final_actions_dag, logger_);
final_actions_dag.Reduce();
InsertVrcActionsIntoDag(final_actions_dag, *layout_, ctx->initial_state, cost_model_);
final_actions_dag.Reduce();
auto final_ordering = final_actions_dag.GetTopologicalOrdering();   // fails if there is a cycle
return BuildScheduledActionsArray(ctx, final_actions_dag, *final_ordering);
```

1.  **Collect motions.** Every entity's trajectory is merged into one set, ordered by start time (`MotionScheduleOrder`: start time, then the event's vertex, then a hash as a tie-break). Waits are dropped, and runs of consecutive floor-traversal motions are merged into one.
2.  **One vertex per motion.** `ToActionNode` turns each motion into an `ActionNodeMsg` with a fresh GUID and the job's id. `event_start_end` records the first and last action of each event.
3.  **Same-entity chain.** Each action depends on the previous action of the same entity (`last_entity_action`). This is Type 1.
4.  **Occupancy edges.** Before adding an action, `freeing_moves.GetBlockers(location, footprint, lifted)` returns every *earlier* action whose recorded occupancy conflicts with this action's location and footprint, and each one becomes a predecessor. Then the action is recorded as an occupant of every location its footprint conflicts with (`AddOccupant`). This is the scheduler's Type 2.
5.  **Reduce**, because the occupancy rule adds many implied edges (the code comment says "overkill but pruned later by Reduce()").
6.  **Event-level edges.** For every edge e \to e' of the event DAG, the last action of e must finish before the first action of e' starts. These carry job logic that geometry cannot see, such as "the tray must be at the bay before the bay processes the retrieve".
7.  **Reduce, insert VRC commands, reduce again.** `InsertVrcActionsIntoDag` adds VRC moves where an AGV needs the carriage on another floor ([section 6.3](#bg-vrcs-lifts-between-floors)).
8.  **Serialise.** Take a topological order. Each action's predecessors become indices into the output array (`parents`), and each job records the indices of its actions (`node_indices`). `BuildScheduledActionsArray` also re-adds the edge from the entity's previous action if `Reduce()` removed it. That edge is implied, so it does not change the order, but it makes every entity's chain explicit for the dispatcher.

![Motions to actions](figures/32_motions_to_actions.svg)

From timed trajectories to `ActionNode[]`, steps 1–8 above, on the shape of the `RetrieveJob` test. Every motion with a delta becomes one action; waits are dropped. Times are illustrative.

Step 2 in detail: `ToActionNode` decides what command each motion becomes, from the type of its delta:

``` cpp
// Where: anonymous-namespace helper ToActionNode(const volley::Motion& motion, GuidMsg job_id,
//        const std::shared_ptr<ScheduleEvent>& event) in src/scheduler.cpp
//   motion.GetDelta() -> optional serialized discrete change; its .type names the ROS message type
if(delta->type == "AgvPoseChanged") {
  result->type = ActionNodeMsg::TYPE_AGV_COMMAND;
  // An AGV motion whose collision id is NOT the bare AGV is carrying a tray, so lift = true on both ends.
  result->agv_command.src.lift = motion.GetCollisionId() != common::EnumInteger(volley::CollisionEntityId::AGV);
}
// "AgvLiftChanged" -> AGV command with src.lift != dst.lift; "BayStateChanged" -> TYPE_BAY_COMMAND using the
// BayTransition's own command; "VecsStateChanged" -> start/stop charging; "VrcStateChanged" -> VRC move.
```

![The action DAG the scheduler builds](figures/87_adg_in_scheduler.svg)

**An illustrative retrieve, end to end.** (1) The event DAG. (2) CHUGG's motions per entity. (3) The action DAG. Same-entity edges chain AGV-1's five actions. The occupancy edge `b1 → a3` exists because AGV-2's move swept W2, which AGV-1 enters later. The event edge `e1 → e3` becomes `a5 → c1`. The occupancy edge `a1 → a3` is implied by AGV-1's own chain and is removed by `Reduce()`. (4) The serialised `Schedule.nodes`, in one topological order, with parents as indices.

### The construction, step by step

The figure below runs `ResponseFromTrajectories` on a small retrieve in the Pecos layout and shows every data structure it touches. AGV-2 first leaves W22; AGV-1 lifts the car's tray T23 at P23, carries it through W22 and W41 into bay B21 and lowers it; then the bay hands the car over.

![Building the action DAG, motion by motion](figures/126_action_dag_construction.svg)

**Building the action DAG, motion by motion.** Step through it: the motions are sorted and the wait is dropped; each motion becomes an action that is chained to its entity's previous action, depends on every earlier occupant of the space it needs, and then occupies that space; `Reduce()` removes the implied edge; the event edge from the lower to the hand-over is transferred; and one topological order is written out as `Schedule.nodes` with parent indices.

Five data structures carry the construction. Each has one job:

| Data structure       | Type                                                          | Role                                                                                                                                                                                                                                                                                      |
|----------------------|---------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `all_motions`        | `std::set<Motion, MotionScheduleOrder>`                       | Every non-wait motion of every entity, in the order actions are created: planned start time, then the event vertex (a motion's action id), then a hash so that distinct motions never compare equal                                                                                       |
| `last_entity_action` | `unordered_map<GarageEntityIdMsg, shared_ptr<ActionNodeMsg>>` | The latest action of each AGV, bay, VECS or VRC; the source of the same-entity edge                                                                                                                                                                                                       |
| `freeing_moves`      | `GarageOccupancyChecker<shared_ptr<ActionNodeMsg>>`           | For each location (pose or edge of the motion graph), which actions occupy it and which footprint types they block. `GetBlockers` reads it, `AddOccupant` writes it through the `CollisionTable`. Nothing is ever removed, so “occupant” means “has used this space at some earlier time” |
| `event_start_end`    | `unordered_map<size_t, pair<ActionNode, ActionNode>>`         | For each event, its first and last action; used to turn event edges into action edges                                                                                                                                                                                                     |
| `final_actions_dag`  | `DagBase<ActionNodeMsg>`                                      | The action DAG itself: shared action nodes as vertices, dependencies as edges, with `Reduce()` and `GetTopologicalOrdering()`                                                                                                                                                             |

The loop body is short. For each motion in order, `ToActionNode` creates the action with a fresh guid and the job's id, and `event_start_end` records it as the first action of its event if the event has none yet, and as its last action in any case. The action then gets an edge from `last_entity_action[entity]`, which keeps each machine's commands in order. Next, `GetBlockers(location, collision_id, lifted)` returns every earlier action that occupies a location conflicting with this motion's footprint, and each becomes a predecessor. In the example that is how the hand-over of W22 from AGV-2 to AGV-1 appears: a0 → a2. Finally `AddOccupant` records the new action on every location its footprint conflicts with. `lifted` is true for every motion whose collision id is not the bare AGV, because a tray or car can only move on a lifted AGV. A tray standing on the ground is checked against an AGV through its legs only, so an empty AGV can still pass under it.

Because occupancy is never cleared, a motion depends on *every* earlier user of its space, not just the last one. W22 is blocked for a3 by both a0 and a2. The first `Reduce()` removes the edges that such chains imply (a0 → a3 here). Geometry cannot express some orders, though: the bay's hand-over never shares space with the car's arrival in a way the code checks (bay transitions carry a TODO in this loop). `TransferEventDagDepsToActionDag` therefore adds, for every event edge e \to e', an edge from the last action of e to the first action of e', which gives a5 → a6. A second `Reduce()` follows, then VRC insertion (nothing to insert in Pecos) and a third `Reduce()`. `BuildScheduledActionsArray` takes one topological order and writes each action's in-edges as indices of earlier array entries. It re-adds the edge from the same entity's previous action if `Reduce()` removed it, and appends each action's index to its job's `node_indices`.

### VRC commands: lifts between floors

VRC commands are not planned by CHUGG; they are added to the action DAG after motion planning, in step 7 of the construction above. The figure shows the concept on two floors, and the paragraph after it describes how `InsertVrcActionsIntoDag` decides where to insert them.

![VRC conceptual transfer](figures/14_vrc_floors.svg)

Conceptual VRC connecting two floors, as a side elevation. The Pecos YAML has no VRC; this shows general code-supported behaviour.

VRCs are handled at the **action** level, after motion planning (step 7 above): `InsertVrcActionsIntoDag` (in `utils.cpp`) walks AGV actions in topological order, simulates the carriage floor per VRC, and inserts a `TYPE_VRC_COMMAND` *approach* when the carriage is on the wrong floor for the AGV's next action, plus a *move* command that replaces each cross-floor AGV action. Each command's duration is door close + carriage transit + door open. Consecutive cross-floor motions are first collapsed into one motion in `CollectAndCollapseTrajectoryMotions`. `VrcTransition` (in `planner_core`, [section 11](#bg-event-types-and-polymorphism)) exists, but the scheduler never creates one, and CHUGG's planning loop has no branch for it ([section 21.1](#bg-inside-solvesequential)).

### Our edges versus Type 1 and Type 2

Let M be the set of non-wait motions, and m \lt_t m' the `MotionScheduleOrder` (planned start time first). With \mathrm{ent}(m) the entity, \mathrm{loc}(m) its location (a pose, or an edge of the motion graph for a move), \mathrm{fp}(m) its footprint type and \mathrm{ev}(m) its event, the builder adds:

E\_{\text{entity}} = \\ (m, m') : \mathrm{ent}(m) = \mathrm{ent}(m'),\\ m' \text{ is the next motion of that entity after } m \\

E\_{\text{occ}} = \\ (m, m') : m \lt_t m',\\ \mathrm{conflict}\big(\mathrm{loc}(m), \mathrm{fp}(m);\\ \mathrm{loc}(m'), \mathrm{fp}(m')\big) \\

E\_{\text{event}} = \\ (\mathrm{last}(e), \mathrm{first}(e')) : (e, e') \text{ an edge of the event DAG} \\

The result is the transitive reduction of E\_{\text{entity}} \cup E\_{\text{occ}} \cup E\_{\text{event}}, plus the VRC commands. Here \mathrm{conflict} is what the `CollisionTable` says about two footprints at two locations, with one special case: a tray standing on the ground conflicts with an AGV only through its legs (`TRAY_LEGS`), so an empty AGV can drive under it. Compared with the textbook rule:

| Textbook ADG                              | The scheduler                                                     | Why it differs                                                                                                                                                                                                                                        |
|-------------------------------------------|-------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Type 1: consecutive actions of a robot    | E\_{\text{entity}}: consecutive actions of an AGV, a bay or a VRC | Bays, VECS and VRCs are agents too. One quirk: `BuildScheduledActionsArray` keys its extra chain by AGV, bay or VRC id, and gives every VECS command the same empty key, so each VECS command is chained after the previous one, whichever VECS it is |
| Type 2: s^i_k = g^j_l, the same grid cell | E\_{\text{occ}}: footprint conflict at poses *and* along moves    | AGVs and trays are rectangles of different sizes, and a move sweeps an area. Equal locations are not enough to detect a conflict                                                                                                                      |
| Only between different robots             | Any earlier occupant, the same entity included                    | Simpler; the same-entity edges are implied by the chain, and `Reduce()` removes them                                                                                                                                                                  |
| From the action that *leaves* a location  | From *every* earlier action that occupied a conflicting location  | Occupancy is never cleared, so the rule is conservative. The extra edges are implied by the chain of hand-overs, and `Reduce()` removes them                                                                                                          |
| No task-level edges                       | E\_{\text{event}} from the event DAG                              | Some orders are logical, not geometric. A bay must not start a retrieve before the tray arrives, even though they never share space                                                                                                                   |
| Wait actions are vertices                 | Waits are dropped                                                 | As in Dunkel's streamlined ADG: a wait only delays, and dependencies already enforce every real wait                                                                                                                                                  |

One consequence to keep in mind: the occupancy rule relates motions by *planned start time*, exactly as Hönig's t^i_k \le t^j_l does. If two conflicting motions have the same start time, the tie-break (the event's vertex, then a hash) decides which goes first. CHUGG should never produce such a pair, since it would mean the plan itself overlaps.

### What goes over the wire

`Schedule.msg` says it directly: "A schedule is a DAG. Nodes are provided in a topological order." Each `ActionNodeMsg` carries the ADG's data:

| ADG concept               | `ActionNodeMsg` field                                                  | Notes                                                                                                                                                       |
|---------------------------|------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Vertex identity           | `guid`                                                                 | Fresh per plan call (`CreateActionGuid`); VECS and VRC command ids are set from it                                                                          |
| Incoming edges            | `parents`: indices into `Schedule.nodes`                               | Because the array is in topological order, every parent index is smaller than the node's own index: an invariant worth a test                               |
| Which robot, which action | `type` plus `agv_id`/`agv_command`, `bay_id`/`bay_command`, …          | One of four command kinds                                                                                                                                   |
| d(v)                      | `duration` (seconds)                                                   | Enough to recompute S, C and the critical path ([section 4.4](#ad-timing-critical-path-and-slack))                                                          |
| Status                    | `status`: `STATUS_NOT_RECEIVED`, `STATUS_RECEIVED`, `STATUS_COMPLETED` | Close to staged, enqueued and finished. The comments define them as "not acknowledged as received by the entity", "acknowledged as received" and "complete" |
| Task grouping             | `job_id`; `ScheduledJobData.node_indices`                              | Which job each action serves                                                                                                                                |

After the response is built, `Plan()` marks every planned job `STATE_EXECUTING`, and for `TYPE_RETRIEVE` jobs records the bay and the `PROCESS_RETRIEVE` action in `bay_id` and `bay_arrival_node_guid`.

The dispatcher, which executes this graph, is not in the snapshots, so its exact enqueue rule cannot be confirmed here. The questions to ask its owners are: does it send an action when its parents are `COMPLETED`, or when the same-entity parent is only `RECEIVED` (Hönig's rule)? And how does it treat an entity whose command is rejected?

### Persistent planning: `base_schedule` and the split

The fleet keeps moving while `Plan()` runs, so a new schedule must fit around actions that are already committed. The interface handles this with a *split*:

- `PlanRequest.base_schedule` is "the immutable portion of the current schedule". The scheduler "is to assume that all of these actions will be completed". Dispatch fills it with every incomplete action of its schedule; `active_jobs` lists their jobs.
- `ActionNode.outside_split`: "this node is outside the split in the schedule while waiting on the plan call response and will not be sent".

The design is that, while a plan call is in flight, the dispatcher keeps executing the actions before the split and holds back the rest. In the current Dispatch code the split is not applied (the `SplitSchedule` call is commented out), and with overlapping planning off no call is made while jobs are active. The scheduler does not add edges into the base schedule. Instead, `Plan()` makes every resource the base schedule uses unavailable:

``` cpp
// src/scheduler.cpp — Scheduler::Plan (abridged)
for(const auto& node : request_data.base_schedule.nodes) {
  if(node.type == ActionNodeMsg::TYPE_AGV_COMMAND) {
    initial_state.SetAgvDisabled(node.agv_id);                         // the AGV cannot be assigned
    initial_state.SetNodeDisabled(node.agv_command.src.pose.node_id);  // nor its start and goal nodes used
    initial_state.SetNodeDisabled(node.agv_command.dst.pose.node_id);
  }
  else if(node.type == ActionNodeMsg::TYPE_BAY_COMMAND)  { initial_state.SetBayDisabled(node.bay_id); }
  else if(node.type == ActionNodeMsg::TYPE_VECS_COMMAND) { initial_state.SetVecsDisabled(node.vecs_id); }
}
```

So the new ADG cannot conflict with the committed one, because they share no AGV, bay, VECS or start and goal node. The cost is that a busy AGV is unavailable for the whole new plan, even if it would be free a few seconds in. The Background tab traces every place the reservation is read and what could replace it ([section 14](#bg-the-base-schedule-reserved-assets-and-keep-out-filters)). VRC commands in the base schedule are not handled in this loop. Dispatch, for its part, expects the response to contain every base node unchanged and rebuilds its schedule from the response alone; the Dispatch tab describes that check ([section 4](#ds-what-dispatch-does-with-the-response)).

### What this means for the refactor

The action DAG is the last stage before the response, so it reflects every change made upstream. The points below state what the refactor should expect to see change here, how to compare two responses for parity, and which invariants can be checked on every response.

- **The action DAG is downstream of everything the refactor touches.** Tray and AGV assignment change the event DAG, CHUGG plans from it, and the action DAG is built from both. A change in assignment shows up here.
- **Compare reduced graphs, not arrays.** GUIDs are fresh on every call, and the array is one of many topological orders. A parity test should match actions by content (entity, command, poses), then compare the reduced edge sets. Because the transitive reduction is unique ([section 2.4](#ad-transitive-reduction)), equal reduced sets mean an identical order. The [Verification](#doc-verification) tab describes the parity harness.
- **A quirk to preserve, then question.** All VECS commands are chained into one sequence by `BuildScheduledActionsArray` ([section 7.3](#ad-our-edges-versus-type-1-and-type-2)). That serialises charging starts and stops across different VECS. Parity requires keeping it; whether it is intended is a question for the dispatcher owners.
- **Cheap invariants to assert on every response:** every `parents` index is smaller than its own index; each entity's actions form a chain; recomputing C from `duration` gives a makespan close to CHUGG's.
- **Names.** The naming catalogue ([section 15.9.4](#nm-jobs-plans-and-schedules)) proposes `action_indices` for `node_indices` and `parent_indices` for `parents`, because these index actions, not garage nodes.

## Check your understanding

The questions below test the main ideas of this chapter; expand each one to see the answer.

1\. Why does a Type 1 predecessor only need to be enqueued, while a Type 2 predecessor must be finished?

The Type 1 predecessor is on the same robot, which runs its queue in order, so it cannot start the next action before finishing the previous one. A Type 2 predecessor is on another robot; only its completion report proves the location is clear.

2\. In [Figure 3](#ad-fig-86_adg_critical_path), a^3_1 is delayed by 2.5 s. What is the new makespan?

a^3_1 now finishes at 4.5 instead of 2. Its slack is 1, so the end moves by 2.5 - 1 = 1.5: a^1_2 starts at 4.5 and the makespan becomes 11.5.

3\. The action DAG builder adds an edge from every earlier occupant, not just the last one. Why is that still correct, and what does it cost?

Every extra edge points from an earlier action to a later one in a plan that was collision-free, so it never creates a cycle and only restates an order the plan already has. The cost is construction time and memory before `Reduce()`. `Reduce()` is O(\|V\| \cdot \|E\|), so many redundant edges make it slower.

4\. Why can't the occupancy rule alone replace the event-level edges?

Some dependencies involve no shared space. A bay's `PROCESS_RETRIEVE` must wait until the tray has arrived, but the bay command and the tray's last move need not have conflicting footprints. Only the event DAG knows that order.

5\. Two arrays `Schedule.nodes` from the same input list the actions in different orders. Are the schedules different?

Not necessarily. Both may be topological orders of the same DAG. Map actions between the two by content, then compare the reduced edge sets (or the reachability relations). If they are equal, the dispatcher will enforce the same orders.

6\. `Schedule.nodes` is written in one topological order. Does that make the robots move one at a time?

No. The order is only how the graph is listed; each node keeps its `parents`, and execution starts a node as soon as its parents are done, whatever its index. Two unordered actions can be listed either way round and still run together. Only a consumer that ignored `parents` and walked the array would serialise them.

## References

The sources below are cited in this chapter.

- W. Hönig, S. Kiesel, A. Tinka, J. W. Durham, N. Ayanian. "Persistent and Robust Execution of MAPF Schedules in Warehouses." *IEEE Robotics and Automation Letters*, 2019. [PDF](https://act.usc.edu/publications/Hoenig_RAL2019.pdf). The ADG, its construction (Algorithm 1) and the enqueue rule.
- W. Hönig, T. K. S. Kumar, L. Cohen, H. Ma, H. Xu, N. Ayanian, S. Koenig. "Multi-Agent Path Finding with Kinematic Constraints." *ICAPS*, 2016. The temporal plan graph.
- A. Berndt, N. van Duijkeren, L. Palmieri, T. Keviczky. "A Feedback Scheme to Reorder a Multi-Agent Execution Schedule by Persistently Optimizing a Switchable Action Dependency Graph." 2020. [arXiv:2010.05254](https://arxiv.org/abs/2010.05254). Receding-horizon version: [arXiv:2312.04190](https://arxiv.org/abs/2312.04190).
- J. Dunkel. "Streamlining the Action Dependency Graph Framework: Two Key Enhancements." 2024. [arXiv:2412.01277](https://arxiv.org/abs/2412.01277).
- Y. Wu, R. Veerapaneni, J. Li, M. Likhachev. "From Space-Time to Space-Order: Directly Planning a Temporal Planning Graph by Redefining CBS." 2024. [arXiv:2404.15137](https://arxiv.org/abs/2404.15137).
- A. V. Aho, M. R. Garey, J. D. Ullman. "The Transitive Reduction of a Directed Graph." *SIAM Journal on Computing* 1(2), 1972.

## Design notes

With all five stages behind us, these notes step back and look at the design as a whole. Each note separates what the code does (with evidence) from opinion (marked as such).

### Events plus a DAG: two established models combined

Two established ideas are combined here:

1.  **Precedence-constrained scheduling.** Activities with "finish before start" constraints form a DAG. This is the standard model in project scheduling (critical-path networks) and shop scheduling. The event DAG built in job expansion is exactly this: "the bay must open before the tray goes in".
2.  **Action dependency graphs for multi-robot execution** (Hönig et al., [RA-L 2019](https://act.usc.edu/publications/Hoenig_RAL2019.pdf)), the subject of this tab ([section 3](#ad-from-a-timed-plan-to-an-adg)). The scheduler's response is one ([section 6.2](#ad-how-the-action-dag-is-built)).

The scheduler uses **both**, as two separate graphs ([section 6.1](#ad-two-dags-two-jobs)). The event DAG is the first kind: it exists before any motion is planned and is the motion planner's input. The action DAG is the second kind, built from CHUGG's trajectories; it inherits the event DAG's edges, so the task logic ends up in the execution policy without the event DAG ever becoming it.

### Comparison with Open-RMF's `rmf_traffic`

Open-RMF's `rmf_traffic` has no DAG; it is a database updated by events. The two systems solve different problems.

|                        | Open-RMF `rmf_traffic`                                                                                                                                                                                                                                                    | This scheduler                                                                                                            |
|------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| Who plans robot paths  | Each fleet or participant plans its own robots                                                                                                                                                                                                                            | One central planner plans every AGV                                                                                       |
| Shared object          | A traffic **schedule database** of timed itineraries. Participants write through `schedule::Writer`: `set`, `extend`, `delay`, `reached`, `clear` ([API](https://openrmf.readthedocs.io/projects/rmf-traffic/en/latest/api/classrmf__traffic_1_1schedule_1_1Writer.html)) | A `PlanRequest` holding the current garage state and in-flight actions, answered with a full schedule                     |
| Conflicts              | Detected between itineraries and resolved by negotiation (for example `rmf_traffic::agv::CentralizedNegotiation`, [API](https://openrmf.readthedocs.io/projects/rmf-traffic/en/latest/api/classrmf__traffic_1_1agv_1_1CentralizedNegotiation.html))                       | Avoided at planning time: precedence edges plus collision-aware motion planning (CHUGG)                                   |
| Coupling between tasks | Mostly spatial: robots share corridors                                                                                                                                                                                                                                    | Strong and logical: moving one car can require moving several other trays first, an AGV must lift a tray, bays have modes |
| Built for              | Many heterogeneous fleets from different vendors in one building                                                                                                                                                                                                          | One tightly coupled automated garage                                                                                      |

Two nuances:

- **Open-RMF is not entirely free of dependencies.** Its routes can declare them: `DependsOnCheckpoint` is a map where "the checkpoint in the value waits for the checkpoint in the key" ([API](https://openrmf.readthedocs.io/projects/rmf-traffic/en/latest/api/typedef_Route_8hpp_1a9125a240740855280a6356bbf1591153.html)). That is a precedence edge between plans.
- **This scheduler is event-driven too, just one level up.** `Scheduler::Plan()` keeps no state between calls: everything lives in a fresh `ScheduleContext`. The live state and the job queue are held by Dispatch, which sends `base_state` (the garage now) and `base_schedule` (actions already executing; `Plan()` marks their AGVs, nodes, bays and VECS disabled) with every request. "A robot went down" or "a new car arrived" therefore means a new `PlanRequest`, not an edit to an old DAG. Dispatch is not in the snapshot, so when exactly it replans cannot be shown here.

Why a DAG fits better here (opinion): the hard part of this garage is not two robots meeting in a corridor but chains like "to retrieve T17, first move T15 out of its way, which needs a free spot, which needs the bay to switch mode". Those are precedence constraints, and a DAG states them directly. A traffic database would still need something like it to express "this tray move must finish before that one starts".

### A DAG and its topological order allow parallel commands

A DAG is a partial order, so a topological order of it does not serialise execution ([section 2.4](#ad-topological-orders-and-parallelism)). The figure applies that to the scheduler's own response, separating the **DAG** (the constraints), the **topological order** (one list that respects them) and the **execution** (what happens in time).

![From one DAG to a sorted list to parallel execution](figures/54_partial_order_parallel.svg)

\(1\) The input is one action DAG; its three lanes are linked by edges. (2) A topological sort lists the same ten actions so that every edge points right; it adds no information about time. (3) The response stores that list as `Schedule.nodes`, and each node keeps the indices of its parents. (4) In execution, every node whose parents are done can start, so Y1, A1 and B1 start together, and B3 waits only for its parent A3.

Read it as a pipeline:

1.  **Input: one DAG**, not several. The lanes are only a way of drawing it; the bay edges and the occupancy edge connect them. (Even a DAG with no edges between lanes would be fine: it would simply mean nothing waits for anything.)
2.  **The topological sort produces a list**, `std::optional<VertexVec>`. It neither creates nor removes parallelism; it only guarantees that every node comes after its parents. The scheduler uses this list to replay events on a `DiscreteGarageState` and to number the actions.
3.  **The response keeps both the list and the edges.** `BuildScheduledActionsArray` walks the action DAG in topological order, gives each action its position in `Schedule.nodes`, and fills `parents` from its in-edges plus the previous action of the same AGV, bay or VRC. So the "sorted graph" is exactly this: a sorted array in which every node points back to its parents, always at smaller indices.
4.  **Execution is driven by `parents`, not by array order** ([section 4](#ad-executing-an-adg) explains why that is safe). A node can start as soon as all its parents are done; nodes without a path between them run at the same time. The times themselves come from motion planning: in the `ContinuousStateToSchedule` test, AGV-1 and AGV-2 both have motions starting at `t = 0`. How Dispatch's executor consumes `parents` is outside this package.

Parallelism is still lost wherever an edge exists. Some edges are physical (one AGV does one thing at a time; a tray is in one place). Others are choices: rule B orders every step of a job even when two steps could overlap, and REBALANCE_GARAGE runs its bays one after another because they share a job index ([section 14.18](#bg-gotchas-2)). Those are fair targets for improvement.

### Where the complexity comes from

Some of the complexity is forced by the problem and some is added by the code. The two are separated below.

**What the problem forces.** Trays block each other, an AGV must fetch a tray before carrying it, bays and VECS have modes, and every job's plan depends on where earlier jobs leave things. Some precedence structure is unavoidable. Separating *what must happen in which order* (the event DAG) from *how and when robots move* (CHUGG) and from *in which order the robots may use shared space* (the action DAG) is a sound and common split: task planning, multi-agent path finding, then an action dependency graph for execution.

**What the code adds** (evidence from `scheduler.cpp`):

- **One mutable DAG, edited by three passes.** Job expansion leaves blanks (`T21 -> ?`), tray assignment fills them and adds blocker moves, AGV assignment adds approach, lift and lower events. To know what an event looks like you need to know which pass you are in.
- **Edges come from many places.** `AddDependency` appears 28 times in `scheduler.cpp`, spread over ten `Scheduler` methods (`DoTrayAssignments` 7, `AssignDestForUntargetedMove` 5, `MoveAgvToTrayPose` 3, `PlanReparkTrayJob` 2, `DoAgvAssignments` 2, `AddDepsAfterAmiga` 2, and one each in `AppendAgvLiftEvent`, `AddNodeArrivalDeps`, `GetEventDag` and `TryClearBlockedAgvMove`), plus the two `ScheduleContext` helpers. An edge does not record why it was added, and `Reduce()` later removes the redundant ones, so the final DAG does not show where its edges came from.
- **Repeated replay.** Almost every step copies `initial_state` and replays the whole DAG to know the current state.
- **Implicit conventions.** `job_index` is a position in a list that only successful jobs enter; failed jobs can leave events behind ([section 14.18](#bg-gotchas-2)).

**What would make it easier to follow** (suggestions, not plans): record a reason or kind on every edge; keep each kind of constraint in one function; check invariants after each pass (acyclic, every `TrayMove` complete, no leftover events); give each pass a narrow input and output. That last point is what the solver interfaces in the [Issue & proposal](#doc-proposal) tab start to do, and [section 2.2](#pr-is-task-planning-too-complex) there sorts this complexity into what the problem needs and what can go. Until then, the `debug/printdags` service ([section 22](#bg-debugging-and-testing)), which logs the DAG after each pass, is the best way to see what the code built.

## Known limitations and reading checkpoint

Across the whole pipeline, limits of the code worth remembering: `GetAgvOccupiedDuration` returns zero; failed jobs can leave events in the DAG; any failure after expansion fails all jobs in the request, except CHUGG's exceptions, which nothing in the scheduler catches; `Reduce()` placement is load-bearing; `UseEvChargeHeading` contains a hard-coded site rule; CHUGG plans loaded moves at unloaded speed and three places disagree on wheel-turn time ([section 23.2](#bg-the-cost-model)); `PROCESS_RETRIEVE` is a hard-coded 60 s.

**Before reading the [Issue & proposal](#doc-proposal) tab, check you can answer:**

1.  What is the difference between a job, an event, a motion and an action, and which graph holds each?
2.  Which DAG does CHUGG take as input, which DAG does Dispatch execute, and how do edges get from the first to the second?
3.  In which order does CHUGG plan events, and why can adding one edge change the whole plan?
4.  In `Scheduler::Plan`, what is `this`, what is `plan_ctx`, and why can a `const` method still change the plan?
5.  Why does every `Plan<Type>Job` start by copying `ctx->initial_state` and calling `ctx->events.Apply`?
6.  What makes a `TrayMove` incomplete, and which stage completes each missing part?
7.  What does an edge in `ScheduleEventDag` mean, and which three rules add edges during job expansion?
8.  Why is `first_tray_event` recorded in tray assignment and read in AGV assignment?
9.  What does bottleneck matching optimise, and why might it not pick the lowest total cost?
10. When does `Plan()` return `success == false`, and how do you tell which jobs really failed?
11. How does a bay differ from a VECS and from a VRC in this code?
