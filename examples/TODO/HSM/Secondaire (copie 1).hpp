// This file as been generated the June 29, 2022 from the PlantUML statechart ../SimpleComposite.plantuml
// This code generation is still experimental. Some border cases may not be correctly managed!

#ifndef EnableSystem_HPP
#  define EnableSystem_HPP

#  include "StateMachine.hpp"

//********************************************************************************
//! \brief States of the state machine.
//********************************************************************************
enum class EnableSystemStates
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
static inline const char* stringify(EnableSystemStates const state)
{
    static const char* s_states[] =
    {
        [int(EnableSystemStates::CONSTRUCTOR)] = "[*]",
        [int(EnableSystemStates::ON)] = "ON",
        [int(EnableSystemStates::OFF)] = "OFF",
    };

    return s_states[int(state)];
};

//********************************************************************************
//! \brief State machine concrete implementation.
//********************************************************************************
class EnableSystem : public StateMachine<EnableSystem, EnableSystemStates>
{
public: // CONSTRUCTOR and external events

    //----------------------------------------------------------------------------
    //! \brief Default CONSTRUCTOR. Start from initial state and call it actions.
    //----------------------------------------------------------------------------
    EnableSystem()
        : StateMachine(EnableSystemStates::CONSTRUCTOR)
    {
    }

#if defined(MOCKABLE)
    //----------------------------------------------------------------------------
    //! \brief Needed because of virtual methods.
    //----------------------------------------------------------------------------
    virtual ~EnableSystem() = default;
#endif

    //----------------------------------------------------------------------------
    //! \brief Reset the state machine.
    //----------------------------------------------------------------------------
    void start()
    {
        StateMachine::start();
        {
            LOGD("[EnableSystem][STATE [*]] Candidate for internal transitioning to state ON\n");
            static const Transition tr =
            {
                .destination = EnableSystemStates::ON,
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
        LOGD("[EnableSystem][EVENT %s]\n", __func__);

        static const Transitions s_transitions =
        {
            {
                EnableSystemStates::ON,
                {
                    .destination = EnableSystemStates::OFF,
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
        LOGD("[EnableSystem][EVENT %s]\n", __func__);

        static const Transitions s_transitions =
        {
            {
                EnableSystemStates::OFF,
                {
                    .destination = EnableSystemStates::ON,
                },
            },
        };

        transition(s_transitions);
    }
};

#endif // EnableSystem_HPP
