#ifndef LKSCONTROLLERMACROS_HPP
#  define LKSCONTROLLERMACROS_HPP

#  define Disable true
#  define Enable false

#  define CUSTOM_LKSCONTROLLER_CONSTRUCTOR

#  define CUSTOM_LKSCONTROLLER_MEMBER_FUNCTIONS

#  define CUSTOM_LKSCONTROLLER_MEMBER_VARIABLES \
   bool LED_LKS = false; \
   bool LED_lane = false; \
   bool LED_steering = false; \
   bool servoing = false;

#  define CUSTOM_LKSCONTROLLER_PREPARE_UNIT_TEST

#  define CUSTOM_LKSCONTROLLER_INIT_UNIT_TEST_VARIABLES

#endif // LKSCONTROLLERMACROS_HPP
