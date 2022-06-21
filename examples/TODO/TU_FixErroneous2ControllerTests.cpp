// This file as been generated the June 21, 2022
// This code generation is still experimental. Some border cases may not be correctly managed!

#include "FixErroneous2Controller.hpp"
#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <cstring>

using namespace ::testing;

class MockFixErroneous2Controller : public FixErroneous2Controller
{
public:

    virtual ~MockFixErroneous2Controller() = default;
    MOCK_METHOD(bool, guard1, (), (override));
    MOCK_METHOD(bool, guard2, (), (override));
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
/*TEST(FixErroneous2ControllerTests, TestInitialSate)
{
    LOGD("===============================================\n");
    LOGD("Check initial state after constructor or reset.\n");
    LOGD("===============================================\n");
    FixErroneous2Controller fsm;

    ASSERT_TRUE(fsm.state() == FixErroneous2ControllerStates::A);
    ASSERT_TRUE(strcmp(fsm.c_str(), "A") == 0);

    fsm.reset();
    ASSERT_TRUE(fsm.state() == FixErroneous2ControllerStates::A);
    ASSERT_TRUE(strcmp(fsm.c_str(), "A") == 0);
}*/

//--------------------------------------------------------------------------------
TEST(FixErroneous2ControllerTests, TestPath0)
{
    LOGD("===========================================\n");
    LOGD("Check path: [*] A B\n");
    LOGD("===========================================\n");
    MockFixErroneous2Controller fsm;

    EXPECT_CALL(fsm, guard1()).Times(0);//WillRepeatedly(Return(true));
    EXPECT_CALL(fsm, guard2()).WillRepeatedly(Return(false));
    fsm.reset();

    LOGD("Current state: %s\n", fsm.c_str());
    //EXPECT_CALL(fsm, guard1()).Times(AtLeast(1));
    //EXPECT_CALL(fsm, guard2()).Times(AtLeast(0));
    ASSERT_EQ(fsm.state(), FixErroneous2ControllerStates::B);
    ASSERT_STREQ(fsm.c_str(), "B");
    LOGD("Assertions: ok\n\n");
}

#if 0
//--------------------------------------------------------------------------------
TEST(FixErroneous2ControllerTests, TestPath1)
{
    LOGD("===========================================\n");
    LOGD("Check path: [*] A C\n");
    LOGD("===========================================\n");
    MockFixErroneous2Controller fsm;
    EXPECT_CALL(fsm, guard1()).WillOnce(Return(false));
    EXPECT_CALL(fsm, guard2()).WillOnce(Return(true));

    LOGD("Current state: %s\n", fsm.c_str());
    EXPECT_CALL(fsm, guard1()).Times(AtLeast(0));
    EXPECT_CALL(fsm, guard2()).Times(AtLeast(1));
    ASSERT_EQ(fsm.state(), FixErroneous2ControllerStates::C);
    ASSERT_STREQ(fsm.c_str(), "C");
    LOGD("Assertions: ok\n\n");
}

//--------------------------------------------------------------------------------
TEST(FixErroneous2ControllerTests, TestPath2)
{
    LOGD("===========================================\n");
    LOGD("Check path: [*] A D\n");
    LOGD("===========================================\n");
    MockFixErroneous2Controller fsm;
    EXPECT_CALL(fsm, guard1()).WillOnce(Return(false));
    EXPECT_CALL(fsm, guard2()).WillOnce(Return(false));

    LOGD("Current state: %s\n", fsm.c_str());
    EXPECT_CALL(fsm, guard1()).Times(AtLeast(0));
    EXPECT_CALL(fsm, guard2()).Times(AtLeast(0));
    ASSERT_EQ(fsm.state(), FixErroneous2ControllerStates::A);
    ASSERT_STREQ(fsm.c_str(), "A");
    LOGD("Assertions: ok\n\n");

    fsm.event();
    EXPECT_CALL(fsm, guard1()).WillOnce(Return(false));
    EXPECT_CALL(fsm, guard2()).WillOnce(Return(false));
    LOGD("Current state: %s\n", fsm.c_str());
    EXPECT_CALL(fsm, guard1()).Times(AtLeast(0));
    EXPECT_CALL(fsm, guard2()).Times(AtLeast(0));
    ASSERT_EQ(fsm.state(), FixErroneous2ControllerStates::D);
    ASSERT_STREQ(fsm.c_str(), "D");
    LOGD("Assertions: ok\n\n");
}
#endif
