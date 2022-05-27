#ifndef RICHMANCONTROLLERMACROS_HPP
#  define RICHMANCONTROLLERMACROS_HPP

#  include <stdio.h>

#  define youpi printf("youpi\n")

#  define CUSTOM_RICHMANCONTROLLER_CONSTRUCTOR \
    {}

#  define CUSTOM_RICHMANCONTROLLER_MEMBER_FUNCTIONS \
    void incr(int& x) { x += 1; }

#  define CUSTOM_RICHMANCONTROLLER_MEMBER_VARIABLES \
    int quarters = 0;

#endif // RICHMANCONTROLLERMACROS_HPP
