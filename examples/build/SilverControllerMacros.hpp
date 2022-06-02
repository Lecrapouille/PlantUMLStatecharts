#ifndef SILVERCONTROLLERMACROS_HPP
#  define SILVERCONTROLLERMACROS_HPP

#  define CUSTOM_SILVERCONTROLLER_CONSTRUCTOR

#  define CUSTOM_SILVERCONTROLLER_MEMBER_FUNCTIONS \
   void pairing_phone(); \
   void blue_led_off(); \
   void white_led_off(); \
   void blue_led_blinking(); \
   void white_led_glow(); \
   void blue_led_constant_glow(); \
   void launch_home_screen();

#  define CUSTOM_SILVERCONTROLLER_MEMBER_VARIABLES

#  define CUSTOM_SILVERCONTROLLER_PREPARE_UNIT_TEST \
   void SilverController::pairing_phone() { LOGD("[ACTION %s]\n", __func__); } \
   void SilverController::blue_led_off() { LOGD("[ACTION %s]\n", __func__); } \
   void SilverController::white_led_off() { LOGD("[ACTION %s]\n", __func__); } \
   void SilverController::blue_led_blinking() { LOGD("[ACTION %s]\n", __func__); } \
   void SilverController::white_led_glow() { LOGD("[ACTION %s]\n", __func__); } \
   void SilverController::blue_led_constant_glow() { LOGD("[ACTION %s]\n", __func__); } \
   void SilverController::launch_home_screen() { LOGD("[ACTION %s]\n", __func__); } \

#  define CUSTOM_SILVERCONTROLLER_INIT_UNIT_TEST_VARIABLES

#endif // SILVERCONTROLLERMACROS_HPP
