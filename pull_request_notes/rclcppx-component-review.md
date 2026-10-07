# `rclcppx::Component` — Syntax, Patterns, and Design Review

This header wraps an application object and its ROS node so they can be exposed through ROS 2's component interface. Its central choices are composition, constructor dependency injection, compile-time constraints, and member ordering for lifetime management.

The review below distinguishes what the code guarantees from conventions and inferred design intent. The implementation of `CreateNode` and the application's implementation were not supplied.

## 1. Inventory: concepts, idioms, patterns, and features

### Language and library features

| Feature | Application in this header |
|---|---|
| `#pragma once` | Common compiler-supported header inclusion guard; not a standard C++ directive |
| `#include` | Imports declarations needed by the header |
| Nested namespaces | C++17 syntax `namespace volley::rclcppx` |
| Class and function templates | Generic application/node wrapper and `CreateNode<NodeT>` call |
| Default template argument | `NodeT = rclcpp::Node` supplies the normal node type |
| C++20 concept definition | `ComponentApp` names the application's requirements |
| `std::constructible_from` | Tests construction from specified argument types and nonthrowing destructibility |
| `std::convertible_to` | Tests conversion of the name expression to `std::string_view` |
| Requires-expression | `requires { ... }` checks expressions without executing them |
| Compound requirement | `{ expression } -> Concept` constrains the expression's type |
| Requires-clause | Restricts admissible `Component` template arguments |
| Qualified member lookup | `NodeAppT::kNodeName` refers to application metadata by type |
| `std::string_view` | Non-owning string interface used by the name constraint |
| `std::string` | Creates an owning name for the node factory |
| `std::shared_ptr` | Holds a shared ownership handle to the node |
| `explicit` constructor | Prevents implicit conversion from `NodeOptions` |
| Const reference parameter | Passes options without copying and prevents ordinary mutation through that parameter |
| Member initializer list | Directly constructs `node_` and `app_` |
| Embedded object member | Stores the application directly, without a separate application allocation |
| Overloaded `operator->` | Accesses the node through its smart pointer |
| Nested type alias | ROS's `NodeBaseInterface::SharedPtr` return type |
| Const member function | Keeps the wrapper's pointer member unchanged when obtaining the interface |
| Access control | Public adapter API and private storage |
| Implicit special members | Compiler-generated copy/move/destruction operations, subject to member capabilities |
| Declaration-order initialization | Constructs `node_` before `app_` |
| Reverse-order destruction | Destroys `app_` before releasing `node_` |
| Doxygen comments | Describes the public API and lifetime intention |
| Lint annotation | Allows the external API's required naming style |

### Idioms and architectural patterns

| Idiom or pattern | Application |
|---|---|
| RAII | Members manage resources through construction and destruction |
| Rule of Zero | No manually implemented resource-management special members |
| Composition over inheritance | Wrapper has a node and an application; app need not inherit from a node |
| Constructor dependency injection | Wrapper creates the node and passes it to the application |
| Adapter | Exposes the component-facing API around an application-facing constructor |
| Constrained generic programming | Accepts types according to their supported operations |
| Compile-time structural interface | No application base class is required |
| Type customization point | `NodeT` changes the node implementation; calling this a full policy-based design would overstate it |
| Factory delegation | Node construction is centralized in `CreateNode` |
| Lifetime dependency encoded in storage | Member order keeps the wrapper's node handle alive during application destruction |

## 2. The source

```cpp
#pragma once

#include <concepts>
#include <memory>
#include <rclcpp/node.hpp>
#include <rclcpp/node_interfaces/node_base_interface.hpp>
#include <rclcpp/node_options.hpp>
#include <rclcppx/node.hpp>
#include <string>
#include <string_view>

namespace volley::rclcppx {

/// A type constructible from a node that declares its node name as `kNodeName`.
template <typename NodeAppT, typename NodeT>
concept ComponentApp =
    std::constructible_from<NodeAppT, const std::shared_ptr<NodeT>&> &&
    requires {
      { NodeAppT::kNodeName } -> std::convertible_to<std::string_view>;
    };

/// Stores a NodeAppT and its node, exposing the ROS component interface.
template <typename NodeAppT, typename NodeT = rclcpp::Node>
  requires ComponentApp<NodeAppT, NodeT>
class Component {
public:
  explicit Component(const rclcpp::NodeOptions& options) :
      node_(CreateNode<NodeT>(std::string(NodeAppT::kNodeName), options)),
      app_(node_) { }

  /// Returns the node's base interface, required by rclcpp_components.
  // NOLINTNEXTLINE(readability-identifier-naming)
  rclcpp::node_interfaces::NodeBaseInterface::SharedPtr
  get_node_base_interface() const {
    return node_->get_node_base_interface();
  }

private:
  // Declared before app_ so it outlives it.
  std::shared_ptr<NodeT> node_;
  NodeAppT app_;
};

}  // namespace volley::rclcppx
```

## 3. Concept syntax in detail

### 3.1 A concept is a named compile-time predicate

```cpp
template <typename NodeAppT, typename NodeT>
concept ComponentApp = /* constraint expression */;
```

`NodeAppT` and `NodeT` are type parameters. Substituting concrete types produces a constraint that can be satisfied or unsatisfied. It creates no application or node at runtime.

For example:

```cpp
static_assert(ComponentApp<MyApp, rclcpp::Node>);
```

asks the compiler to reject the program if these types do not meet the requirements. `ComponentApp` is not a base class, object, or ordinary function.

### 3.2 Reading `std::constructible_from`

```cpp
std::constructible_from<
    NodeAppT,
    const std::shared_ptr<NodeT>&
>
```

Read this as:

> Can a `NodeAppT` be directly initialized using one argument of type `const std::shared_ptr<NodeT>&`, and does it satisfy `std::destructible`?

| Syntax | Meaning |
|---|---|
| `std::` | The concept is in the standard library namespace |
| `constructible_from` | Name of the standard concept |
| `< ... >` | Template arguments, all types here |
| `NodeAppT` | Type to construct |
| Comma | Separates the target type from argument types |
| `const std::shared_ptr<NodeT>&` | Type of the single construction argument |

The nested brackets belong to two different template argument lists: `<NodeT>` belongs to `shared_ptr`; the final `>` closes `constructible_from`. Line breaks only improve readability.

The standard definition is:

```cpp
template<class T, class... Args>
concept constructible_from =
    destructible<T> && is_constructible_v<T, Args...>;
```

`class... Args` is a parameter pack: zero, one, or several argument types. Here `T` becomes `NodeAppT`, and the pack contains exactly one type. Other examples are `std::constructible_from<T>` for default construction and `std::constructible_from<T, int, double>` for construction from two arguments. [1]

### 3.3 What `const std::shared_ptr<NodeT>&` means

Build the type from inside outward:

1. `NodeT`: the node's type.
2. `std::shared_ptr<NodeT>`: a shared ownership handle to that node.
3. `const std::shared_ptr<NodeT>`: a handle that cannot ordinarily be reset or reassigned through this access path.
4. `const std::shared_ptr<NodeT>&`: a reference to that const handle, avoiding an obligatory handle copy when binding the argument.

The node itself remains mutable. This differs from `std::shared_ptr<const NodeT>`, which provides access to a const node.

```cpp
void inspect(const std::shared_ptr<NodeT>& node) {
  // node.reset();       // Error: modifies the const handle.
  // node->some_method(); // May call a non-const node method.
  auto owner = node;    // Allowed: copies the handle, sharing ownership.
}
```

Passing the reference alone does not add an owner. Copying it into the application does.

### 3.4 What construction is being tested?

For an ordinary application class, a useful approximation is:

```cpp
using NodePtr = std::shared_ptr<NodeT>;

// Hypothetical input, not something the concept executes:
const NodePtr& node = /* existing handle */;
NodeAppT app(node);
```

The underlying trait checks a hypothetical direct initialization using the argument types. Overload resolution and permitted conversions apply; the constructor need not have an identical parameter declaration. An `explicit` constructor is eligible. Private, deleted, or ambiguous applicable constructors prevent successful construction in this check.

For reference arguments, the reference qualification determines the input's value category: this argument is a const lvalue. The trait checks the immediate initialization context; it does not certify arbitrary code inside a constructor body. A declared constructor can satisfy the trait yet still cause a compilation or link failure when actually used. [2]

### 3.5 Which constructor signatures satisfy it?

Assume `using NodePtr = std::shared_ptr<NodeT>;`, a public constructor, a normally destructible class, and no interfering overloads.

| Constructor | Satisfies the check? | Explanation |
|---|---|---|
| `explicit App(const NodePtr&)` | Yes | Binds the const lvalue directly |
| `explicit App(NodePtr)` | Yes | Copies the handle into the parameter |
| `explicit App(NodePtr&)` | No | Cannot bind a const lvalue to a non-const reference |
| `explicit App(NodePtr&&)` | No | An rvalue reference cannot bind this const lvalue |
| `explicit App(NodeT&)` | No | A smart pointer does not implicitly become a node reference |
| `App()` only | No | Does not accept the required argument |

These examples are specific to the supplied type and ordinary reference-binding rules. A converting or templated constructor can also qualify.

```cpp
struct App {
  explicit App(std::shared_ptr<rclcpp::Node> node);
};

static_assert(std::constructible_from<
    App, const std::shared_ptr<rclcpp::Node>&>);
```

The by-value constructor works even though the tested argument type is a const reference. The check asks whether construction is possible, not whether a signature matches exactly.

### 3.6 The additional destruction requirement

`std::destructible<T>` is defined in terms of `std::is_nothrow_destructible_v<T>`. An ordinary application class needs an accessible, non-deleted destructor considered nonthrowing. A destructor declared `noexcept(false)` fails this requirement. [3]

```cpp
struct RiskyApp {
  explicit RiskyApp(const std::shared_ptr<rclcpp::Node>&);
  ~RiskyApp() noexcept(false);
};

static_assert(!std::constructible_from<
    RiskyApp, const std::shared_ptr<rclcpp::Node>&>);
```

The constructor itself may throw. `constructible_from` does not mean nonthrowing construction; `std::is_nothrow_constructible_v` tests that stronger property.

### 3.7 How `&&` combines requirements

```cpp
std::constructible_from<NodeAppT, const std::shared_ptr<NodeT>&>
    && requires { /* name requirement */ };
```

Both constraints must be satisfied. The left checks application construction and destruction; the right checks the name expression. Constraint conjunction short-circuits during satisfaction checking.

### 3.8 The requires-expression and arrow

```cpp
requires {
  { NodeAppT::kNodeName } -> std::convertible_to<std::string_view>;
}
```

The outer braces contain requirements. The inner braces introduce a **compound requirement**. The arrow attaches a constraint to the expression's type; it performs no conversion and is not a function call.

Its type constraint is effectively:

```cpp
std::convertible_to<
    decltype((NodeAppT::kNodeName)),
    std::string_view
>
```

The compiler supplies the first concept argument from `decltype((expression))`; the written `std::string_view` is the second. Double parentheses preserve the expression's reference/value-category information. For a static `constexpr std::string_view` member, this expression is an lvalue and the type is `const std::string_view&`. [4]

`std::convertible_to<From, To>` checks implicit conversion and a corresponding `static_cast`. It also imposes semantic requirements that those conversions produce consistent results; the compiler cannot generally prove all semantic promises for user-defined conversions. [5]

The normal intended declaration is:

```cpp
static constexpr std::string_view kNodeName = "motor_controller";
```

The requirement does not establish that the name is valid ROS syntax, nonempty, immutable, or a constant expression. Nor should this unevaluated member expression alone be treated as a complete guarantee that the member is static: non-static members can be named in some unevaluated contexts. Actual runtime access must also be valid.

### 3.9 Requires-expression versus requires-clause

```cpp
template <typename NodeAppT, typename NodeT = rclcpp::Node>
  requires ComponentApp<NodeAppT, NodeT>
class Component { /* ... */ };
```

This `requires` introduces a **requires-clause**: it limits which template arguments are admissible. The earlier `requires { ... }` was an expression that computes whether its listed requirements hold. One defines a check; the other applies the named check to a declaration.

## 4. How the features apply at runtime

### Construction

```cpp
node_(CreateNode<NodeT>(std::string(NodeAppT::kNodeName), options)),
app_(node_)
```

1. Convert the application name into an owning string.
2. Ask `CreateNode<NodeT>` to produce the node handle.
3. Initialize `node_`.
4. Construct `app_` using that handle.
5. Enter the empty constructor body.

Member declaration order determines initialization order, regardless of initializer-list order. The declarations therefore encode a dependency: application construction occurs after node-handle initialization.

`explicit` prevents an options object from silently becoming a component, an operation that creates runtime resources. Direct construction remains allowed:

```cpp
Component<MyApp> component(options);
```

### Destruction and exceptions

`app_` is destroyed first; `node_` is then destroyed and releases its ownership share. The node object is destroyed only when its ownership count reaches zero. Other owners may extend its lifetime.

If application construction throws, the initialized node handle is cleaned up during unwinding. The failed application's own fully constructed subobjects are cleaned up; its complete-object destructor is not called because construction never finished.

Member ordering guarantees availability of the wrapper's node handle during normal application destruction, assuming it still holds the node. It does not automatically stop callbacks, join worker threads, or prevent application-created ownership cycles. Those behaviors belong to the application and executor setup.

### ROS interface forwarding

```cpp
get_node_base_interface() const {
  return node_->get_node_base_interface();
}
```

The wrapper forwards the component-facing request to its node. Its `const` qualification does not make the pointee const: a const smart pointer still permits mutable access to `NodeT`.

### Typical application

```cpp
class MotorController {
public:
  static constexpr std::string_view kNodeName = "motor_controller";

  explicit MotorController(
      const std::shared_ptr<rclcpp::Node>& node)
      : node_(node) {
    // Create publishers, subscriptions, timers, etc.
  }

private:
  std::shared_ptr<rclcpp::Node> node_;
};

using MotorControllerComponent =
    volley::rclcppx::Component<MotorController>;
```

This application copies the injected handle and becomes another owner. It contains application behavior while the wrapper supplies construction and interface forwarding for component loading.

### 4.1 Practical usage: what do I actually define?

**You normally define only the application class. You do not need to derive a custom node from `rclcpp::Node`.** The wrapper defaults to the existing `rclcpp::Node` type and constructs that node for you.

The roles are:

| Type | Responsibility | Defined by |
|---|---|---|
| `rclcpp::Node` | ROS infrastructure: timers, publishers, subscriptions, parameters | ROS |
| `HeartbeatApp` | Your application behavior; accepts a node during construction | You |
| `Component<HeartbeatApp>` | Creates the node and app; supplies the component-facing API | This wrapper |

For the default case, the construction relationship is `Component<HeartbeatApp>` creates a `rclcpp::Node`, then constructs `HeartbeatApp` using the resulting shared pointer.

### 4.2 A concrete application and standalone `main()`

This example uses a timer to make execution visible. The include `rclcppx/component.hpp` assumes that is the filename of the supplied wrapper; substitute its actual include path if different. The project must provide the supplied wrapper and `CreateNode`, link against `rclcpp`, and enable C++20.

```cpp
#include <chrono>
#include <memory>
#include <string_view>

#include <rclcpp/rclcpp.hpp>
#include <rclcppx/component.hpp>  // The supplied wrapper header.

class HeartbeatApp {
public:
  static constexpr std::string_view kNodeName = "heartbeat";

  explicit HeartbeatApp(
      const std::shared_ptr<rclcpp::Node>& node)
      : node_(node) {
    timer_ = node_->create_wall_timer(
        std::chrono::seconds(1),
        [logger = node_->get_logger()]() {
          RCLCPP_INFO(logger, "Heartbeat");
        });
  }

private:
  // Keep both the node and timer available for the app's lifetime.
  std::shared_ptr<rclcpp::Node> node_;
  rclcpp::TimerBase::SharedPtr timer_;
};

using HeartbeatComponent = volley::rclcppx::Component<HeartbeatApp>;

// Optional: documents and checks the app contract explicitly.
static_assert(volley::rclcppx::ComponentApp<HeartbeatApp, rclcpp::Node>);

int main(int argc, char* argv[]) {
  rclcpp::init(argc, argv);

  {
    const rclcpp::NodeOptions options;
    HeartbeatComponent component(options);

    rclcpp::executors::SingleThreadedExecutor executor;
    const auto node_base = component.get_node_base_interface();
    executor.add_node(node_base);
    executor.spin();
    executor.remove_node(node_base);
  }  // Executor/interface handle go away, then app and node handle.

  rclcpp::shutdown();
  return 0;
}
```

The concept is checked at compile time when the constrained component type is used. `HeartbeatComponent component(options)` then constructs a runtime object. `executor.spin()` runs callbacks until spinning is stopped, commonly by shutdown after Ctrl+C. The executor accepts the node's base interface; it does not require this wrapper to inherit from `rclcpp::Node`. [8]

Keep `component` alive while callbacks execute: an interface pointer alone does not own its embedded application. This example shows the ordinary success path; a production executable can add exception handling according to the project's shutdown/error policy. These ROS examples have not been compiled against a local ROS installation.

### 4.3 Is the concept itself instantiated?

Precisely speaking, **concepts are not instantiated like classes**. A concept-id such as `ComponentApp<HeartbeatApp, rclcpp::Node>` is evaluated as a constraint. It creates no runtime object. [6]

These are different operations:

```cpp
// Evaluate the named constraint; no node or app is created.
static_assert(volley::rclcppx::ComponentApp<HeartbeatApp, rclcpp::Node>);

// Name a constrained class-template specialization.
using C = volley::rclcppx::Component<HeartbeatApp>;

// Construct an object: creates a node and then constructs the app.
C component(options);
```

The compiler applies the wrapper's `requires ComponentApp<NodeAppT, NodeT>` automatically. You do not have to call the concept or write a `static_assert` first. The optional assertion gives an explicit contract check near the application definition.

If the app lacks the required constructor or usable name expression, using it as this wrapper's template argument fails constraint checking. Passing the concept still does not verify the factory body or all other operations, as discussed in section 6.

### 4.4 When would I define a custom node subclass?

Use a subclass when you need additional node-specific behavior or an existing project-specific node type. It is optional, not a prerequisite for the application pattern.

```cpp
class CustomNode : public rclcpp::Node {
public:
  CustomNode(const std::string& name, const rclcpp::NodeOptions& options)
      : rclcpp::Node(name, options) {}

  void announce() {
    RCLCPP_INFO(get_logger(), "Using CustomNode");
  }
};

class CustomApp {
public:
  static constexpr std::string_view kNodeName = "custom_app";

  explicit CustomApp(const std::shared_ptr<CustomNode>& node)
      : node_(node) {
    node_->announce();
    // Create and retain this application's ROS entities here.
  }

private:
  std::shared_ptr<CustomNode> node_;
};

using CustomComponent =
    volley::rclcppx::Component<CustomApp, CustomNode>;

static_assert(volley::rclcppx::ComponentApp<CustomApp, CustomNode>);
```

Add `<string>` for this snippet. In the previous `main()`, replace `HeartbeatComponent` with `CustomComponent`; executor setup is the same. This particular app just logs once during construction, so there is no recurring callback until you add one.

**Factory assumption:** this custom-node example requires `CreateNode<CustomNode>` to support the shown constructor. Inheritance alone does not establish that. Confirm the factory implementation before treating this example as a supported extension.

An app accepting `std::shared_ptr<rclcpp::Node>` by value can also receive a compatible derived-node shared pointer via conversion. An app accepting only `std::shared_ptr<CustomNode>` needs the custom node type supplied to the wrapper; the default base-node type will not meet its constructor requirement.

### 4.5 Can I run the app without the wrapper?

Yes. Constructor injection also supports direct construction:

```cpp
int main(int argc, char* argv[]) {
  rclcpp::init(argc, argv);
  {
    auto node = std::make_shared<rclcpp::Node>(
        std::string(HeartbeatApp::kNodeName), rclcpp::NodeOptions{});
    HeartbeatApp app(node);
    rclcpp::spin(node);
  }
  rclcpp::shutdown();
  return 0;
}
```

This alternative uses the application directly and never applies `ComponentApp`. The wrapper is useful when you want its centralized `CreateNode` behavior and component-facing interface. Direct `make_shared` construction bypasses any additional factory policies.

### 4.6 Standalone execution versus dynamically loaded components

The `main()` above manually constructs and executes the wrapper. For dynamic component loading, register the wrapper specialization in a library translation unit:

```cpp
#include <rclcpp_components/register_node_macro.hpp>
// Include the header defining HeartbeatApp and its wrapper alias.

using HeartbeatComponent = volley::rclcppx::Component<HeartbeatApp>;
RCLCPP_COMPONENTS_REGISTER_NODE(HeartbeatComponent)
```

The macro registers the wrapper type with the component factory. A component container supplies the executable and executor, so the component library does not need the standalone `main()`. The package also needs its shared-library target, component build registration, and dependencies. The macro alone is not the complete packaging setup. [9]

### 4.7 Should the concept's second argument have a default?

**Yes, that is legal and reasonable if `rclcpp::Node` is the usual case.** Replace the original concept definition with:

```cpp
template <typename NodeAppT, typename NodeT = rclcpp::Node>
concept ComponentApp =
    std::constructible_from<NodeAppT, const std::shared_ptr<NodeT>&> &&
    requires {
      { NodeAppT::kNodeName } -> std::convertible_to<std::string_view>;
    };
```

Now these checks are equivalent:

```cpp
static_assert(ComponentApp<HeartbeatApp>);
static_assert(ComponentApp<HeartbeatApp, rclcpp::Node>);
```

Custom checks remain explicit:

```cpp
static_assert(ComponentApp<CustomApp, CustomNode>);
```

These unqualified examples assume you are inside `volley::rclcppx` or have brought its concept name into scope. Defaults apply when arguments are omitted; they do not infer `NodeT` from an application's constructor. [7]

The wrapper and concept have **independent defaults**. Keep the wrapper's default too:

```cpp
template <typename NodeAppT, typename NodeT = rclcpp::Node>
  requires ComponentApp<NodeAppT, NodeT>
class Component {
  // Original implementation.
};
```

Here the wrapper explicitly forwards its chosen `NodeT` to the concept, so the concept's default is unused in that clause. Adding a default to the concept does not automatically add one to the class template or change runtime behavior.

Avoid shortening that clause to `requires ComponentApp<NodeAppT>`: it would check compatibility with `rclcpp::Node` even when the wrapper was configured with `CustomNode`.

After adding the concept default, a standalone generic function can also use concise constrained-parameter syntax:

```cpp
template <ComponentApp App>
void check_default_app() {
  // App is constrained by ComponentApp<App, rclcpp::Node>.
}
```

For a generic two-type wrapper, the existing explicit requires-clause is clearer because it shows the relationship between both types.

**Recommendation:** keep the wrapper default. Add the concept default if application authors commonly use it directly in assertions or other constraints. Leaving the concept's two inputs explicit is equally sound if it is only an internal predicate used by the wrapper. This is an API convenience decision, not a missing correctness requirement. The original source listing above remains unchanged; this subsection shows the optional replacement definition.

## 5. Design intent

The apparent intent is to separate application behavior from component-loading infrastructure. An application can operate on an injected node without itself inheriting from `rclcpp::Node`.

The wrapper owns the application directly and holds a node ownership handle. This reduces application allocation and keeps the adaptation layer small. A centralized factory can provide consistent node construction, although its actual policies cannot be inferred from this header alone.

The application contract is deliberately narrow: receive a node and supply a default node name. This can make applications easier to construct in different contexts. It does not, by itself, make ROS behavior mockable or independent of ROS: that depends on what the application uses and how the node type is substituted.

`NodeT` is a useful customization point, but the supported range depends on `CreateNode` and the node interface. Type-level naming provides a canonical default; whether deployments override it through ROS remapping depends on factory and options handling.

## 6. Does it make sense? What is lacking?

**Yes: the abstraction is compact and coherent.** Composition, dependency injection, and member ordering all serve its purpose. However, the earlier claim that the concept exactly matches every implementation operation was too strong.

### 6.1 The const-reference check does not enforce const-reference use

The concept checks construction from a const lvalue, but this expression passes a non-const lvalue:

```cpp
app_(node_)
```

An app can provide both overloads:

```cpp
App(const NodePtr&);  // Makes the concept succeed.
App(NodePtr&);        // Can be selected by app_(node_).
```

The second overload could reset or move from the wrapper's handle. A deleted non-const overload can even make the actual call fail despite the concept succeeding.

If const access to the handle is the intended contract, make the call reflect it:

```cpp
#include <utility>

// In the initializer list:
app_(std::as_const(node_))
```

This still allows copying ownership and mutating the node itself.

### 6.2 Name checking and name construction should align

The concept checks conversion to `string_view`; the constructor directly constructs a `string` from the original expression. Normal string types work, but generic code is clearer when the constraint and use agree.

One option preserves the string-view contract and explicitly uses that conversion:

```cpp
std::string(std::string_view(NodeAppT::kNodeName))
```

Another option checks the precise original operation in a requires-expression:

```cpp
requires {
  std::string(NodeAppT::kNodeName);
}
```

Use a simple requirement for this validity check. Also document `static constexpr` as the intended metadata convention, or enforce the stronger properties if they matter.

### 6.3 The node contract is implicit

This header assumes `CreateNode<NodeT>(name, options)` produces a compatible handle and that `node_->get_node_base_interface()` returns a compatible interface pointer.

A separate node concept could check those expressions if arbitrary custom nodes are a supported API. However, checking a factory call's declaration does not necessarily validate its function body. A useful factory constraint must also constrain its underlying construction operations.

Review `rclcppx/node.hpp` before adding redundant requirements. It may already specify the node contract.

### 6.4 Copy/move policy needs a deliberate decision

Copying can create two application objects associated with the same node. Moving can break an application that retains a reference to the wrapper's `shared_ptr` member rather than copying it: that reference still points at the old wrapper's member.

Assignment is especially subtle. Implicit assignment updates `node_` before `app_`. The destination's old node could be released while its old application state still needs it. An application holding its own ownership copy may avoid this, but the concept does not require one.

For runtime components with stable identity, deleting copy and move operations is a reasonable policy. If moving is needed, establish and document the application's ownership/reference invariants before defaulting it. The Rule of Zero simplifies resource management; it does not prove that memberwise value semantics are appropriate.

### 6.5 Shared ownership is a choice, not inherently a flaw

`NodeT&` would express borrowing more strictly if the application needs the node only during its own lifetime. A `shared_ptr` permits the application and asynchronous work to extend node lifetime.

The existing member order and shared ownership are compatible: the order ensures the wrapper retains its share through app destruction, while shared pointers allow other owners. Decide based on actual application usage rather than changing ownership just for stylistic purity.

### 6.6 Runtime assumptions remain

The wrapper dereferences its node handle without a null check. That is sensible if `CreateNode` guarantees a non-null result or throws. Verify that guarantee in the factory.

Construction failure is naturally propagated through exceptions; local recovery is not inherently necessary in this adapter. Callback shutdown, executor removal, and lifecycle-node transitions are separate concerns that this header does not implement.

## 7. Review priorities

1. Inspect `CreateNode` for node constraints, non-null guarantees, options, and remapping behavior.
2. Align the actual app argument with the const-reference contract if that contract is intentional.
3. Choose an explicit copy/move/assignment policy.
4. Align name conversion with its constraint and document the metadata convention.
5. Add a node concept if custom node types are a real public extension point.
6. Confirm application teardown handles its callbacks and asynchronous work.

The wrapper's purpose and structure are sound. Its main gaps concern exact constraint/use alignment and object identity semantics, rather than a need for a larger abstraction.

## References

The supplied code is the basis for the architectural review. These primary C++ working-draft sections support the additional language details:

1. [Standard definition of `constructible_from`](https://eel.is/c++draft/concept.constructible)
2. [Type traits, including `is_constructible`](https://eel.is/c++draft/meta.unary.prop)
3. [Standard definition of `destructible`](https://eel.is/c++draft/concept.destructible)
4. [Requires-expressions and compound requirements](https://eel.is/c++draft/expr.prim.req)
5. [Standard definition of `convertible_to`](https://eel.is/c++draft/concept.convertible)
6. [Concept definitions and evaluation](https://eel.is/c++draft/temp.concept)
7. [Template parameters, defaults, and constrained-parameter syntax](https://eel.is/c++draft/temp.param)
8. [ROS executor API, including base-interface node registration](https://docs.ros2.org/latest/api/rclcpp/classrclcpp_1_1Executor.html)
9. [ROS component registration macro requirements](https://docs.ros2.org/latest/api/rclcpp_components/register__node__macro_8hpp.html)

These links point to the evolving working draft. The explanations here use the C++20 features present in the supplied header.
