# Details Design

The translation pipeline of the Python script is:

- The [Lark](https://github.com/lark-parser/lark) parser loads the
  [grammar](../../translator/statecharts.ebnf) file for parsing the
  PlantUML statechart file. This grammar does not come from an
  official source: PlantUML does not publish its own grammar; this
  one only manages a subset of their syntax.
- The [PlantUML statecharts](https://plantuml.com/fr/state-diagram)
  file is parsed by Lark and an Abstract Syntax Tree (AST) is
  produced.
- The AST is visited and a [Networkx](https://networkx.org/)
  directed graph is created (nodes are states, arcs are transitions).
  Events and actions are stored on the edges.
- The graph is visited to make some verifications (well-formedness)
  and then to generate the C++ code source. Unit tests are generated
  from graph cycles or paths from sources to sinks (what inputs make
  the FSM reach the desired state).

## Generated code shape

The state machine, like any graph structure (nodes are states and
edges are transitions) can be depicted by a matrix.

For example, the motor controller:

![alt motor](../Motor.png)

can be depicted in the following table (guards and actions are not
shown). In practice the table is usually sparse:

|                 | Set Speed  | Halt      | --        |
|-----------------|------------|-----------|-----------|
| IDLE            | STARTING   |           |           |
| STOPPING        |            |           | IDLE      |
| STARTING        | SPINNING   | STOPPING  |           |
| SPINNING        | SPINNING   | STOPPING  |           |

- The first column holds source states (origin).
- The first row holds events.
- For each event (column) each cell holds the destination state. The
  third column has no event, and the consequence is that the state is
  immediately transited.

## Implementation overview (legacy `StateMachine.hpp` backend)

- A private fixed-size array holds states and their entry/exit actions
  (pointers to private methods).
- Events are public methods. In each, a static lookup table (a
  `std::map` for the sparse side) maps transitions (source ⇒
  destination). The table also holds pointers to private methods for
  guards and actions. It is used by a generic private method
  implementing the FSM logic following the UML norm.
- The norm says that events shall be mutually exclusive (since we deal
  with discrete-time events, several events can occur during the delta
  time). Since the C++ API only offers public methods to trigger an
  event, mutual exclusion shall be enforced upstream by the caller.
- The code is based on this
  [project](https://www.codeproject.com/Articles/1087619/State-Machine-Design-in-Cplusplus-2)
  with several differences:
  - Curiously-recurring template pattern to use the child class and
    keep state enums external (internal enums were not possible).
  - Actions and guards are placed on transitions.
  - Transitions are parameters of the main function implementing the
    FSM logic.
  - Internal and external transitions are merged into a single
    function with an internal queue.

## New backend: the `statechart` C++ library

A modern alternative to the legacy `StateMachine.hpp` lives in the
[UML-Statechart-Framework-for-Java](https://github.com/lecrapouille/UML-Statechart-Framework-for-Java)
sister project (see the README of that repository). It re-uses
`statecharts.py` but rewrites the C++ emission to compose a
`statechart::Statechart` arena, hand out raw `State*` pointers via
`chart.create<T>(...)`, and wire transitions with
`statechart::Action`/`statechart::Guard` lambdas. There is no longer a
dependency on a single header template, and GoogleMock is replaced by
public counters that GoogleTest can assert on directly.
