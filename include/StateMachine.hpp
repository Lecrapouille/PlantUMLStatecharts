// ############################################################################
// MIT License
//
// Copyright (c) 2022 Quentin Quadrat
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
// ############################################################################

#ifndef STATE_MACHINE_HPP
#  define STATE_MACHINE_HPP

#  include <map>
#  include <queue>
#  include <cassert>
#  include <stdlib.h>

//-----------------------------------------------------------------------------
//! \brief Verbosity activated in debug mode.
//-----------------------------------------------------------------------------
#  include <cstdio>
#  if defined(FSM_DEBUG)
#    define LOGD printf
#  else
#    define LOGD(...)
#  endif
#  define LOGE printf

//-----------------------------------------------------------------------------
//! \brief Return the given state as raw string (they shall not be free).
//! \note implement this function inside the C++ file of the derived class.
//-----------------------------------------------------------------------------
template<class STATES_ID>
const char* stringify(STATES_ID const state);

// *****************************************************************************
//! \brief Base class for depicting and running small Finite State Machine (FSM)
//! by implementing a subset of UML statechart. See this document for more
//! information about them: http://niedercorn.free.fr/iris/iris1/uml/uml09.pdf
//!
//! This class is not made for defining hierarchical state machine (HSM). It
//! also does not implement composites, history, concurrent parts of the FSM.
//! This class is fine for small Finite State Machine (FSM) and is limited due
//! to memory footprint (therefore no complex C++ designs, no dynamic containers
//! and few virtual methods). The code is based on the following link
//! https://www.codeproject.com/Articles/1087619/State-Machine-Design-in-Cplusplus-2
//! For bigger state machines, please use something more robust such as Esterel
//! SyncCharts or directly the Esterel language
//! https://www.college-de-france.fr/media/gerard-berry/UPL8106359781114103786_Esterelv5_primer.pdf
//!
//! This class holds the list of states \c State and the currently active state.
//! Each state holds actions to perform as function pointers 'on entering', 'on
//! leaving', 'on event' and 'do activity'.
//!
//! A state machine is depicted by a graph structure (nodes: states; arcs:
//! transitions) which can be represented by a matrix (states / events) usually
//! sparse. For example the following state machine, in plantuml syntax:
//!
//! @startuml
//! [*] --> Idle
//! Idle --> Starting : set speed
//! Starting --> Stopping : halt
//! Starting -> Spinning : set speed
//! Spinning -> Stopping: halt
//! Spinning --> Spinning : set speed
//! Stopping -> Idle
//! @enduml
//!
//! Can be depicted by the following matrix:
//! +-----------------+------------+-----------+-----------+
//! | States \ Event  | Set Speed  | Halt      |           |
//! +=================+============+===========+===========+
//! | IDLE            | STARTING   |           |           |
//! +-----------------+------------+-----------+-----------+
//! | STOPPING        |            |           | IDLE      |
//! +-----------------+------------+-----------+-----------+
//! | STARTING        | SPINNING   | STOPPING  |           |
//! +-----------------+------------+-----------+-----------+
//! | SPINNING        | SPINNING   | STOPPING  |           |
//! +-----------------+------------+-----------+-----------+
//!
//! The first column contains all states. The first line contains all events.
//! Each column depict a transition: given the current state (i.e. IDLE) and a
//! given event (i.e. Set Speed) the next state of the state machine will be
//! STARTING. Empty cells are forbidden transitions.
//!
//! This class does not hold directly tables for transitioning origin state to
//! destination state when an external event occured (like done in boost
//! lib). Instead, each external event shall be implemented as member function
//! in the derived FSM class and in each member function shall implement the
//! transition table.
//!
//! \tparam FSM the concrete Finite State Machine deriving from this base class.
//! In this class you shall implement external events as public methods,
//! reactions and guards as private methods, and set the first column of the
//! matrix and their guards/reactions in the constructor method. On each event
//! methods, you shall define the table of transition (implicit transition are
//! considered as ignoring the event).
//!
//! \tparam STATES_ID enumerate for giving an unique identifier for each state.
//! In our example:
//!   enum StatesID { IDLE = 0, STOPPING, STARTING, SPINNING,
//!                   IGNORING_EVENT, CANNOT_HAPPEN, MAX_STATES };
//!
//! The 3 last states are mandatory: in the matrix of the control motor of our
//! previous example, holes are implicitely IGNORING_EVENT, but the user can
//! explicitely set to CANNOT_HAPPEN to trap the whole system. Other state enum
//! shall be used to defined the table of states \c m_states which shall be
//! filled with these enums and pointer functions such as 'on entering' ...
//!
//! Transition, like states, can do reaction and have guards as pointer
//! functions.
// *****************************************************************************
template<typename FSM, class STATES_ID>
class StateMachine
{
public:

    //! \brief Pointer method with no argument and returning a boolean.
    using bFuncPtr = bool (FSM::*)();
    //! \brief Pointer method with no argument and returning void.
    using xFuncPtr = void (FSM::*)();

    //--------------------------------------------------------------------------
    //! \brief Class depicting a state of the state machine and hold pointer
    //! methods for each desired action to perform. In UML states are like
    //! Moore state machine: states can do action.
    //--------------------------------------------------------------------------
    struct State
    {
        //! \brief Call the "on entry" callback when entering for the first time
        //! (AND ONLY THE FIRST TIME) in the state. Note: the transition guard
        //! can prevent calling this function.
        xFuncPtr entering = nullptr;
        //! \brief Call the "on leaving" callback when leavinging for the first
        //! time (AND ONLY THE FIRST TIME) the state. Note: the guard can
        //! prevent calling this function.
        xFuncPtr leaving = nullptr;
    };

    //--------------------------------------------------------------------------
    //! \brief Class depicting a transition from a source state to a destination
    //! state. A transition occurs when an event has occured. In UML,
    //! transitions are like Mealey state machine: transition can do action.
    //--------------------------------------------------------------------------
    struct Transition
    {
        //! \brief State of destination
        STATES_ID destination = STATES_ID::IGNORING_EVENT;
        //! \brief The condition validating the event and therefore preventing
        //! the transition to occur.
        bFuncPtr guard = nullptr;
        //! \brief The action to perform when transitioning to the destination
        //! state.
        xFuncPtr action = nullptr;
    };

    //! \brief Define the type of container holding all stated of the state
    //! machine.
    using States = std::array<State, STATES_ID::MAX_STATES>;
    //! \brief Define the type of container holding states transitions. Since
    //! a state machine is generally a sparse matrix we use red-back tree.
    using Transitions = std::map<STATES_ID, Transition>;

    //--------------------------------------------------------------------------
    //! \brief Default constructor. Pass the number of states the FSM will use,
    //! set the initial state and if mutex shall have to be used.
    //! \param[in] initial the initial state to start with.
    //--------------------------------------------------------------------------
    StateMachine(STATES_ID const initial) // FIXME should be ok for constexpr
        : m_current_state(initial), m_initial_state(initial)
    {
        // FIXME static_assert not working
        assert(initial < STATES_ID::MAX_STATES);
    }

    //--------------------------------------------------------------------------
    //! \brief Restore the state machin to its initial state.
    //--------------------------------------------------------------------------
    inline void reset()
    {
        m_current_state = m_initial_state;
        std::queue<Transition const*> empty;
        std::swap(m_nesting, empty);
    }

    //--------------------------------------------------------------------------
    //! \brief Return the current state.
    //--------------------------------------------------------------------------
    inline STATES_ID state() const
    {
        return m_current_state;
    }

    //--------------------------------------------------------------------------
    //! \brief Return the current state as string (shall not be free'ed).
    //--------------------------------------------------------------------------
    inline const char* c_str() const
    {
        return stringify(m_current_state);
    }

    //--------------------------------------------------------------------------
    //! \brief Internal transition: jump to the desired state from internal
    //! event. This will call the guard, leaving actions, entering actions ...
    //! \param[in] transitions the table of transitions.
    //--------------------------------------------------------------------------
    inline void transition(Transitions const& transitions)
    {
        auto const& it = transitions.find(m_current_state);
        if (it != transitions.end())
        {
            transition(&it->second);
        }
        else
        {
            LOGD("[FSM INTERNALS] Ignoring external event\n");
            //LOGE("[FSM INTERNALS] Unknow transition. Aborting!\n");
            //exit(EXIT_FAILURE);
        }
    }

protected:

    //--------------------------------------------------------------------------
    //! \brief Internal transition: jump to the desired state from internal
    //! event. This will call the guard, leaving actions, entering actions ...
    //! \param[in] transitions the table of transitions.
    //--------------------------------------------------------------------------
    void transition(Transition const* transition);

protected:

    //! \brief Container of states.
    States m_states;

    //! \brief Current active state.
    STATES_ID m_current_state;

private:

    //! \brief Save the initial state need for restoring initial state.
    STATES_ID m_initial_state;
    //! \brief Temporary variable saving the nesting state (needed for internal
    //! event).
    std::queue<Transition const*> m_nesting;
};

//------------------------------------------------------------------------------
template<class FSM, class STATES_ID>
void StateMachine<FSM, STATES_ID>::transition(Transition const* tr)
{
#if defined(THREAD_SAFETY)
    // If try_lock failed it is not important: it just means that we have called
    // an internal event from this method and internal states are still
    // protected.
    m_mutex.try_lock();
#endif

    // Reaction from internal event (therefore coming from this method called by
    // one of the action functions: memorize and leave the function: it will
    // continue thank to the while loop. This avoids recursion.
    if (m_nesting.size())
    {
        LOGD("[FSM INTERNALS] Internal event. Memorize state %s\n",
             stringify(tr->destination));
        m_nesting.push(tr);
        if (m_nesting.size() >= 16u)
        {
            LOGE("[FSM INTERNALS] Infinite loop detected. Abort!\n");
            exit(EXIT_FAILURE);
        }
        return ;
    }

    m_nesting.push(tr);
    Transition const* transition;
    do
    {
        // Consum the current state
        transition = m_nesting.front();

        LOGD("[FSM INTERNALS] React to event from state %s\n",
             stringify(m_current_state));

        // Forbidden event: kill the system
        if (transition->destination == STATES_ID::CANNOT_HAPPEN)
        {
            LOGE("[FSM INTERNALS] Forbidden event. Aborting!\n");
            exit(EXIT_FAILURE);
        }

        // Do not react to this event
        else if (transition->destination == STATES_ID::IGNORING_EVENT)
        {
            LOGD("[FSM INTERNALS] Ignoring external event\n");
            return ;
        }

        // Unknown state: kill the system
        else if (transition->destination >= STATES_ID::MAX_STATES)
        {
            LOGE("[FSM INTERNALS] Unknown state. Aborting!\n");
            exit(EXIT_FAILURE);
        }

        // Reaction: call the member function associated to the current state
        StateMachine<FSM, STATES_ID>::State const& cst = m_states[m_current_state];
        StateMachine<FSM, STATES_ID>::State const& nst = m_states[transition->destination];

        // Call the guard
        bool guard_res = (transition->guard == nullptr);
        if (!guard_res)
        {
            LOGD("[FSM INTERNALS] Call the guard %s -> %s\n",
                 stringify(m_current_state), stringify(transition->destination));
            guard_res = (static_cast<FSM*>(this)->*transition->guard)();
        }

        if (!guard_res)
        {
            LOGD("[FSM INTERNALS] Transition refused by the %s guard. Stay"
                 " in state %s\n", stringify(transition->destination),
                 stringify(m_current_state));
        }
        else
        {
            // The guard allowed the transition to the next state
            LOGD("[FSM INTERNALS] Transitioning to new state %s\n",
                 stringify(transition->destination));

            // Transition
            STATES_ID previous_state = m_current_state;
            m_current_state = transition->destination;
            if (transition->action != nullptr)
            {
                LOGD("[FSM INTERNALS] Call the transition %s -> %s action\n",
                     stringify(previous_state), stringify(transition->destination));
                (static_cast<FSM*>(this)->*transition->action)();
            }

            // Transitioning to a new state ?
            if (previous_state != transition->destination)
            {
                if (cst.leaving != nullptr)
                {
                    LOGD("[FSM INTERNALS] Call the state %s 'on leaving' action\n",
                         stringify(previous_state));

                    // Do reactions when leaving the current state
                    (static_cast<FSM*>(this)->*cst.leaving)();
                }

                if (nst.entering != nullptr)
                {
                    LOGD("[FSM INTERNALS] Call the state %s 'on entry' action\n",
                         stringify(transition->destination));

                    // Do reactions when entring into the new state
                    (static_cast<FSM*>(this)->*nst.entering)();
                }
            }
            else
            {
                LOGD("[FSM INTERNALS] Was previously in this mode: no "
                     "actions to perform\n");
            }
        }

        m_nesting.pop();
    } while (!m_nesting.empty());

#if defined(THREAD_SAFETY)
    m_mutex.unlock();
#endif
}

#endif // STATE_MACHINE_HPP
