# Simple PlantUML examples

These minimal PlantUML files illustrate the basic features of the
[statechart](../../../README.md) library exposed by the
[PlantUML translator](../../plantuml.md):

| File | Feature |
| --- | --- |
| `01_simple_state.plantuml` | start, named state, final state |
| `02_action_guard.plantuml` | guard + action on a transition |
| `03_entry_do_exit.plantuml` | entry / exit hooks on a state |
| `04_internal_event.plantuml` | `on event` internal transition (no exit/re-entry) |
| `05_event_parameters.plantuml` | event carrying typed parameters |
| `06_segmented_transition.plantuml` | two-segment transition via an intermediate junction-like state |

Each file is fed at build-time to `tools/translator/statecharts.py` and
the generated `.hpp` is compiled together with a tiny GoogleTest suite
under the `plantuml_<Name>` CTest targets.

## Not yet covered

The following advanced PlantUML constructs are accepted by the
`statechart` library but **not** by the current Python translator (which
is limited to flat FSMs):

- Hierarchical states (`state Foo { ... }`).
- Orthogonal regions (`--` / `||`).
- History pseudo-states (`H`, `H*`).
- Fork / join pseudo-states.
- Time-triggered transitions (`after(N)`).

Refer to the C++ unit tests under [`tests/`](../../../tests/) and to
[`doc/example.cpp`](../../example.cpp) for usage of those constructs at
the library level.
