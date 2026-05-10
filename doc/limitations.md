# Limitations: what the tool cannot offer to you

- The tool only generates C++ code. You can help by contributing
  back-ends for other languages.
- The tool currently parses simple **Finite State Machines (FSM)**
  only. Hierarchical State Machines (HSM) are still on the roadmap.
- For FSM, the tool does not parse fork, concurrent states, composite
  states, history pseudo-states.
- For FSM, `do / activity` and `after(X ms)` are not yet managed.
- The tool does not manage multi-edges (several transitions sharing
  the same origin **and** destination state). Consequently, you cannot
  add several `on event` lines on the same state.
- I am not a UML expert, so this tool probably does not strictly
  follow UML standards. It has not yet been used in real production
  code.
- No formal proof: the tool cannot check that the output transitions
  from a state are mutually exclusive or that some branches are
  unreachable. This is currently too complex for me to develop (any
  help is welcome): we would need to parse and understand C++ code.
  For example, in the [RichMan](../RichMan.png) diagram, if the
  initial count of quarters starts negative, you will be stuck in
  the state `CountQuarter`. Similarly, events on outgoing transitions
  shall be mutually exclusive but the tool cannot parse C++ logic to
  check it. Likewise for unit tests, the tool cannot pick "good"
  values for guards on its own.
- Does not give 100% of compilable C++ code source out of the box: it
  depends on the C++ in your guards and actions. They should be
  simple valid C++ code. The structural part of the generated state
  machine is functional and you should not have to modify it, but you
  may need to clean up your guards/actions or add member variables to
  complete compilation.
