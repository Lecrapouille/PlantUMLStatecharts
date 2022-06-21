// This file as been generated the June 21, 2022
// This code generation is still experimental. Some border cases may not be correctly managed!

#define MOCKABLE virtual
#include "FixErroneous2Controller.hpp"
#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <cstring>

using namespace ::testing;

class MockFixErroneous2Controller : public FixErroneous2Controller
{
public:

    virtual ~MockFixErroneous2Controller() = default;
    MOCK_METHOD(bool, onGuardingTransitionA_B, (), (override));
    MOCK_METHOD(bool, onGuardingTransitionA_C, (), (override));
};

//*********************************************************************************************************************************************
//! \brief Compile with one of the following line:
//! g++ --std=c++14 -Wall -Wextra -Wshadow -I../include -DFSM_DEBUG FixErroneous2ControllerTests.cpp `pkg-config --cflags --libs gtest gmock`
//*********************************************************************************************************************************************
int main(int argc, char *argv[])
{
    // The following line must be executed to initialize Google Mock
    // (and Google Test) before running the tests.
    ::testing::InitGoogleMock(&argc, argv);
    return RUN_ALL_TESTS();
}

//--------------------------------------------------------------------------------
TEST(FixErroneous2ControllerTests, TestInitialSate)
{
    LOGD("===============================================\n");
    LOGD("Check initial state after constructor or reset.\n");
    LOGD("===============================================\n");
    FixErroneous2Controller fsm; // not mocked !
    fsm.reset();
    EXPECT_TRUE((fsm.state() == FixErroneous2ControllerStates::A) ||
                (fsm.state() == FixErroneous2ControllerStates::B));
    EXPECT_TRUE((strcmp(fsm.c_str(), "A") == 0) ||
                (strcmp(fsm.c_str(), "B") == 0));
}

//--------------------------------------------------------------------------------
TEST(FixErroneous2ControllerTests, TestPath0)
{
    LOGD("===========================================\n");
    LOGD("Check path: [*] A B\n");
    LOGD("===========================================\n");
    MockFixErroneous2Controller fsm;

    EXPECT_CALL(fsm, onGuardingTransitionA_B()).WillOnce(Return(true));
    EXPECT_CALL(fsm, onGuardingTransitionA_C()).Times(AtMost(1)).WillOnce(Return(false));
    fsm.reset();

    LOGD("Current state: %s\n", fsm.c_str());
    EXPECT_EQ(fsm.state(), FixErroneous2ControllerStates::B);
    EXPECT_STREQ(fsm.c_str(), "B");
}

//--------------------------------------------------------------------------------
TEST(FixErroneous2ControllerTests, TestPath1)
{
    LOGD("===========================================\n");
    LOGD("Check path: [*] A C\n");
    LOGD("===========================================\n");
    MockFixErroneous2Controller fsm;

    EXPECT_CALL(fsm, onGuardingTransitionA_B()).Times(AtMost(1)).WillOnce(Return(false));
    EXPECT_CALL(fsm, onGuardingTransitionA_C()).WillOnce(Return(true));
    fsm.reset();

    LOGD("Current state: %s\n", fsm.c_str());
    EXPECT_EQ(fsm.state(), FixErroneous2ControllerStates::C);
    EXPECT_STREQ(fsm.c_str(), "C");
}

//--------------------------------------------------------------------------------
TEST(FixErroneous2ControllerTests, TestPath2)
{
    LOGD("===========================================\n");
    LOGD("Check path: [*] A D\n");
    LOGD("===========================================\n");
    MockFixErroneous2Controller fsm;

    EXPECT_CALL(fsm, onGuardingTransitionA_B()).WillRepeatedly(Return(false));
    EXPECT_CALL(fsm, onGuardingTransitionA_C()).WillRepeatedly(Return(false));
    fsm.reset();

    LOGD("Current state: %s\n", fsm.c_str());
    EXPECT_EQ(fsm.state(), FixErroneous2ControllerStates::A);
    EXPECT_STREQ(fsm.c_str(), "A");

    fsm.event();
    LOGD("Current state: %s\n", fsm.c_str());
    EXPECT_EQ(fsm.state(), FixErroneous2ControllerStates::D);
    EXPECT_STREQ(fsm.c_str(), "D");
}
