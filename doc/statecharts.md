# Introduction to statecharts

If you are new to the statecharts it may be hard to understand the syntax and especially the semantics. This short introduction should help you to get into statecharts and learn how to use them. All elements which are supported by this framework are described here. The original text can be found in [3] (german only).

## States and Actions

Statecharts are represented as directed graphs and therefore have vertices and (directed) edges. The vertices are the states an object can reach. Edges are changes of the state, the so-called _transitions_. States are represented through a rectangle with rounded edges and can have a name and actions. Three kind of state-actions are available:

* The _entry-action_ is executed when the state is activated.
* The _do-action_ is executed after finishing the entry-action.
* The _exit-action_ is executed when the state is deactivated.

A special type of state are the _pseudo-states_. They exists only for modelling and are not real states of the object. The statechart **must not** stay or can execute actions in these pseudostates. The main entry activated when the statechart begins the event-handling is the _start-state_ which is a pseudostate and only have outgoing transitions. The _final-state_ instead is a real state and only have incoming transitions.

![g1.png](images/g1.png)

## Transitions

### Events

Changing a state normally is triggered with events. An event is the result of an arbitrary action from the system or the environment around the system. Events are not defined in a special way. In the UML specification are four event-types described, the most important ones are:

* The _signal-event_ is triggered by the surrounding environment.
* The _time-event_ is triggered by the statechart itself.

Every state can have a completion-transition which is a transition without an event. If the state has no such transition (all transitions are triggered by events) the object stays in this state until an appropriate event ca be handled by an outgoing transition. All events are only handled by the current active state. If the event cannot be handled by the state, the event is discarded. For the end-transition the finishing of the states exit-action is interpreted as the trigger.

### Guards and Actions

A transition can have a guard and an action besides the event. The first is marked as `[guard]` the latter as `/action`. Guards are used to make sure that the transition only can trigger if the evaluation of the guard is true. Therefore it is possible  to create transitions with the same event and different guards. Depending on the guard different actions can be executed or target states reached.

![g2.png](images/g2.png)

While modelling you have to make sure that the model is deterministic. So it is not allowed to add outgoing transitions to the state which can trigger both on an event.

### Time-triggered transitions

The time event is marked at the transition with the keyword after `(x)`. This defines a special kind of transition, the so-called time-triggered transition. `x` is the time the source state must be active before the transition can trigger (if the optional guard evaluation is true). Counting the time begins when an state is activated.

![g3.png](images/g3.png)

### Segmented transitions

Another aspect of statecharts are the segmented transitions. They are used if you want to concatenate several transitions e.g. to execute an action with each subtransition. The other usefull commitment of segmented transitions is the modelling of branches. All subtransitions are concatenated with the junction point pseudostate which is displayed as a small black circle in the diagram.

One important property of segmented transitions is that they are always atomic. Therefore the transition triggers either complete or not at all. That means before a statechange occurs the segmented transition must check if there exists a permitted path to the next real state. But there is another noteworthiness to mention: Only the first segment of the transition can contain an event as a trigger. Otherwise all segments can contain guards and actions.

![g4.png](images/g4.png)

## Hierarchical states

Complex systems often requires abstraction of an actual situation and specify the concrete behaviour in a separate step later on. In statecharts the usage of hierarchical states, also known as or-state, can be used to decompose a complex state into substates which describe the behaviour in detail. Once the object reaches this composite or-state, exactly one substate is activated automatically and only one substate is active at the time (which explains the name or-state). This interlocking implies new particularities which will be described now.

### Start- and final-states

Inside an or-state it is essential to know which substate to activate when the parent state is activated and when the or-state is finished respectivly. This information is modelled with the already known start- and final-states. The existence of these pseudostates is not mandatory in every case. Why will be cleared in the next paragraph.

### Entering and leaving the hierarchical state

Two types can be described how a complex state may be activated:

* An incoming transition ends at the border of the or-state. In this case the existence of the start-state is mandatory.
* An incoming transition ends at a substate, it crosses the border of the or-state. Therefore the start-state is not mandatory because the hierarchical state knows the first active substate by the target of the transition.

Leaving a hierarchical state is analogue:

* The state can be deactivated through an outgoing (end-)transition. If this transition has no trigger the finishing of the composite state is the signal to trigger the end-transition. In such a case a final-state is mandatory.
* The state can be deactivated through an outgoing transition which source is a substate and target is a state outside the or-state. In such a case a final-state is not mandatory.

### State transitions

Transitions within hierarchies brings up two questions we need a semantics for. At first, what happens with outgoing event-triggered transitions from the or-state? The semantics is that the object is in exactly one substate when the or-state is active. So it is nessecary that every substate can handle this event as well. To realize this semantics every event-triggered outgoing transition of the hierarchical-state is inherited by all substates. In other words, every substate handles all outgoing  event-triggered transitions of its parent states which are on the path from the state to the root node of the hierarchy-tree.

This semantics will cause the next question: What happens if a substate "overrides" an outgoing transition with the same event? In this case more than one transition is able to fire. That means a rule is nessecary to prioritize transitions: `t1` is an outgoing transition of the state `s1` and `s1` is a transitively reachable substate of `s2`. `t2` is an outgoing transition of `s2` and handles the same event as `t1`. In this case the inner transition `t1` has a higher priority as `t2`. This rule assures that always the lowest transition in the hierarchy tree triggers.

![g5.png](images/g5.png)

### History states

Many Systems require to know the last configuration of a complex state when it was deactivated. With this information it is possible to continue in the same configuration when reactivating the complex-state. This information is modelled using history-pseudostates in hierarchical states. History is shown as `H` or `H*` in the diagram and are categorized as follow:

* The shallow history `H` stores the last active substate.
* The deep history `H*` stores all active substates on the path from the node to the leaf in the hierarchy tree.

One difference between classic statecharts by David Harel and UML statecharts is that in latter you must specify a start-transition from the history-state to the state which should be activated if no history is available. This is the case when the or-state has never been active before. If a history is available, the stored substate is activated.

![g6.png](images/g6.png)

## Concurrent states

The second improvement of statecharts is the possibility to model concurrency. A concurrent state must have at least two parallel active substates. These are the regions of the and-state. In the diagram these regions are separated with a dashed line. Concurrency implies new conceptual consequences which are described now.

### Regions

Regions are described with hierarchical states, therefore the semantics introduced above applies here as well. Basically all regions are active as soon as the and-state is activated. They are some kind of processes which are running inside the concurrent state.

It not possible that several regions are "deactivated" while others aren´t. Incoming events are always handled by all regions which means that perhaps more than one transition are able to fire. Namely up to region count transitions. Like in or-states event triggered outgoing transitions are inherited by all regions (and thereby all substates). The priority rule for fireing transitions is applied here as well.

![g7.png](images/g7.png)

### Entering and leaving the concurrent state

When entering a concurrent state all regions must be activated and vice versa. As in hierarchical states two cases can be described.

* The incoming transition ends at the and-state. In this case all regions must have a start-state.
* The incoming transition ends at a substate of exatly one region. Then the and-state is activated imlicit at this substate. All other regions are activated at there start-states. Therefore n-1 start-states are nessecary.

Deactivating is analogue:

* If all regions have activated their end-state the completion-transition can trigger. The end-states are synching the regions.
* If a transition of a substate fires and the target state is outside the and-state, the concurrent state is deactivated implicit. All other regions must be deactivated immediately as well. This semantics applies also for inherited event-triggered transition.

![g8.png](images/g8.png)

### Complex transitions

Two cases of activating a concurrent-state were described above: implicit and explicit. The first all n regions need start-states where latter `n-1` start-states are needed. But what happens when `n-m` regions should be activated (where `1 < m < n`). E.g. this is nessecary if the start-states should describe the default entry behaviour and for some special case the configuration of the and-state should be different when activating.

To model this behaviour complex transitions were introduced. They split the control flow. One incoming transition is split into maximum one transition per region with a target substate in this region. An analogue case can be described for leaving the and-state. A complex transition can have these two semantics:

* Split one transition into at least two transitions. All regions which are not allowed for the incoming transitions are activated at their start-states automatically.
* Synchronising different regions for leaving the and-state when some substates are activated. All regions which are not allowed for the outgoing transitions are deactivated automatically.

The diagram provides two kind of pseudo-states for this behaviour. Both are shown as a small black bar. This bar represents the fork-state if it is a `1:n`-mapping, so one transition is split into n. If it is `n:1`-mapping, that means `n` incoming transitions are synchronised into one. This kind is called the join-state.

![g9.png](images/g9.png)
