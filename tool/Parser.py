#!/usr/bin/env python3
###############################################################################
## PlantUML Statecharts (State Machine) Translator.
## Copyright (c) 2022 Quentin Quadrat <lecrapouille@gmail.com>
##
## This file is part of PlantUML Statecharts (State Machine) Translator.
##
## This tool is free software: you can redistribute it and/or modify it
## under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see http://www.gnu.org/licenses/.
###############################################################################

from pathlib import Path
from collections import defaultdict
from collections import deque
from datetime import date

import sys
import os
import networkx as nx

###############################################################################
### Colorful print
###############################################################################
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


###############################################################################
### Structure holding information after having parsed a PlantUML event.
### Example of PlantUML events:
###    get quarter
###    setSpeed(x)
###############################################################################
class Event(object):
    def __init__(self):
        # Unique name of the event
        self.name = ''
        # List of params
        self.params = []

    def header(self):
        if self.name == '':
            return 'void noEvent()'

        params = ''
        for p in self.params:
            if params != '':
                params += ', '
            params += p.upper() + ' const& ' + p.lower()
        return 'void ' + self.name + '(' + params + ')'

    def caller(self):
        if self.name == '':
            return 'noEvent()'

        i = 0
        params = ''
        for p in self.params:
            if params != '':
                params += ', ' + self.name.lower() + '_x[' + str(i) + ']'
                i += 1
            params += p.lower()
        if params != '' or self.name[-1] != ')':
            params = '(' + params + ')'
        return self.name + params

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, Event) and (self.name == other.name)

    def __str__(self):
        return self.definition()

    def __repr__(self):
        return self.definition()

###############################################################################
### Structure holding information after having parsed a PlantUML transition.
### Example of PlantUML transition:
###    source -> destination : event [ guard ] / action
###############################################################################
class Transition(object):
    def __init__(self):
        # Source state (upper case)
        self.origin = ''
        # Destination state (upper case)
        self.destination = ''
        # Event name
        self.event = Event()
        # Guard code (boolean expression)
        self.guard = ''
        # Action code (C++ code or pseudo code)
        self.action = ''

###############################################################################
### Structure holding information after having parsed a PlantUML state.
### Example of PlantUML state:
###     state : on event [ guard ] / action
###     state : entry / action
###     state : exit / action
###     state : do / activity
###############################################################################
class State(object):
    def __init__(self, name):
        # State name (upper case).
        self.name = name
        # Optional C++ comment
        self.comment = ''
        # Action to perform when entering the state.
        self.entering = ''
        # Action to perform when leaving the state.
        self.leaving = ''
        # Action to perform on event. FIXME only one managed
        self.event = Event()
        # state : do / activity
        # self.activity = ''

    def __str__(self):
        return self.name + ': ' + self.entering + ' / ' + self.leaving

###############################################################################
### Context of the parser translating a PlantUML file depicting a state machine
### into a C++ file state machine holding some unit tests.
### See https://plantuml.com/fr/state-diagram
###############################################################################
class Parser(object):

    ###########################################################################
    ### Default dummy constructor.
    ###########################################################################
    def __init__(self):
        # File descriptor of the plantUML file.
        self.fd = None
        # Name of the plantUML file.
        self.name = ''
        # The name of the C++ state machine class.
        self.class_name = ''
        # The name of the C++ state machine enum.
        self.enum_name = ''
        # List of tokens split line by line.
        self.tokens = []
        # List Cache tokens::size().
        self.nb_tokens = 0
        # List Cache the current line to display in error messages.
        self.lines = 0
        # Dictionnary of "event => (source, destination) states" needed to
        # compute tables of state transitions for each events.
        self.events = defaultdict(list)
        # Store all parsed information from plantUML file as a graph.
        self.graph = nx.DiGraph()
        self.initial_state = ''

    ###########################################################################
    ### Reset states
    ###########################################################################
    def reset(self):
        self.tokens = []
        self.nb_tokens = 0
        self.lines = 0
        self.events = defaultdict(list)
        self.graph = nx.DiGraph()
        self.initial_state = ''

    ###########################################################################
    ### Helper to raise an exception with a given and the current line where
    ### the error happened.
    ###########################################################################
    def parse_error(self, msg):
        raise Exception('Failed parsing ' + self.name + ' at line ' + str(self.lines) + ': ' + msg)

    ###########################################################################
    ### Print an error message and exit
    ###########################################################################
    def warning(self, msg):
        print(f"{bcolors.WARNING}   WARNING in the state machine " + self.name + ": "  + msg + f"{bcolors.ENDC}")

    ###########################################################################
    ### Read a single line, tokenize its symbols and store them in a list.
    ###########################################################################
    def parseline(self):
        self.nb_tokens = 0
        # Iterate for each empty line
        while self.nb_tokens == 0:
            self.lines += 1
            line = self.fd.readline()
            if not line:
                return False
            # Replace substring to be sure to parse correctly (ugly hack)
            #line = line.replace(':', ' : ')
            #line = line.replace('/', ' / ')
            line = line.replace('\\n--\\n', ' / ')
            #line = line.replace('[', ' [ ')
            #line = line.replace(']', ' ] ')
            #line = line.replace('\\n', ' ')
            # Tokenize the line
            self.tokens = line.strip().split(' ')
            while '' in self.tokens:
                self.tokens.remove('')
            self.nb_tokens = len(self.tokens)
            # Skip the line if detects a comment
            if (self.nb_tokens > 0) and (self.tokens[0] == '\''):
                self.nb_tokens = 0
                continue
            # Uncomment to help debuging
            #print('\n=========\nparseline: ' + line[:-1])
            #for t in self.tokens:
            #    print('token: "' + t + '"')
        return True

    ###########################################################################
    ### Add a state as graph node with its attribute if and only if it does not
    ### belong to this graph structure.
    ###########################################################################
    def add_state(self, name):
        if not self.graph.has_node(name):
            self.graph.add_node(name, data = State(name))

    ###########################################################################
    ### Parse the following plantUML code and store information of the analyse:
    ###    State : Entry / action
    ###    State : Exit / action
    ###    State : On event [ guard ] / action
    ###    State : Do / activity
    ###########################################################################
    def parse_state(self):
        name = self.tokens[0].upper()
        what = self.tokens[2].lower()

        # Create first a node if it does not exist. This is the simplest way
        # preventing smashing previously initialized values.
        self.add_state(name)

        # Update state fields
        st = self.graph.nodes[name]['data']
        if (what in ['entry', 'entering']) and (self.tokens[3] in ['/', ':']):
            st.entering = ' '.join(self.tokens[4:])
        elif (what in ['exit', 'leaving']) and (self.tokens[3] in ['/', ':']):
            st.leaving = ' '.join(self.tokens[4:])
        elif what == 'comment':
            st.comment = ' '.join(self.tokens[4:])
        # 'on event' is not sugar syntax to a real transition: since it disables
        # 'entry' and 'exit' actions but we want create a real graph edege to
        # help us on graph theory traversal algorithm (like finding cycles).
        elif what == 'on':
            self.tokens = [ name, '->', name, ':' ] + self.tokens[3:]
            self.parse_transition(True)
            return
        elif what == 'do':
            self.parse_error('do / activity not yet implemented')
        else:
            self.parse_error('Bad syntax describing a state')

    ###########################################################################
    ### Parse a guar
    ### TODO manage things like "when(event)" or "event(x)"
    ###########################################################################
    def concat_tokens(self, toks):
        code = ''
        for t in toks:
            code += t
            code += ' '
        return code[:-1]

    ###########################################################################
    ### Parse an event.
    ### TODO for the moment we do not manage boolean expression
    ### TODO manage builtins such as "when(event)" or "after(x)"
    ###########################################################################
    def parse_event(self, event, toks):
        if len(toks) == 0:
            event.name = ''
            event.params = []
            return
        parameters = False
        event.name = toks[0].lower()
        for t in toks[1:]:
            if t[0] == '(':
                parameters = True
            elif t[0] == ')':
                parameters = False
                if event[-1] == ',':
                    event.params.append(event[:-1])
            if not parameters:
                event.name += t.capitalize()
            else:
                event.name += t.upper() + 'const& ' + t + ','

    ###########################################################################
    ### Parse the following plantUML code and store information of the analyse:
    ###    origin state -> destination state : event [ guard ] / action
    ###    destination state <- origin state : event [ guard ] / action
    ### In which event, guard and action are optional.
    ###########################################################################
    def parse_transition(self, as_state = False):
        tr = Transition()

        # Analyse the following plantUML code: "origin state -> destination state ..."
        # Analyse the following plantUML code: "destination state <- origin state ..."
        if self.tokens[1] == '->' or self.tokens[1] == '-->':
            tr.origin, tr.destination = self.tokens[0].upper(), self.tokens[2].upper()
        else:
            tr.origin, tr.destination = self.tokens[2].upper(), self.tokens[0].upper()

        self.add_state(tr.origin)
        self.add_state(tr.destination)

        # Initial state
        if tr.origin == '[*]':
            self.initial_state = tr.destination

        # Analyse the following optional plantUML code: ": event ..."
        if (self.nb_tokens > 3) and (self.tokens[3] == ':'):
            i = 4
            # Halt on the end of line or when detecting the beginning of a guard '[' or an action '/'
            while (i < self.nb_tokens) and (self.tokens[i] not in ['[', '/']):
                i += 1
            self.parse_event(tr.event, self.tokens[4:i])

            # Events are optional. If not given, we use them as anonymous internal event.
            # Store them in a dictionary: "event => (origin, destination) states" to create
            # the state transition for each event.
            self.events[tr.event].append((tr.origin, tr.destination))

            # Analyse the following optional plantUML code: "[ guard ] ..."
            # Guards are optional. When optional they always return true.
            if (i < self.nb_tokens) and (self.tokens[i] == '['):
                i, j = i + 1, i + 1
                while (i < self.nb_tokens) and (self.tokens[i] != ']'):
                    i += 1
                if self.tokens[i] != ']':
                    self.parse_error("Unterminated guard close")
                tr.guard = ' '.join(self.tokens[j:i])
                i = i + 1

            # Analyse the following optional plantUML code: "/ action"
            if (i < self.nb_tokens) and (self.tokens[i] == '/'):
                i, j = i + 1, i + 1
                while (i < self.nb_tokens) and (self.tokens[i] != ']'):
                    i += 1
                tr.action = ' '.join(self.tokens[j:i])

            # Distinguish a transition cycling to its own state from the "on event" on the state
            if as_state and (tr.origin == tr.destination):
                if tr.action == '':
                    tr.action = '// Dummy action'
                self.graph.nodes[tr.origin]['data'].event.name = tr.action
                tr.action = ''

        # Store parsed information as edge of the graph
        self.graph.add_edge(tr.origin, tr.destination, data=tr)

    ###########################################################################
    ### Code generator: add a separator line for function.
    ###########################################################################
    def generate_function_line_separator(self):
        self.fd.write('//*****************************************************************************\n')

    ###########################################################################
    ### Code generator: add a dummy function comment.
    ###########################################################################
    def generate_function_comment(self, comment):
        self.generate_function_line_separator()
        if comment == '':
            self.fd.write('//! \\brief\n')
        else:
            self.fd.write('//! \\brief ' + comment + '\n')
        self.generate_function_line_separator()

    ###########################################################################
    ### Code generator: add a separator line for methods.
    ###########################################################################
    def generate_method_line_separator(self):
        self.fd.write('    //-------------------------------------------------------------------------\n')

    ###########################################################################
    ### Code generator: add a dummy method comment.
    ###########################################################################
    def generate_method_comment(self, comment):
        self.generate_method_line_separator()
        if comment == '':
            self.fd.write('    //! \\brief\n')
        else:
            self.fd.write('    //! \\brief ' + comment + '\n')
        self.generate_method_line_separator()

    ###########################################################################
    ### Code generator: add the header file.
    ### TODO include or insert custom header like done with flex/bison
    ###########################################################################
    def generate_header(self, hpp):
        if hpp:
            self.fd.write('#ifndef ' + name + '_HPP\n')
            self.fd.write('#  define ' + name + '_HPP\n\n')
            self.fd.write('#  include "StateMachine.hpp"\n')
        else:
            self.fd.write('#include "StateMachine.hpp"\n')
        self.fd.write('\n')
        self.generate_custom_macro('// Custom header file to implement macros to complete the compilation.',
                                   '#  include "' + self.class_name + 'Macros.hpp"')
        self.fd.write('\n')

    ###########################################################################
    ### Code generator: add the footer file.
    ### TODO include or insert custom footer like done with flex/bison
    ###########################################################################
    def generate_footer(self, hpp):
        if hpp:
            self.fd.write('#endif // ' + self.class_name.upper() + '_HPP')
        self.fd.write('// This file as been generated the ' +
            date.today().strftime("%B %d, %Y\n"))

    ###########################################################################
    ### Code generator: add the function that stringify states.
    ###########################################################################
    def generate_stringify(self):
        self.generate_function_comment('Convert enum states to human readable string.')
        self.fd.write('static inline const char* stringify(' + self.enum_name + ' const state)\n')
        self.fd.write('{\n')
        self.fd.write('    static const char* s_states[] =\n')
        self.fd.write('    {\n')
        for state in list(self.graph.nodes):
            if state == '[*]':
                continue
            self.fd.write('        [' + self.enum_name + '::' + state + '] = "' + state + '",\n')
        self.fd.write('    };\n')
        self.fd.write('\n')
        self.fd.write('    return s_states[state];\n')
        self.fd.write('};\n\n')

    ###########################################################################
    ### Code generator: add the state machine constructor method.
    ###########################################################################
    def generate_pointer_function(self, what, state_name):
        dict = {
                'guard' : 'onGuardingState',
                'entering' : 'onEnteringState',
                'leaving' : 'onLeavingState',
                'activity' : 'doActivityState',
                'onevent' : 'onEventState', # FIXME missing onEventXXXState once dealing with multiple events
        }
        self.fd.write('            .' + what +' = &' + self.class_name + '::' + dict[what] + state_name + ',\n')

    ###########################################################################
    ### Code generator: add the state machine constructor method.
    ###########################################################################
    def generate_table_states(self, states):
        empty = True
        for state in states:
            if state == '[*]':
                continue

            if 'data' not in self.graph.nodes[state]:
                continue

            s = self.graph.nodes[state]['data']
            if (s.entering == '') and (s.leaving == '') and (s.event.name == ''):
                continue

            self.fd.write('        m_states[' + self.enum_name + '::' + s.name + '] =\n')
            self.fd.write('        {\n')
            if s.entering != '':
                self.generate_pointer_function('entering', s.name)
            if s.leaving != '':
                self.generate_pointer_function('leaving', s.name)
            if s.event.name != '':
                self.generate_pointer_function('onevent', s.name)
            # TODO
            #if s.activity != '':
            #    self.generate_pointer_function('activity', s.name)
            self.fd.write('        };\n')
            empty = False
        if empty:
            self.fd.write('        // Note: no table of states created since no state will do actions!\n')

    ###########################################################################
    ### Code generator: add the state machine constructor method.
    ###########################################################################
    def generate_constructor(self):
        states = list(self.graph.nodes)
        self.generate_method_comment('Default dummy constructor. Start with state ' + self.initial_state + '.')
        self.fd.write('    ' + self.class_name + '() : StateMachine(' + self.enum_name + '::' + self.initial_state + ')\n')
        self.fd.write('    {\n')
        self.generate_table_states(states)
        self.generate_custom_macro('\n        // Complete your constructor',
                                   '        CUSTOM_' + self.class_name.upper() + '_CONSTRUCTOR')
        d = self.graph.nodes['[*]']['data']
        if d.entering != '':
            self.fd.write(d.entering)
            if d.entering[-2] != '}':
                self.fd.write(';\n')
        self.fd.write('    }\n\n')

    ###########################################################################
    ### Code generator: add the state machine reset method.
    ###########################################################################
    def generate_reset(self):
        if self.graph.nodes['[*]']['data'].entering == '':
            return
        self.generate_method_comment('Reset the state machine.')
        self.fd.write('    void reset()\n')
        self.fd.write('    {\n')
        self.fd.write('        StateMachine::reset();\n')
        self.fd.write('        onEnteringInitialState();\n')
        self.fd.write('    }\n\n')

    ###########################################################################
    ### Code generator: add all methods associated with external events.
    ###########################################################################
    def generate_external_events(self):
        for event, arcs in self.events.items():
            if event.name == '':
                continue

            self.generate_method_comment('External event.')
            self.fd.write('    ' + event.header() + '\n')
            self.fd.write('    {\n')
            self.fd.write('        LOGD("[EVENT %s]\\n", __func__);\n\n')
            self.fd.write('        static Transitions s_transitions =\n')
            self.fd.write('        {\n')
            for origin, destination in arcs:
                tr = self.graph[origin][destination]['data']
                self.fd.write('            {\n')
                self.fd.write('                ' + self.enum_name + '::' + origin + ',\n')
                self.fd.write('                {\n')
                self.fd.write('                    ' + self.enum_name + '::' + destination + ',\n')
                if tr.guard != '':
                    if origin != '[*]':
                        self.fd.write('                    &' + self.class_name + '::onGuardingTransition' + origin + '_' + destination + ',\n')
                    else:
                        self.fd.write('                    &' + self.class_name + '::onGuardingTransition_' + destination + ',\n')
                else:
                    self.fd.write('                    nullptr,\n')
                if tr.action != '':
                    self.fd.write('                    &' + self.class_name + '::onTransitioning' + origin + '_' + destination + ',\n')
                else:
                    self.fd.write('                    nullptr,\n')
                self.fd.write('                },\n')
                self.fd.write('            },\n')
            self.fd.write('        };\n')
            self.fd.write('\n')
            self.fd.write('        transition(s_transitions);\n')
            self.fd.write('    }\n\n')

    ###########################################################################
    ### Code generator: Transitions reactions.
    ###########################################################################
    def generate_states_transitions_reactions(self):
        transitions = list(self.graph.edges)
        for origin, destination in transitions:
            tr = self.graph[origin][destination]['data']
            if tr.guard != '':
                self.generate_method_comment('Guard the transition from state ' + origin  + '\n    //! to state ' + destination + '.')
                if origin != '[*]':
                    self.fd.write('    bool onGuardingTransition' + origin + '_' + destination + '()\n')
                else:
                    self.fd.write('    bool onGuardingTransition_' + destination + '()\n')
                self.fd.write('    {\n')
                self.fd.write('        const bool guard = (' + tr.guard + ');\n')
                self.fd.write('        LOGD("[GUARD ' + origin + ' --> ' + destination + ': ' + tr.guard + '] result: %s\\n",\n')
                self.fd.write('             (guard ? "true" : "false"));\n')
                self.fd.write('        return guard;\n')
                self.fd.write('    }\n\n')

            if tr.action != '':
                self.generate_method_comment('Do the action when transitioning from state ' + origin + '\n    //! to state ' + destination + '.')
                self.fd.write('    void onTransitioning' + origin + '_' + destination + '()\n')
                self.fd.write('    {\n')
                self.fd.write('        LOGD("[TRANSITION ' + origin + ' --> ' + destination + ': ' + tr.action + ']\\n");\n')
                self.fd.write('        ' + tr.action + ';\n')
                self.fd.write('    }\n\n')

    ###########################################################################
    ### Code generator: States reactions.
    ###########################################################################
    def generate_states_states_reactions(self):
        nodes = list(self.graph.nodes)
        for node in nodes:
            if 'data' not in self.graph.nodes[node]:
                continue
            state = self.graph.nodes[node]['data']
            if state.entering != '':
                self.generate_method_comment('Do the action when entering the state ' + state.name + '.')
                if state.name != '[*]':
                    self.fd.write('    void onEnteringState' + state.name + '()\n')
                else:
                    self.fd.write('    void onEnteringInitialState()\n')
                self.fd.write('    {\n')
                self.fd.write('        LOGD("[ENTERING STATE ' + state.name + ']\\n");\n')
                self.fd.write('        ' + state.entering)
                if state.entering[-2] != '}':
                    self.fd.write(';\n')
                self.fd.write('    }\n\n')

            if state.leaving != '':
                self.generate_method_comment('Do the action when leaving the state ' + state.name + '.')
                self.fd.write('    void onLeavingState' + state.name + '()\n')
                self.fd.write('    {\n')
                self.fd.write('        LOGD("[LEAVING STATE ' + state.name + ']\\n");\n')
                self.fd.write('        ' + state.leaving + ';\n')
                self.fd.write('    }\n\n')

            if state.event.name != '':
                self.generate_method_comment('Do the action on event XXX ' + state.name + '.')
                self.fd.write('    void onEventState' + state.name + '()\n')
                self.fd.write('    {\n')
                self.fd.write('        LOGD("[EVENT STATE ' + state.name + ']\\n");\n')
                self.fd.write('        ' + state.event.name + ';\n')
                self.fd.write('    }\n\n')

    ###########################################################################
    ### Code generator: add the state machine class and all its methods.
    ###########################################################################
    def generate_state_machine_class(self):
        self.generate_function_comment('State machine concrete implementation.')
        self.fd.write('class ' + self.class_name + ' : public StateMachine<')
        self.fd.write(self.class_name + ', ' + self.enum_name + '>\n')
        self.fd.write('{\n')
        self.fd.write('public: // Constructor and external events\n\n')
        self.generate_constructor()
        self.generate_reset()
        self.generate_external_events()
        self.fd.write('private: // Guards and reactions\n\n')
        self.generate_states_transitions_reactions()
        self.generate_states_states_reactions()
        name = self.class_name.upper()
        self.generate_custom_macro('    // Define your member variables functions',
                                   'private:\n    CUSTOM_' + name + '_MEMBER_FUNCTIONS'
                                   '\n    CUSTOM_' + name + '_MEMBER_VARIABLES')
        self.fd.write('};\n\n')

    ###########################################################################
    ###
    ###########################################################################
    def generate_custom_macro(self, comment, code):
        self.fd.write(comment)
        self.fd.write('\n#if defined(CUSTOMIZE_STATE_MACHINE') # self.class_name.upper()
        self.fd.write(')\n')
        self.fd.write(code)
        self.fd.write('\n')
        self.fd.write('#endif\n')

    ###########################################################################
    ### Code generator: add the enum of the states of the state machine.
    ###########################################################################
    def generate_state_enums(self):
        self.generate_function_comment('States of the state machine.')
        self.fd.write('enum ' + self.enum_name + '\n{\n')
        self.fd.write('    // Client states\n')
        for state in list(self.graph.nodes):
            if state == '[*]':
                continue
            self.fd.write('    ' + state + ',')
            comment = self.graph.nodes[state]['data'].comment
            if comment != '':
                self.fd.write(' //!< ' + comment)
            self.fd.write('\n')
        self.fd.write('    // Mandatory states\n')
        self.fd.write('    IGNORING_EVENT, CANNOT_HAPPEN, MAX_STATES\n')
        self.fd.write('};\n\n')

    ###########################################################################
    ### Code generator: Add an example of how using this state machine. It
    ### gets all cycles in the graph and try them. This example can be used as
    ### partial unit test.
    ### FIXME Manage guard logic to know where to pass in edges.
    ### FIXME Check if two branches from a parent node are mutually exclusive.
    ###########################################################################
    def generate_unit_tests(self, cppfile):
        states = list(self.graph.nodes)

        # Cycles may not start from initial state, therefore do some permutation
        # to be sure to start by the initial state.
        cycles = []
        for cycle in list(nx.simple_cycles(self.graph)):
            try:
                index = cycle.index(self.initial_state)
                cycles.append(cycle[index:] + cycle[:index])
                cycles[-1].append(cycles[-1][0])
            except Exception as ValueError:
                continue

        self.fd.write('#include <iostream>\n')
        self.fd.write('#include <cassert>\n')
        self.fd.write('#include <cstring>\n\n')
        self.generate_function_comment('Compile with one of the following line:\n' +
                                       '//! g++ --std=c++14 -Wall -Wextra -Wshadow -DFSM_DEBUG ' + os.path.basename(cppfile) + '\n' +
                                       '//! g++ --std=c++14 -Wall -Wextra -Wshadow -DFSM_DEBUG -DCUSTOMIZE_STATE_MACHINE ' + os.path.basename(cppfile))
        self.fd.write('int main()\n')
        self.fd.write('{\n')
        self.fd.write('    ' + self.class_name + ' ' + 'fsm;\n\n')
        self.generate_custom_macro('    // Add here initial variables', '    CUSTOM_' + self.class_name.upper() + '_INIT_UNIT_TEST_VARIABLES')
        self.fd.write('\n    std::cout << "===========================================" << std::endl;\n')
        self.fd.write('    std::cout << "Current state: " << fsm.c_str() << std::endl;\n')
        self.fd.write('    std::cout << "===========================================" << std::endl;\n')
        self.fd.write('    assert(fsm.state() == ' + self.enum_name + '::' + self.initial_state + ');\n')
        self.fd.write('    assert(strcmp(fsm.c_str(), "' + self.initial_state + '") == 0);\n')
        self.fd.write('    LOGD("Test: ok\\n");\n\n')
        for cycle in cycles:
            self.fd.write('    std::cout << "===========================================" << std::endl;\n')
            self.fd.write('    std::cout << "Cycle:')
            for c in cycle:
                self.fd.write(' ' + c)
            self.fd.write('" << std::endl;\n')
            self.fd.write('    std::cout << "===========================================" << std::endl;\n')
            self.fd.write('    fsm.reset();\n')
            for i in range(len(cycle) - 1):
                event = self.graph[cycle[i]][cycle[i+1]]['data'].event
                if event.name != '':
                    self.fd.write('    fsm.' + event.caller() + ';\n')
                if (i == len(cycle) - 2):
                    if self.graph[cycle[i+1]][cycle[1]]['data'].event.name == '':
                        self.fd.write('    #warning "Malformed state machine"\n\n')
                    else:
                        self.fd.write('    std::cout << "Current state: " << fsm.c_str() << std::endl;\n')
                        self.fd.write('    assert(fsm.state() == ' + self.enum_name + '::' + cycle[i+1] + ');\n')
                        self.fd.write('    assert(strcmp(fsm.c_str(), "' + cycle[i+1] + '") == 0);\n')
                        self.fd.write('    LOGD("Assertions: ok\\n");\n\n')
                elif self.graph[cycle[i+1]][cycle[i+2]]['data'].event.name != '':
                        self.fd.write('    std::cout << "Current state: " << fsm.c_str() << std::endl;\n')
                        self.fd.write('    assert(fsm.state() == ' + self.enum_name + '::' + cycle[i+1] + ');\n')
                        self.fd.write('    assert(strcmp(fsm.c_str(), "' + cycle[i+1] + '") == 0);\n')
                        self.fd.write('    LOGD("Assertions: ok\\n");\n\n')


        self.fd.write('    std::cout << "Unit test done with success" << std::endl;\n\n')
        self.fd.write('    return EXIT_SUCCESS;\n')
        self.fd.write('}\n\n')

    ###########################################################################
    ### Code generator: entry point generating a C++ file.
    ###########################################################################
    def generate_code(self, cppfile):
        filename, extension = os.path.splitext(cppfile)
        hpp = True if extension in ['.h', '.hpp', '.hh', '.hxx'] else False

        self.fd = open(cppfile, 'w')
        self.generate_header(hpp)
        self.generate_state_enums()
        self.generate_stringify()
        self.generate_state_machine_class()
        if not hpp:
            self.generate_unit_tests(cppfile)
        self.generate_footer(hpp)
        self.fd.close()
        self.generate_macros(cppfile)

    ###########################################################################
    ### Code generator: generate the header file for macros.
    ###########################################################################
    def generate_macros(self, cppfile):
        filename = self.class_name + 'Macros.hpp'
        path = os.path.join(os.path.dirname(cppfile), filename)
        if os.path.exists(path):
            return

        name = self.class_name.upper()
        guard_name = filename.upper().replace('.', '_')
        self.fd = open(path, 'w')
        self.fd.write('#ifndef ' + guard_name + '\n')
        self.fd.write('#  define ' + guard_name + '\n\n')
        self.fd.write('#  define CUSTOM_' + name + '_CONSTRUCTOR\n\n')
        self.fd.write('#  define CUSTOM_' + name + '_MEMBER_FUNCTIONS\n\n')
        self.fd.write('#  define CUSTOM_' + name + '_MEMBER_VARIABLES\n\n')
        self.fd.write('#  define CUSTOM_' + name + '_INIT_UNIT_TEST_VARIABLES\n\n')
        self.fd.write('#endif // ' + guard_name + '\n')
        self.fd.close()

    ###########################################################################
    ### Count the total number of events which shall be > 1
    ###########################################################################
    def verify_number_of_events(self):
        for e in self.events:
            if e.name != '':
                return

        str = ''
        cycle = list(nx.simple_cycles(self.graph))[0]
        for c in cycle:
            str += ' ' + c
        self.warning('The state machine shall have at least one event to prevent infinite loop.'
                     + '\n   For example:' + str)

    ###########################################################################
    ### Verify for each state if transitionings are dereminist.
    ### Case 1: each state having more than 1 transition in where one transition
    ###         does not have event and guard.
    ### Case 2: several transitions and guards does not check all cases (for
    ###         example the Richman case with init quarters < 0. TODO
    ###########################################################################
    def verify_transition(self):
        # Case 1
        for state in list(self.graph.nodes()):
            out = list(self.graph.neighbors(state))
            if len(out) <= 1:
                continue
            for d in out:
                data = self.graph[state][d]['data']
                if (data.event.name == '') and (data.guard == ''):
                    self.warning('The state ' + state + ' has an issue with its transitions: it has'
                                 ' several possible ways\n   while the way to state ' + d +
                                 ' is always true and therefore will be always a candidate and transition'
                                 ' to other states is\n   non determinist.')

    ###########################################################################
    ### Check if the state machine is determinist or not.
    ### TODO for each node: are out edges mutually exclusive ?
    ### TODO all states are reachable ?
    ### TODO how to analyse guards ? How to use networkx + guards ?
    ### TODO cycles where all guards are true or no events
    ###########################################################################
    def is_state_machine_determinist(self):
        self.verify_number_of_events()
        self.verify_transition()
        pass

    ###########################################################################
    ### Some information parsed by PlantUML can be reorganized.
    ###########################################################################
    def finalize_machine(self):
        self.manage_noevents()

    ###########################################################################
    ### Manage transitions without events
    ###########################################################################
    def manage_noevents(self):
        # Make unique the list of states that does not have event on their
        # outout edges
        states = []
        for s in list(self.graph.nodes()):
            for d in list(self.graph.neighbors(s)):
                tr = self.graph[s][d]['data']
                if s == '[*]' and tr.event.name == '' and tr.guard != '':
                    states.append(s)
                elif s != '[*]' and tr.event.name == '':
                    states.append(s)
        states = list(set(states))

        # Generate the code of direct transitions to destiantion states
        code = ''
        for s in states:
            if s == '[*]': # Part of the constructor
                code = '\n        onEnteringInitialState()'
            else:
                count = 0
                code = '\n        LOGD("[STATE ' + s +  '] Transitioning by internal event\\n");\n'
                for d in list(self.graph.neighbors(s)):
                    tr = self.graph[s][d]['data']
                    if tr.guard != '':
                        code += '        if (onGuardingTransition' + s + '_' + d + '())\n'
                        code += '        {\n'
                        code += '            static StateMachine<' + self.class_name + ', ' + self.enum_name + '>::Transition tr =\n'
                        code += '            {\n'
                        code += '                .destination = ' + self.enum_name + '::' + d + ',\n'
                        code += '                .guard = &' + self.class_name + '::onGuardingTransition' + s + '_' + d + ',\n'
                        if tr.action != '':
                            code += '                .action = &' + self.class_name + '::onTransitioning' + s + '_' + d + ',\n'
                        code += '            };\n'
                        code += '            transition(&tr);\n'
                        code += '            return ;\n'
                        code += '        }\n'
                    else:
                        if count == 1:
                            code += '#warning "Undeterminist State machine"\n'
                        code += '        static StateMachine<' + self.class_name + ', ' + self.enum_name + '>::Transition tr =\n'
                        code += '        {\n'
                        code += '            .destination = ' + self.enum_name + '::' + d + ',\n'
                        if tr.action != '':
                            code += '            .action = &' + self.class_name + '::onTransitioning' + s + '_' + d + ',\n'
                        code += '        };\n'
                        code += '        transition(&tr)'
                    count += 1
            self.graph.nodes[s]['data'].entering += code

    ###########################################################################
    ### Entry point of the plantUML file parser.
    ### umlfile: path to the plantuml file.
    ### cppfile: path to the generated C++ file.
    ### classname: class name of the state machine.
    ###########################################################################
    def translate(self, umlfile, cppfile, classname):
        if not os.path.isfile(umlfile):
            print('File path {} does not exist. Exiting...'.format(umlfile))
            sys.exit()

        self.reset()
        self.fd = open(umlfile, 'r')
        self.name = Path(umlfile).stem
        self.class_name = self.name + classname
        self.enum_name = classname + 'States'

        # PlantUML file shall start by '@startuml'
        if (not self.parseline()) or (self.tokens[0] != '@startuml'):
           self.parse_error('Bad plantuml file: did not find @startuml')

        # Since PlantUML instruction by line read a line one by one
        while self.parseline():
            if (self.nb_tokens >= 3) and (self.tokens[1] in ['->', '-->', '<-', '<--']):
                self.parse_transition()
            if (self.nb_tokens >= 4) and (self.tokens[1] == ':'):
                self.parse_state()
            elif self.tokens[0] == '@enduml':
                break
            elif self.tokens[0] in ['hide', 'scale', 'skin']:
                continue

        self.fd.close()
        self.is_state_machine_determinist()
        self.finalize_machine()
        self.generate_code(cppfile)

###############################################################################
### Entry point.
### argv[1] Mandatory: path of the state machine in plantUML format.
### argv[2] Mandatory: path of the C++ file to create.
### argv[3] Optional: Postfix name for the state machine class.
###############################################################################
def main():
    argc = len(sys.argv)
    if argc < 3:
        print('Command line: ' + sys.argv[1] + ' <plantuml file> <path generated C++ file> [ state machine name ]')
        sys.exit(-1)

    p = Parser()
    p.translate(sys.argv[1], sys.argv[2], 'Controller' if argc == 3 else sys.argv[3])

if __name__ == '__main__':
    main()
