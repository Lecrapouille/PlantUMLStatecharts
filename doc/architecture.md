# Architecture and design notes

This page documents the C++20 port of the original Java framework. It assumes that you read [`statecharts.md`](statecharts.md) and [`getting-started.md`](getting-started.md) for the high-level concepts.

## Source layout

```bash
include/statechart/   public headers (forward.hpp + per-class headers)
src/                  library implementation (.cpp files)
doc/example.cpp       runnable port of the "Getting started" example
doc/examples/         PlantUML examples consumed by the translator
tests/                GoogleTest port of the SemanticTest / MetadataPersistanceTest suites
tools/translator/     Python translator from PlantUML to C++ (statecharts.py)
CMakeLists.txt        root CMake configuration (project name: statechart)
```

The library exposes a single `statechart::` namespace. The headers are
strictly `#pragma once` + forward declarations; full definitions live
in the corresponding `.cpp` files so cycles between `State`, `Context`,
`Statechart`, `Transition`, etc. never surface in the headers.

## Ownership model

`Statechart` is the *arena* for every object spawned in its scope:

* `chart.create<T>("name", parent, args...)` allocates a `T` (which must
  derive from `State`), records it in an internal lookup map, and
  returns a non-owning pointer.
* `chart.createTransition(...)` and `chart.createEvent<E>(...)` mirror
  the same convention for `Transition` / `Event` subclasses.
* Destroying the `Statechart` reclaims every state, transition and
  event in one shot, with deterministic order.

This avoids the original Java reliance on the GC while still letting
client code pass plain pointers around — the lifetime contract is
"valid as long as the chart is alive".

## Threading

The library spins a single-threaded executor for the event queue and a
dedicated thread for the timeout queue. The single-threaded design is a
deliberate match for the Java reference, which also serialises async
events per `ThreadPoolExecutor`. Keeping FIFO semantics avoids ordering
surprises between `dispatchAsynchron` and `start`.

`Metadata` exposes a `std::recursive_mutex`; it is the C++ equivalent
of `synchronized(data)` in the Java source. `dispatch()` takes that
mutex automatically; user code only needs it when reading the active
states from outside a callback.

## Deviations from the Java API

The biggest deviations are intentional and aim at a more idiomatic C++:

* `Action` and `Guard` are `std::function` aliases, so any callable
  (lambda, functor, plain function) works:

  ```cpp
  using Action = std::function<void(Metadata&, Parameter&)>;
  using Guard  = std::function<bool(Metadata&, Parameter&)>;
  ```

* `Statechart` owns every state, transition and trigger event via the
  arena described above. Use the factory methods
  `chart.create<State>("name", parent)`,
  `chart.createTransition(start, end, ...)` and
  `chart.createEvent<MyEvent>(...)` instead of free `new`.

* The framework-internal `activate` / `deactivate` / `dispatch` methods
  are `public` instead of package-private — C++ does not have Java's
  package-private visibility, so the cross-class internal calls within
  the framework simply use `public`. They are documented as
  "framework-internal entry points"; user code should keep using
  `Statechart::start()` and `Statechart::dispatch()`.

* `dynamic_cast<PseudoState*>(s)` / `dynamic_cast<FinalState*>(s)` is
  used instead of Java's `instanceof` to introspect the type of a state
  at run-time.

## Building

Requirements: a C++20 compiler (gcc 12+, clang 15+, MSVC 19.30+) and
CMake 3.20+.

```sh
cmake -S . -B build
cmake --build build -j
ctest --test-dir build --output-on-failure
./build/statechart_example
```

The relevant CMake options are:

| Option | Default | Effect |
| --- | --- | --- |
| `STATECHART_BUILD_TESTS` | `ON` | Build the GoogleTest suite (`statechart_tests`). |
| `STATECHART_BUILD_EXAMPLE` | `ON` | Build `statechart_example` from `doc/example.cpp`. |
| `STATECHART_BUILD_PLANTUML_TESTS` | `ON` | Run the Python translator at build-time on every `doc/examples/**/*.plantuml` and add a `plantuml_<Name>` CTest target per example. Requires Python 3 with `lark` and `networkx` (see [`tools/translator/requirements.txt`](../tools/translator/requirements.txt)). |

`FetchContent` pulls GoogleTest automatically when either test target is enabled.

A minimal CMake snippet to consume the library from another project:

```cmake
add_subdirectory(third_party/statechart)
target_link_libraries(my_target PRIVATE statechart::statechart)
```
