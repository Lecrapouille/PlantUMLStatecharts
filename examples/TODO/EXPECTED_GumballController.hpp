// This file as been generated the June 16, 2022
// This code generation is still experimental. Some border cases may not be correctly managed!

#ifndef GUMBALLCONTROLLER_HPP
#  define GUMBALLCONTROLLER_HPP

#  include "StateMachine.hpp"

//********************************************************************************
//! \brief States of the state machine.
//********************************************************************************
enum GumballControllerStates
{
    // Client states:
    CONSTRUCTOR,
    NOQUARTER,
    OUTOFGUMBALLS,
    HASQUARTER,
    GUMBALLSOLD,
    // Mandatory internal states:
    IGNORING_EVENT, CANNOT_HAPPEN, MAX_STATES
};

//********************************************************************************
//! \brief Convert enum states to human readable string.
//********************************************************************************
static inline const char* stringify(GumballControllerStates const state)
{
    static const char* s_states[] =
    {
        [GumballControllerStates::CONSTRUCTOR] = "[*]",
        [GumballControllerStates::NOQUARTER] = "NOQUARTER",
        [GumballControllerStates::OUTOFGUMBALLS] = "OUTOFGUMBALLS",
        [GumballControllerStates::HASQUARTER] = "HASQUARTER",
        [GumballControllerStates::GUMBALLSOLD] = "GUMBALLSOLD",
    };

    return s_states[state];
};

//********************************************************************************
//! \brief State machine concrete implementation.
//********************************************************************************
class GumballController : public StateMachine<GumballController, GumballControllerStates>
{
public: // Constructor and external events

    //----------------------------------------------------------------------------
    //! \brief Default constructor. Start from initial state and call it actions.
    //----------------------------------------------------------------------------
    GumballController(int g)
       : StateMachine(GumballControllerStates::CONSTRUCTOR), gumballs(g)
    {
        m_states[GumballControllerStates::CONSTRUCTOR] =
        {
            .entering = &GumballController::onEnteringStateCONSTRUCTOR,
        };
        m_states[GumballControllerStates::GUMBALLSOLD] =
        {
            .entering = &GumballController::onEnteringStateGUMBALLSOLD,
        };
        //gumballs = 1;
        onEnteringStateCONSTRUCTOR();
    }

    //----------------------------------------------------------------------------
    //! \brief Reset the state machine.
    //----------------------------------------------------------------------------
    void reset()
    {
        StateMachine::reset();
        gumballs = 1;
        onEnteringStateCONSTRUCTOR();
    }

    //----------------------------------------------------------------------------
    //! \brief External event.
    //----------------------------------------------------------------------------
    void insertQuarter()
    {
        LOGD("[EVENT %s]\n", __func__);

        static Transitions s_transitions =
        {
            {
                GumballControllerStates::NOQUARTER,
                {
                    GumballControllerStates::HASQUARTER,
                    nullptr,
                    nullptr,
                },
            },
        };

        transition(s_transitions);
    }

    //----------------------------------------------------------------------------
    //! \brief External event.
    //----------------------------------------------------------------------------
    void ejectQuarter()
    {
        LOGD("[EVENT %s]\n", __func__);

        static Transitions s_transitions =
        {
            {
                GumballControllerStates::HASQUARTER,
                {
                    GumballControllerStates::NOQUARTER,
                    nullptr,
                    nullptr,
                },
            },
        };

        transition(s_transitions);
    }

    //----------------------------------------------------------------------------
    //! \brief External event.
    //----------------------------------------------------------------------------
    void turnCrank()
    {
        LOGD("[EVENT %s]\n", __func__);

        static Transitions s_transitions =
        {
            {
                GumballControllerStates::HASQUARTER,
                {
                    GumballControllerStates::GUMBALLSOLD,
                    nullptr,
                    &GumballController::onTransitioningHASQUARTER_GUMBALLSOLD,
                },
            },
        };

        transition(s_transitions);
    }

private: // Guards and reactions

    //----------------------------------------------------------------------------
    //! \brief Guard the transition from state [*] to state NOQUARTER.
    //----------------------------------------------------------------------------
    bool onGuardingTransitionCONSTRUCTOR_NOQUARTER()
    {
        const bool guard = (gumballs > 0);
        LOGD("[GUARD [*] --> NOQUARTER: gumballs > 0] result: %s\n",
             (guard ? "true" : "false"));
        return guard;
    }

    //----------------------------------------------------------------------------
    //! \brief Guard the transition from state [*] to state OUTOFGUMBALLS.
    //----------------------------------------------------------------------------
    bool onGuardingTransitionCONSTRUCTOR_OUTOFGUMBALLS()
    {
        const bool guard = (gumballs == 0);
        LOGD("[GUARD [*] --> OUTOFGUMBALLS: gumballs == 0] result: %s\n",
             (guard ? "true" : "false"));
        return guard;
    }

    //-----------------------------------------------------------------------------------
    //! \brief Do the action when transitioning from state HASQUARTER to state GUMBALLSOLD.
    //-----------------------------------------------------------------------------------
    void onTransitioningHASQUARTER_GUMBALLSOLD()
    {
        LOGD("[TRANSITION HASQUARTER --> GUMBALLSOLD: --gumballs]\n");
        --gumballs;
        LOGD("Il me reste %d gumballs\n", gumballs);
    }

    //----------------------------------------------------------------------------
    //! \brief Guard the transition from state GUMBALLSOLD to state NOQUARTER.
    //----------------------------------------------------------------------------
    bool onGuardingTransitionGUMBALLSOLD_NOQUARTER()
    {
        const bool guard = (gumballs > 0);
        LOGD("[GUARD GUMBALLSOLD --> NOQUARTER: gumballs > 0] result: %s\n",
             (guard ? "true" : "false"));
        return guard;
    }

    //----------------------------------------------------------------------------
    //! \brief Guard the transition from state GUMBALLSOLD to state OUTOFGUMBALLS.
    //----------------------------------------------------------------------------
    bool onGuardingTransitionGUMBALLSOLD_OUTOFGUMBALLS()
    {
        const bool guard = (gumballs == 0);
        LOGD("[GUARD GUMBALLSOLD --> OUTOFGUMBALLS: gumballs == 0] result: %s\n",
             (guard ? "true" : "false"));
        return guard;
    }

    //----------------------------------------------------------------------------
    //! \brief Do the action when entering the state [*].
    //----------------------------------------------------------------------------
    void onEnteringStateCONSTRUCTOR()
    {
        LOGD("[ENTERING STATE [*]]\n");
        
        LOGD("[STATE [*]] Internal transition\n");
        if (onGuardingTransitionCONSTRUCTOR_NOQUARTER())
        {
            static StateMachine<GumballController, GumballControllerStates>::Transition tr =
            {
                .destination = GumballControllerStates::NOQUARTER,
                .guard = &GumballController::onGuardingTransitionCONSTRUCTOR_NOQUARTER,
            };
            transition(&tr);
            return ;
        }
        if (onGuardingTransitionCONSTRUCTOR_OUTOFGUMBALLS())
        {
            static StateMachine<GumballController, GumballControllerStates>::Transition tr =
            {
                .destination = GumballControllerStates::OUTOFGUMBALLS,
                .guard = &GumballController::onGuardingTransitionCONSTRUCTOR_OUTOFGUMBALLS,
            };
            transition(&tr);
            return ;
        }
    }

    //----------------------------------------------------------------------------
    //! \brief Do the action when entering the state GUMBALLSOLD.
    //----------------------------------------------------------------------------
    void onEnteringStateGUMBALLSOLD()
    {
        LOGD("[ENTERING STATE GUMBALLSOLD]\n");
        
        LOGD("[STATE GUMBALLSOLD] Internal transition\n");
        if (onGuardingTransitionGUMBALLSOLD_NOQUARTER())
        {
            static StateMachine<GumballController, GumballControllerStates>::Transition tr =
            {
                .destination = GumballControllerStates::NOQUARTER,
                .guard = &GumballController::onGuardingTransitionGUMBALLSOLD_NOQUARTER,
            };
            transition(&tr);
            return ;
        }
        if (onGuardingTransitionGUMBALLSOLD_OUTOFGUMBALLS())
        {
            static StateMachine<GumballController, GumballControllerStates>::Transition tr =
            {
                .destination = GumballControllerStates::OUTOFGUMBALLS,
                .guard = &GumballController::onGuardingTransitionGUMBALLSOLD_OUTOFGUMBALLS,
            };
            transition(&tr);
            return ;
        }
    }

    private : 
    int gumballs;
};

#endif // GUMBALLCONTROLLER_HPP
