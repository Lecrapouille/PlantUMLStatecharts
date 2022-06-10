// This file as been generated the June 09, 2022
// Copyright (c) Quentin QUADRAT
// Copyright (c) Faurecia Clarion Electronics Europe SAS
// This code generation is still experimental. Some border cases may not be correctly managed!

#ifndef SIMPLECONTROLLERMACROS_HPP
#  define SIMPLECONTROLLERMACROS_HPP

#  define CUSTOM_SIMPLECONTROLLER_CONSTRUCTOR

#  define CUSTOM_SIMPLECONTROLLER_MEMBER_FUNCTIONS \
   void action1() { LOGD("[ACTION %s]\n", __func__); } \
   void action3() { LOGD("[ACTION %s]\n", __func__); } \
   void action4() { LOGD("[ACTION %s]\n", __func__); } \
   void action5() { LOGD("[ACTION %s]\n", __func__); } \
   void action6() { LOGD("[ACTION %s]\n", __func__); } \
   void action7() { LOGD("[ACTION %s]\n", __func__); } \
   void action8() { LOGD("[ACTION %s]\n", __func__); } \
   void action9() { LOGD("[ACTION %s]\n", __func__); } \
   void action10() { LOGD("[ACTION %s]\n", __func__); }

#  define CUSTOM_SIMPLECONTROLLER_MEMBER_VARIABLES \
   bool guard1 = true; \
   bool guard3 = true; \
   bool guard6 = true;

#  define CUSTOM_SIMPLECONTROLLER_PREPARE_UNIT_TEST

#  define CUSTOM_SIMPLECONTROLLER_INIT_UNIT_TEST_VARIABLES

#endif // SIMPLECONTROLLERMACROS_HPP
