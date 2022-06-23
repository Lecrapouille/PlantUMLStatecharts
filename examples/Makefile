###############################################################################
# MIT License
#
# Copyright (c) 2022 Quentin Quadrat
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###############################################################################

# Our tool for parsing PlantUML statecharts and generate C++ code
PLANTUML_PARSER = ../tool/Parser.py
# File and class name prefix
PREFIX = Controller
# Arguments passed to $(PLANTUML_PARSER)
PLANTUML_COMMAND_LINE = hpp $(PREFIX)
# Uncomment this line if you do not want debug logs
DEFINES += -DFSM_DEBUG
# Outpout folder holding generated files and compilation
BUILD = build
# Makfile search files in folder
VPATH = $(BUILD)
# Search C++ header files
INCLUDES = -I$(BUILD) -I../include

# Verbosity control
ifeq ($(VERBOSE),1)
Q :=
else
Q := @
endif

# C++14 is the minimum
STANDARD=--std=c++14

# Compilation flags
COMPIL_FLAGS = -Wall -Wextra -Wuninitialized -Wundef -Wunused       \
  -Wunused-result -Wunused-parameter -Wtype-limits -Wshadow         \
  -Wcast-align -Wcast-qual -Wconversion -Wfloat-equal               \
  -Wpointer-arith -Wswitch-enum -Wpacked -Wold-style-cast           \
  -Wdeprecated -Wvariadic-macros -Wvla -Wsign-conversion            \
  -D_GLIBCXX_ASSERTIONS

COMPIL_FLAGS += -Wno-switch-enum -Wno-undef -Wno-unused-parameter   \
  -Wno-old-style-cast -Wno-sign-conversion -Wcast-function-type

# Project compile and linker flags. We depends on Google tests
CXXFLAGS += $(STANDARD) $(COMPIL_FLAGS) `pkg-config --cflags gtest gmock`
LDFLAGS = `pkg-config --libs gtest gmock`

# Header file dependencies
# FIXME
# DEPFLAGS = -MT $@ -MMD -MP -MF $(BUILD)/$*$(PREFIX).Td
# POSTCOMPILE = $(Q)mv -f $(BUILD)/$*$(PREFIX).Td $(BUILD)/$*$(PREFIX).d

# Files to compile
TARGETS = Simple LKS Gumball LoopError Erroneous RichMan Wifi

# Mandatory else Makefile drops temporary files.
.PRECIOUS: $(BUILD)/%$(PREFIX)Tests.cpp $(BUILD)/%$(PREFIX)Tests.o

# Compile targets
.PHONY: all
all: $(TARGETS)

# Link the target
%: %$(PREFIX)Tests.o
	@echo "\033[0;32mLinking $@\033[0m"
	$(Q)$(CXX) $(INCLUDES) -o $@ $^ $(LDFLAGS)
	$(Q)mv $@ $(BUILD)

# Compile C++ source files
%$(PREFIX)Tests.o: %$(PREFIX)Tests.cpp
# FIXME $(BUILD)/%$(PREFIX)Tests.d
	@echo "\033[0;32mCompiling $<\033[0m"
	$(Q)$(CXX) $(DEPFLAGS) $(CXXFLAGS) $(INCLUDES) $(DEFINES) -c $(abspath $(BUILD)/$<) -o $(abspath $@)
	$(POSTCOMPILE)

# Create the UML diagrams
%.png: %.plantuml
	@echo "\033[0;32mGenerating $@\033[0m"
	$(Q)java -jar $(HOME)/plantuml-1.2022.5.jar $<
	$(Q)mv $@ $(BUILD)

%$(PREFIX)Tests.cpp: %.plantuml %.png $(PLANTUML_PARSER) Makefile
	@echo "\033[0;32mParsing $<\033[0m"
	$(Q)(cd $(BUILD) && ../$(PLANTUML_PARSER) ../$< $(PLANTUML_COMMAND_LINE))

.PHONY: clean
clean:
	@echo "\033[0;32mcleaning\033[0m"
	$(Q)rm -fr $(BUILD)

# Create the directory before compiling sources
$(TARGETS): | $(BUILD)
$(BUILD):
	@mkdir -p $(BUILD)

# Create the dependency files
$(BUILD)/%.d: ;
.PRECIOUS: $(BUILD)/%.d

# Header file dependencies
-include $(patsubst %,$(BUILD)/%$(PREFIX).d,$(basename %$(PREFIX).o))
