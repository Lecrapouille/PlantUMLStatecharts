# Medium PlantUML examples

Real-world flat finite state machines reused from the original
[PlantUMLStatecharts](https://github.com/Lecrapouille/PlantUMLStatecharts)
project, ported to the in-tree `statechart` library.

| File | Description |
| --- | --- |
| `Motor.plantuml` | DC-motor controller (idle/start/spinning/stop) with `setSpeed` and `halt` events. |
| `Gumball.plantuml` | Gumball distributor with constructor parameter. |
| `RichMan.plantuml` | Quarters counter with cycles between three states. |
| `SimpleFSM.plantuml` | Two-state machine illustrating every supported PlantUML directive. |
| `Triggers.plantuml` | Two transitions sharing the same event but separated by guards. |
| `EthernetBox.plantuml` | Wifi pairing state machine for a set-top box. |
| `FixBadSwitch2.plantuml` | Deterministic version of the BadSwitch counter-example. |
| `LaneKeeping.plantuml` | Lane-keeping assistant FSM with several boolean flags. |

Each file is fed at build-time to `tools/translator/statecharts.py` and
the generated `.hpp` is compiled together with a tiny GoogleTest suite
under the `plantuml_<Name>` CTest targets.

## Excluded examples

Examples that exercise composite states (`state Foo { ... }`) or
orthogonal regions (`--`/`||`) are not yet supported by the translator
and remain available in the original
[PlantUMLStatecharts](https://github.com/Lecrapouille/PlantUMLStatecharts)
repository:

- `SimpleComposite`, `SimpleOrthogonal`, `ComplexComposite`, `Pompe`
  (require hierarchical/orthogonal support).
- `BadSwitch1`, `BadSwitch2`, `InfiniteLoop` (intentionally
  ill-formed; would loop forever or take a non-deterministic path).
- `DigitalWatch`, `SelfParking` (rely on companion code or pseudo-code
  that is not C++-compilable as-is).
