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

PARSER=../tool/Parser.py
BUILD = build
VPATH = $(BUILD) input
INCLUDES = -I$(BUILD) -Iinput -I. -I../tool

# Verbosity control
ifeq ($(VERBOSE),1)
Q :=
else
Q := @
endif

# C++14 (only because of std::make_unique not present in C++11)
STANDARD=--std=c++14

# Compilation flags
COMPIL_FLAGS = -Wall -Wextra -Wuninitialized -Wundef -Wunused       \
  -Wunused-result -Wunused-parameter -Wtype-limits -Wshadow         \
  -Wcast-align -Wcast-qual -Wconversion -Wfloat-equal               \
  -Wpointer-arith -Wswitch-enum -Wpacked -Wold-style-cast           \
  -Wdeprecated -Wvariadic-macros -Wvla -Wsign-conversion -D_GLIBCXX_ASSERTIONS

COMPIL_FLAGS += -Wno-switch-enum -Wno-undef -Wno-unused-parameter   \
  -Wno-old-style-cast -Wno-sign-conversion -Wcast-function-type

# Project flags
CXXFLAGS += $(STANDARD) $(COMPIL_FLAGS)

TARGETS = Simple.cpp

# Gumball.cpp: KO Tu pas generes correctement et boucle inifinie sur reset()
# LoopError.cpp: KO ne lance pas la boucle infinie qui devrait etre lancee par reset()
# Erroneous.cpp: OK viens de corriger les transitions
# Silver.cpp: KO entry du 1er etat pas appelle et on event KO
# LKS.cpp: KO LED_steering = Disable;\nservoing = Disable; sinon semble OK
# RichMan.cpp: OK
# Motor.cpp: OK setspeed(x)() et on event sinon OK

# Silver.cpp LoopError.cpp Erroneous.cpp Gumball.cpp LKS.cpp Motor.cpp RichMan.cpp

.PHONY: all
all: $(TARGETS)

%: %.o
	@echo "Linking $@"
	$(Q)cd $(BUILD) && $(CXX) $(INCLUDES) -o $@ $^ $(LDFLAGS)

%.o: $(BUILD)/%.cpp $(BUILD)/%.d
	@echo "Compiling $<"
	$(Q)$(CXX) $(CXXFLAGS) $(INCLUDES) $(DEFINES) -c $(abspath $<) -o $(abspath $(BUILD)/$@)
	@$(POSTCOMPILE)

%.png: %.plantuml
	@echo "Generating chart $<"
	$(Q)java -jar $(HOME)/plantuml-1.2022.5.jar $<
	$(Q)mv input/$@ $(BUILD)

%.cpp: %.plantuml %.png $(PARSER)
	@echo "Parsing $<"
	$(Q)(cd $(BUILD) && ../$(PARSER) ../$< hpp Controller)

.PHONY: clean
clean:
	@echo "cleaning"
	$(Q)rm -fr $(BUILD)

# Create the directory before compiling sources
$(TARGETS): | $(BUILD)
$(BUILD):
	@mkdir -p $(BUILD)

# Create the dependency files
$(BUILD)/%.d: ;
.PRECIOUS: $(BUILD)/%.d

# Header file dependencies
-include $(patsubst %,$(BUILD)/%.d,$(basename %.o))
