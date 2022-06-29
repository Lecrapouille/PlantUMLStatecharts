// This file as been generated the June 29, 2022 from the PlantUML statechart ../SimpleComposite.plantuml
// This code generation is still experimental. Some border cases may not be correctly managed!

#ifndef Composite_HPP
#  define Composite_HPP

#  include "Secondaire.hpp"

//********************************************************************************
//! \brief States of the state machine.
//********************************************************************************
enum class CompositeStates
{
    // Composite:
    CONSTRUCTOR,
    ENABLESYSTEM,
    DISABLESYSTEM,
    // Mandatory internal states:
    IGNORING_EVENT, CANNOT_HAPPEN, MAX_STATES
};

//********************************************************************************
//! \brief Convert enum states to human readable string.
//********************************************************************************
static inline const char* stringify(CompositeStates const state)
{
    static const char* s_states[] =
    {
        [int(CompositeStates::CONSTRUCTOR)] = "[*]",
        [int(CompositeStates::ENABLESYSTEM)] = "ENABLESYSTEM",
        [int(CompositeStates::DISABLESYSTEM)] = "DISABLESYSTEM",
    };

    return s_states[int(state)];
};

//********************************************************************************
//! \brief State machine concrete implementation.
//********************************************************************************
class Composite : public StateMachine<Composite, CompositeStates>
{
public: // Constructor and external events

    //----------------------------------------------------------------------------
    //! \brief Default constructor. Start from initial state and call it actions.
    //----------------------------------------------------------------------------
    Composite()
        : StateMachine(CompositeStates::CONSTRUCTOR)
    {
    }

#if defined(MOCKABLE)
    //----------------------------------------------------------------------------
    //! \brief Needed because of virtual methods.
    //----------------------------------------------------------------------------
    virtual ~Composite() = default;
#endif

    //----------------------------------------------------------------------------
    //! \brief Reset the state machine.
    //----------------------------------------------------------------------------
    void start()
    {
        StateMachine::start();

        m_enable_system_enabled = true;
        m_enable_system.start();

        // Internal transition
        {
            LOGD("[Composite][STATE [*]] Candidate for internal transitioning to state ENABLESYSTEM\n");
            static const Transition tr =
            {
                .destination = CompositeStates::ENABLESYSTEM,
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
        if (m_enable_system_enabled)
        {
            m_enable_system.off();
        }
        else
        {
           LOGD("Sorry FSM enable_system is disabled\n");
        }
    }

    //----------------------------------------------------------------------------
    //! \brief External event.
    //----------------------------------------------------------------------------
    void on()
    {
        if (m_enable_system_enabled)
        {
            m_enable_system.on();
        }
        else
        {
           LOGD("Sorry FSM enable_system is disabled\n");
        }
    }

    //----------------------------------------------------------------------------
    //! \brief External event.
    //----------------------------------------------------------------------------
    void disable()
    {
        LOGD("[Composite][EVENT %s]\n", __func__);

        m_enable_system_enabled = false;

        static const Transitions s_transitions =
        {
            {
                CompositeStates::ENABLESYSTEM,
                {
                    .destination = CompositeStates::DISABLESYSTEM,
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
        LOGD("[Composite][EVENT %s]\n", __func__);

        m_enable_system_enabled = true;
        m_enable_system.start();

        static const Transitions s_transitions =
        {
            {
                CompositeStates::DISABLESYSTEM,
                {
                    .destination = CompositeStates::ENABLESYSTEM,
                },
            },
        };

        transition(s_transitions);
    }

public:

   EnableSystem m_enable_system;

private:

   bool m_enable_system_enabled = false;
};

#endif // Composite_HPP
