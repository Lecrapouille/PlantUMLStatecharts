// This file as been generated the June 29, 2022 from the PlantUML statechart ../SimpleComposite.plantuml
// This code generation is still experimental. Some border cases may not be correctly managed!

#ifndef ENABLESYSTEMSUB_HPP
#  define ENABLESYSTEMSUB_HPP

#  include "StateMachine.hpp"

//********************************************************************************
//! \brief States of the state machine.
//********************************************************************************
enum class EnableSystemSubStates
{
    // Client states:
    CONSTRUCTOR,
    ON,
    OFF,
    // Mandatory internal states:
    IGNORING_EVENT, CANNOT_HAPPEN, MAX_STATES
};

//********************************************************************************
//! \brief Convert enum states to human readable string.
//********************************************************************************
static inline const char* stringify(EnableSystemSubStates const state)
{
    static const char* s_states[] =
    {
        [int(EnableSystemSubStates::CONSTRUCTOR)] = "[*]",
        [int(EnableSystemSubStates::ON)] = "ON",
        [int(EnableSystemSubStates::OFF)] = "OFF",
    };

    return s_states[int(state)];
};

//********************************************************************************
//! \brief State machine concrete implementation.
//********************************************************************************
class EnableSystemSub : public StateMachine<EnableSystemSub, EnableSystemSubStates>
{
public: // Constructor and external events

    //----------------------------------------------------------------------------
    //! \brief Default constructor. Start from initial state and call it actions.
    //----------------------------------------------------------------------------
    EnableSystemSub()
        : StateMachine(EnableSystemSubStates::CONSTRUCTOR)
    {
    }

#if defined(MOCKABLE)
    //----------------------------------------------------------------------------
    //! \brief Needed because of virtual methods.
    //----------------------------------------------------------------------------
    virtual ~EnableSystemSub() = default;
#endif

    //----------------------------------------------------------------------------
    //! \brief Reset the state machine.
    //----------------------------------------------------------------------------
    void start()
    {
        StateMachine::start();
        {
            LOGD("[ENABLESYSTEMSUB][STATE [*]] Candidate for internal transitioning to state ON\n");
            static const Transition tr =
            {
                .destination = EnableSystemSubStates::ON,
            };
            transition(&tr);
            return ;
        }
    }

    //----------------------------------------------------------------------------
    //! \brief External event.
    //----------------------------------------------------------------------------
    void off()
    {
        LOGD("[ENABLESYSTEMSUB][EVENT %s]\n", __func__);

        static const Transitions s_transitions =
        {
            {
                EnableSystemSubStates::ON,
                {
                    .destination = EnableSystemSubStates::OFF,
                },
            },
        };

        transition(s_transitions);
    }

    //----------------------------------------------------------------------------
    //! \brief External event.
    //----------------------------------------------------------------------------
    void on()
    {
        LOGD("[ENABLESYSTEMSUB][EVENT %s]\n", __func__);

        static const Transitions s_transitions =
        {
            {
                EnableSystemSubStates::OFF,
                {
                    .destination = EnableSystemSubStates::ON,
                },
            },
        };

        transition(s_transitions);
    }
private: // Guards and actions on transitions

private: // Actions on states

private: // Sub state machines
};

#endif // ENABLESYSTEMSUB_HPP
