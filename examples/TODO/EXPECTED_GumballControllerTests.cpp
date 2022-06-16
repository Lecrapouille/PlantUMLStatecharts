// This file as been generated the June 16, 2022
// This code generation is still experimental. Some border cases may not be correctly managed!

#include "GumballController.hpp"
#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <cstring>

//***************************************************************************************************************************************
//! \brief Compile with one of the following line:
//! g++ --std=c++14 -Wall -Wextra -Wshadow -I../include -DFSM_DEBUG GumballControllerTests.cpp `pkg-config --cflags --libs gtest gmock`
//***************************************************************************************************************************************
int main(int argc, char *argv[])
{
    // The following line must be executed to initialize Google Mock
    // (and Google Test) before running the tests.
    ::testing::InitGoogleMock(&argc, argv);
    return RUN_ALL_TESTS();
}

//--------------------------------------------------------------------------------
TEST(GumballControllerTests, TestInitialSate)
{
    LOGD("===============================================\n");
    LOGD("Check initial state after constructor or reset.\n");
    LOGD("===============================================\n");
    GumballController fsm(1);

    ASSERT_TRUE(fsm.state() == GumballControllerStates::NOQUARTER
          || fsm.state() == GumballControllerStates::OUTOFGUMBALLS);
    ASSERT_TRUE(strcmp(fsm.c_str(), "NOQUARTER") == 0
          || strcmp(fsm.c_str(), "OUTOFGUMBALLS") == 0);
    fsm.reset();
    ASSERT_TRUE(fsm.state() == GumballControllerStates::NOQUARTER
          || fsm.state() == GumballControllerStates::OUTOFGUMBALLS);
    ASSERT_TRUE(strcmp(fsm.c_str(), "NOQUARTER") == 0
          || strcmp(fsm.c_str(), "OUTOFGUMBALLS") == 0);
}

//--------------------------------------------------------------------------------
TEST(GumballControllerTests, TestCycle0)
{
    LOGD("===========================================\n");
    LOGD("Check cycle: [*] NOQUARTER HASQUARTER GUMBALLSOLD NOQUARTER\n");
    LOGD("===========================================\n");
    GumballController fsm(2); // If gumballs > 0

    LOGD("// Event insertQuarter []: NOQUARTER ==> HASQUARTER\n");
    fsm.insertQuarter();
    LOGD("Current state: %s\n", fsm.c_str());
    ASSERT_EQ(fsm.state(), GumballControllerStates::HASQUARTER);
    ASSERT_STREQ(fsm.c_str(), "HASQUARTER");
    LOGD("Assertions: ok\n\n");
    LOGD("// Event turnCrank []: HASQUARTER ==> GUMBALLSOLD\n");
    fsm.turnCrank(); // FIXME MANQUE If gumballs > 0
    LOGD("Current state: %s\n", fsm.c_str());
    ASSERT_EQ(fsm.state(), GumballControllerStates::NOQUARTER);
    ASSERT_STREQ(fsm.c_str(), "NOQUARTER");
    LOGD("Assertions: ok\n\n");
}

//--------------------------------------------------------------------------------
TEST(GumballControllerTests, TestCycle1)
{
    LOGD("===========================================\n");
    LOGD("Check cycle: [*] NOQUARTER HASQUARTER NOQUARTER\n");
    LOGD("===========================================\n");
    GumballController fsm(1); // If gumballs > 0

    LOGD("// Event insertQuarter []: NOQUARTER ==> HASQUARTER\n");
    fsm.insertQuarter();
    LOGD("Current state: %s\n", fsm.c_str());
    ASSERT_EQ(fsm.state(), GumballControllerStates::HASQUARTER);
    ASSERT_STREQ(fsm.c_str(), "HASQUARTER");
    LOGD("Assertions: ok\n\n");
    LOGD("// Event ejectQuarter []: HASQUARTER ==> NOQUARTER\n");
    fsm.ejectQuarter();
    LOGD("Current state: %s\n", fsm.c_str());
    ASSERT_EQ(fsm.state(), GumballControllerStates::NOQUARTER);
    ASSERT_STREQ(fsm.c_str(), "NOQUARTER");
    LOGD("Assertions: ok\n\n");
}

//--------------------------------------------------------------------------------
TEST(GumballControllerTests, TestPath0)
{
    LOGD("===========================================\n");
    LOGD("Check path: [*] NOQUARTER HASQUARTER GUMBALLSOLD OUTOFGUMBALLS\n");
    LOGD("===========================================\n");
    GumballController fsm(1); // If gumballs > 0

    LOGD("Current state: %s\n", fsm.c_str());
    ASSERT_EQ(fsm.state(), GumballControllerStates::NOQUARTER);
    ASSERT_STREQ(fsm.c_str(), "NOQUARTER");
    LOGD("Assertions: ok\n\n");
    fsm.insertQuarter();
    LOGD("Current state: %s\n", fsm.c_str());
    ASSERT_EQ(fsm.state(), GumballControllerStates::HASQUARTER);
    ASSERT_STREQ(fsm.c_str(), "HASQUARTER");
    LOGD("Assertions: ok\n\n");
    fsm.turnCrank();  // FIXME MANQUE If gumballs == 0
    LOGD("Current state: %s\n", fsm.c_str());
    ASSERT_EQ(fsm.state(), GumballControllerStates::OUTOFGUMBALLS);
    ASSERT_STREQ(fsm.c_str(), "OUTOFGUMBALLS");
    LOGD("Assertions: ok\n\n");
}

//--------------------------------------------------------------------------------
TEST(GumballControllerTests, TestPath1)
{
    LOGD("===========================================\n");
    LOGD("Check path: [*] OUTOFGUMBALLS\n");
    LOGD("===========================================\n");
    GumballController fsm(0); // If gumballs == 0

    LOGD("Current state: %s\n", fsm.c_str());
    ASSERT_EQ(fsm.state(), GumballControllerStates::OUTOFGUMBALLS);
    ASSERT_STREQ(fsm.c_str(), "OUTOFGUMBALLS");
    LOGD("Assertions: ok\n\n");
}

