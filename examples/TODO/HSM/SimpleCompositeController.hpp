// This file as been generated the June 29, 2022 from the PlantUML statechart ../SimpleSimpleCompositeController.plantuml
// This code generation is still experimental. Some border cases may not be correctly managed!

#ifndef SIMPLECOMPOSITECONTROLLER_HPP
#  define SIMPLECOMPOSITECONTROLLER_HPP

#  include "EnableSystemSub.hpp"

//********************************************************************************
//! \brief States of the state machine.
//********************************************************************************
enum class SimpleCompositeControllerStates
{
    // Client states:
    CONSTRUCTOR,
    ENABLESYSTEM,
    DISABLESYSTEM,
    // Mandatory internal states:
    IGNORING_EVENT, CANNOT_HAPPEN, MAX_STATES
};

//********************************************************************************
//! \brief Convert enum states to human readable string.
//********************************************************************************
static inline const char* stringify(SimpleCompositeControllerStates const state)
{
    static const char* s_states[] =
    {
        [int(SimpleCompositeControllerStates::CONSTRUCTOR)] = "[*]",
        [int(SimpleCompositeControllerStates::ENABLESYSTEM)] = "ENABLESYSTEM",
        [int(SimpleCompositeControllerStates::DISABLESYSTEM)] = "DISABLESYSTEM",
    };

    return s_states[int(state)];
};

//********************************************************************************
//! \brief State machine concrete implementation.
//********************************************************************************
class SimpleCompositeController : public StateMachine<SimpleCompositeController, SimpleCompositeControllerStates>
{
public: // Constructor and external events

    //----------------------------------------------------------------------------
    //! \brief Default constructor. Start from initial state and call it actions.
    //----------------------------------------------------------------------------
    SimpleCompositeController()
        : StateMachine(SimpleCompositeControllerStates::CONSTRUCTOR)
    {
    }

#if defined(MOCKABLE)
    //----------------------------------------------------------------------------
    //! \brief Needed because of virtual methods.
    //----------------------------------------------------------------------------
    virtual ~SimpleCompositeController() = default;
#endif

    //---------------------------------------------------------------------------------------
    //! \brief Reset the state machine and nested machines. Do the initial internal transition.
    //---------------------------------------------------------------------------------------
    void start()
    {
        StateMachine::start();
        m_enablesystemsub.start();

        // Internal transition
        {
            LOGD("[SIMPLECOMPOSITECONTROLLER][STATE [*]] Candidate for internal transitioning to state ENABLESYSTEM\n");
            static const Transition tr =
            {
                .destination = SimpleCompositeControllerStates::ENABLESYSTEM,
            };
            transition(&tr);
            return ;
        }
    }

    //----------------------------------------------------------------------------
    //! \brief Broadcast external event.
    //----------------------------------------------------------------------------
    inline void off() { m_enablesystemsub.off(); }

    //----------------------------------------------------------------------------
    //! \brief Broadcast external event.
    //----------------------------------------------------------------------------
    inline void on() { m_enablesystemsub.on(); }

    //----------------------------------------------------------------------------
    //! \brief External event.
    //----------------------------------------------------------------------------
    void disable()
    {
        LOGD("[SIMPLECOMPOSITECONTROLLER][EVENT %s]\n", __func__);

m_enable_system.stop();

        static const Transitions s_transitions =
        {
            {
                SimpleCompositeControllerStates::ENABLESYSTEM,
                {
                    .destination = SimpleCompositeControllerStates::DISABLESYSTEM,
                },
            },
        };

        transition(s_transitions);
    }

    //----------------------------------------------------------------------------
    //! \brief External event.
    //----------------------------------------------------------------------------
    void enable()
    {
        LOGD("[SIMPLECOMPOSITECONTROLLER][EVENT %s]\n", __func__);

        m_enable_system.start();

        static const Transitions s_transitions =
        {
            {
                SimpleCompositeControllerStates::DISABLESYSTEM,
                {
                    .destination = SimpleCompositeControllerStates::ENABLESYSTEM,
                },
            },
        };

        transition(s_transitions);
    }

private: // Guards and actions on transitions

private: // Actions on states

private: // Sub state machines

    EnableSystemSub m_enablesystemsub;
};

#endif // SIMPLECOMPOSITECONTROLLER_HPP
