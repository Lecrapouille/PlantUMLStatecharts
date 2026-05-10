# PlantUML Statecharts syntax

This tool does not pretend to parse the whole PlantUML syntax or to
implement the entire UML statecharts standard. Here is the basic
PlantUML statecharts syntax it can understand:

- `FromState --> ToState : event [ guard ] / action`
- `FromState -> ToState : event [ guard ] / action`
- `ToState <-- FromState : event [ guard ] / action`
- `ToState <- FromState : event [ guard ] / action`
- `State : entry / action`
- `State : exit / action`
- `State : on event [ guard ] / action` where `[ guard ]` is optional.
- `'` for single-line comment.
- The statecharts shall have one `[*]` as a source.
- Optionally `[*]` as a sink.

Note: `[ guard ]` and `/ action` are optional. You can add C++ code
(the less the better; you can complete with `'[code]` as depicted
below). The tool tolerates spaces between tokens `-->`, `:`, `[]`, and
`/`. The `event` is optional but, if present, it shall refer to a
valid C++ identifier of a function (so do not add logic operations).

Some sugar syntax extensions are accepted:

- `State : entering / action` alias for `State : entry / action`.
- `State : leaving / action` alias for `State : exit / action`.
- `State : comment / description` to add a C++ comment for the state
  in the generated code.
- `\n--\n action` alias for `/ action` to follow State-Transition
  Diagrams used in
  [Structured Analysis for Real Time](https://academicjournals.org/journal/JETR/article-full-text-pdf/07144DC1419)
  (also useful to force a carriage return on PlantUML diagrams).

## Code injection

The following directives start with the `'` keyword (a PlantUML
single-line comment, so they do not produce a syntax error) and inject
extra C++ code:

- `'[brief]` adds a comment for the generated state-machine class.
- `'[header]` adds code in the header of the file, before the class
  of the state machine. You can include other C++ files and create or
  define functions.
- `'[footer]` adds code in the footer of the file, after the class of
  the state machine.
- `'[param]` declares arguments to pass to the state-machine C++
  constructor. Commas are added. One argument per line.
- `'[cons]` initialises an argument before the body of the
  constructor. One entry per line.
- `'[init]` is C++ code called by the constructor or by the `reset()`
  function.
- `'[code]` lets you add member variables or member functions.
- `'[test]` lets you add C++ code for unit tests.
