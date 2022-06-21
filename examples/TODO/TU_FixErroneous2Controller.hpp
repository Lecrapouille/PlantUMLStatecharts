// This file as been generated the June 21, 2022
// This code generation is still experimental. Some border cases may not be correctly managed!

#ifndef FIXERRONEOUS2CONTROLLER_HPP
#  define FIXERRONEOUS2CONTROLLER_HPP

#  include "StateMachine.hpp"

//********************************************************************************
//! \brief States of the state machine.
//********************************************************************************
enum FixErroneous2ControllerStates
{
    // Client states:
    CONSTRUCTOR,
    A,
    B,
    C,
    D,
    // Mandatory internal states:
    IGNORING_EVENT, CANNOT_HAPPEN, MAX_STATES
};

//********************************************************************************
//! \brief Convert enum states to human readable string.
//********************************************************************************
static inline const char* stringify(FixErroneous2ControllerStates const state)
{
    static const char* s_states[] =
    {
        [FixErroneous2ControllerStates::CONSTRUCTOR] = "[*]",
        [FixErroneous2ControllerStates::A] = "A",
        [FixErroneous2ControllerStates::B] = "B",
        [FixErroneous2ControllerStates::C] = "C",
        [FixErroneous2ControllerStates::D] = "D",
    };

    return s_states[state];
};

//********************************************************************************
//! \brief State machine concrete implementation.
//********************************************************************************
class FixErroneous2Controller : public StateMachine<FixErroneous2Controller, FixErroneous2ControllerStates>
{
public: // Constructor and external events

    //----------------------------------------------------------------------------
    //! \brief Default constructor. Start from initial state and call it actions.
    //----------------------------------------------------------------------------
    FixErroneous2Controller() : StateMachine(FixErroneous2ControllerStates::CONSTRUCTOR)
    {
        m_states[FixErroneous2ControllerStates::CONSTRUCTOR] =
        {
            .entering = &FixErroneous2Controller::onEnteringStateCONSTRUCTOR,
        };
        m_states[FixErroneous2ControllerStates::A] =
        {
            .entering = &FixErroneous2Controller::onEnteringStateA,
        };
    }

virtual ~FixErroneous2Controller() = default;

    //----------------------------------------------------------------------------
    //! \brief Reset the state machine.
    //----------------------------------------------------------------------------
    void reset()
    {
        StateMachine::reset();
        onEnteringStateCONSTRUCTOR();
    }

    //----------------------------------------------------------------------------
    //! \brief External event.
    //----------------------------------------------------------------------------
    void event()
    {
        LOGD("[EVENT %s]\n", __func__);

        static Transitions s_transitions =
        {
            {
                FixErroneous2ControllerStates::A,
                {
                    FixErroneous2ControllerStates::D,
                    nullptr,
                    nullptr,
                },
            },
        };

        transition(s_transitions);
    }

private: // Guards and reactions

    //----------------------------------------------------------------------------
    //! \brief Guard the transition from state A to state B.
    //----------------------------------------------------------------------------
    bool onGuardingTransitionA_B()
    {
        const bool guard = (guard1());
        LOGD("[GUARD A --> B: guard1()] result: %s\n",
             (guard ? "true" : "false"));
        return guard;
    }

    //----------------------------------------------------------------------------
    //! \brief Guard the transition from state A to state C.
    //----------------------------------------------------------------------------
    bool onGuardingTransitionA_C()
    {
        const bool guard = (guard2());
        LOGD("[GUARD A --> C: guard2()] result: %s\n",
             (guard ? "true" : "false"));
        return guard;
    }

    //----------------------------------------------------------------------------
    //! \brief Do the action when entering the state [*].
    //----------------------------------------------------------------------------
    void onEnteringStateCONSTRUCTOR()
    {
        LOGD("[ENTERING STATE [*]]\n");
                if (onGuardingTransitionA_B())
        {
            LOGD("[STATE A] Internal transition to state B\n");
            static StateMachine<FixErroneous2Controller, FixErroneous2ControllerStates>::Transition tr =
            {
                .destination = FixErroneous2ControllerStates::B,
                .guard = &FixErroneous2Controller::onGuardingTransitionA_B,
            };
            transition(&tr);
            return ;
        }
        if (onGuardingTransitionA_C())
        {
            LOGD("[STATE A] Internal transition to state C\n");
            static StateMachine<FixErroneous2Controller, FixErroneous2ControllerStates>::Transition tr =
            {
                .destination = FixErroneous2ControllerStates::C,
                .guard = &FixErroneous2Controller::onGuardingTransitionA_C,
            };
            transition(&tr);
            return ;
        }
    }

    //----------------------------------------------------------------------------
    //! \brief Do the action when entering the state A.
    //----------------------------------------------------------------------------
    void onEnteringStateA()
    {
        LOGD("[ENTERING STATE A]\n");
                if (onGuardingTransitionA_B())
        {
            LOGD("[STATE A] Internal transition to state B\n");
            static StateMachine<FixErroneous2Controller, FixErroneous2ControllerStates>::Transition tr =
            {
                .destination = FixErroneous2ControllerStates::B,
                .guard = &FixErroneous2Controller::onGuardingTransitionA_B,
            };
            transition(&tr);
            return ;
        }
        if (onGuardingTransitionA_C())
        {
            LOGD("[STATE A] Internal transition to state C\n");
            static StateMachine<FixErroneous2Controller, FixErroneous2ControllerStates>::Transition tr =
            {
                .destination = FixErroneous2ControllerStates::C,
                .guard = &FixErroneous2Controller::onGuardingTransitionA_C,
            };
            transition(&tr);
            return ;
        }
    }

public:

    virtual bool guard1() = 0;
    virtual bool guard2() = 0;
};

#endif // FIXERRONEOUS2CONTROLLER_HPP
