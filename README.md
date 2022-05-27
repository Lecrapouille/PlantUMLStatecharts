# StateMachine

Python 3 tool for:
- Generating the C++ code of state machine from PlantUML statecharts.
- Generating some C++ unit tests to check your state machine.
- Do some basic verification if your state machine is well form.

```
./parser.py <plantuml statechart file> <output cpp file>
```

PlantUML statecharts syntax:
- `FromState --> ToState : event [ guard ] / action`
- `State : entry / action`
- `State : exit / action`
- `State : on event [ guard ] / action`
