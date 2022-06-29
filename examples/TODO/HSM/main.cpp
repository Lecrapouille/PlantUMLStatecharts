#include "Principal.hpp"
#include <iostream>

int main()
{
    std::cout << "Constructor\n";
    Composite fsm;
    std::cout << fsm.c_str() << ", " << fsm.m_enable_system.c_str() << std::endl;

    std::cout << "init\n";
    fsm.start();
    std::cout << fsm.c_str() << ", " << fsm.m_enable_system.c_str() << std::endl;

    std::cout << "on\n";
    fsm.on();
    std::cout << fsm.c_str() << ", " << fsm.m_enable_system.c_str() << std::endl;

    std::cout << "off\n";
    fsm.off();
    std::cout << fsm.c_str() << ", " << fsm.m_enable_system.c_str() << std::endl;

    std::cout << "on\n";
    fsm.on();
    std::cout << fsm.c_str() << ", " << fsm.m_enable_system.c_str() << std::endl;

    std::cout << "off\n";
    fsm.off();
    std::cout << fsm.c_str() << ", " << fsm.m_enable_system.c_str() << std::endl;

    std::cout << "halt\n";
    fsm.disable();
    std::cout << fsm.c_str() << ", " << fsm.m_enable_system.c_str() << std::endl;

    std::cout << "start\n";
    fsm.enable();
    std::cout << fsm.c_str() << ", " << fsm.m_enable_system.c_str() << std::endl;

    return 0;
}
