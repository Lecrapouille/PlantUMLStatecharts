# Things that I did not understand about state machines before this project

In the beginning, I did not understand the differences between the
State/Transition diagram (STD) from the Structured Analysis for
Real-Time methodology and the UML statechart. In STD actions are
performed by transitions, while in UML actions are performed by
transitions or by states. I was confused.

What I understood after: in 1956 there were two kinds of state
machines: Moore — where actions were called from states — and Mealy —
where actions were called from transitions. They describe exactly the
same system; you can translate a Moore machine into a Mealy machine
and vice versa, without losing any expressiveness
([cite](https://www.itemis.com/en/yakindu/state-machine/documentation/user-guide/overview_what_are_state_machines)).
In 1984, Harel mixed the two syntaxes plus added some features
(composite, ...) and named the result statecharts. Finally UML
integrated statecharts in their standard.

Some tools, like the one explained in this
[document](https://cs.emis.de/LNI/Proceedings/Proceedings07/TowardEfficCode_3.pdf),
simplify the statechart graph to get a Mealy graph before generating
code. To keep the code simple to read, this translator does **not**
simplify the state machine; actions are made by states and by
transitions.

Another point of confusion was the difference between *action* and
*activity*. The action is instantaneous: it does not consume time
(contrary to the activity). The activity can be seen as a thread that
is preempted by any external event the state reacts to. The thread
is halted when the activity is done or when the system switches state.
Therefore an activity should not be seen as a periodic external
`update` event, since its code does not necessarily repeat.

# Rule of execution in Statecharts

Let's suppose the C++ code of the following state machine has been
generated with the C++ class name `Simple`.

![alt statemachine](../Simple.png)

- The system `Simple` enters `State1` (made active): `action7` is
  called (private method of the class `Simple` or any local function).
- The external `event3` (public method of the class `Simple` or any
  local function) may occur and when it does, if and only if `guard3`
  returns `true`, then `action3` is called.
- If `event1` is triggered and `guard1` returns `true` the system
  leaves `State1`: the exit `action8` is called followed by the
  transition `action1`.
- The system enters `State2` (made active): `action9` is called.
- `event5` may be triggered and when it happens `action5` is called.
- If `event2` is triggered then `State2` exit `action10` is called.
  Else if `event6` is triggered, the same `action10` is called.
- Note: when `event3` or `event5` are triggered, the entry and exit
  actions of the corresponding state are **not** called.
- An activity is started after the entry action and halted before the
  exit action.

If an output transition has no explicit event and no guard is given
(or the guard always returns `true`), and the activity has finished,
the transition is immediately taken in an atomic way. In our example,
if `event1`, `event2`, and `guard1` were not present, this would
create an infinite loop.

Events shall be mutually exclusive, since we are dealing with discrete
time events. Several events can occur during the delta time, but in
this API you call the event method directly and the state machine
reacts immediately, so the order is defined by the caller.
