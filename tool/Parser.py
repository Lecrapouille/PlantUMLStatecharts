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

import sys, os, re, itertools
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
        # Initial / final states
        self.initial_state = ''
        self.final_state = ''

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
        self.final_state = ''

    ###########################################################################
    ### Is the generated file should be a C++ source file or header file ?
    ###########################################################################
    def is_hpp_file(self, file):
        filename, extension = os.path.splitext(file)
        return True if extension in ['.h', '.hpp', '.hh', '.hxx'] else False

    ###########################################################################
    ### Print a warning message
    ###########################################################################
    def warning(self, msg):
        print(f"{bcolors.WARNING}   WARNING in the state machine " + self.name + ": "  + msg + f"{bcolors.ENDC}")

    ###########################################################################
    ### Print an error message and exit
    ###########################################################################
    def fatal(self, msg):
        print(f"{bcolors.FAIL}   FATAL in the state machine " + self.name + ": "  + msg + f"{bcolors.ENDC}")
        sys.exit(-1)

    ###########################################################################
    ### Helper to raise an exception with a given and the current line where
    ### the error happened.
    ###########################################################################
    def parse_error(self, msg):
        print(f"{bcolors.FAIL}   Failed parsing " + self.name + " at line " + str(self.lines) + ": " + msg + f"{bcolors.ENDC}")
        sys.exit(-1)

    ###########################################################################
    ### Check if the token match for a C/C++ variable name
    ###########################################################################
    def assert_valid_C_name(self, token):
        if token in ['*', '[*]']:
            return
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", token):
            self.parse_error('Invalid C++ name "' + token + '"')

    ###########################################################################
    ### Add a state as graph node with its attribute if and only if it does not
    ### belong to this graph structure.
    ###########################################################################
    def add_state(self, name):
        self.assert_valid_C_name(name)
        if not self.graph.has_node(name):
            self.graph.add_node(name, data = State(name))

    ###########################################################################
    ### Add a transition as graph arc with its attribute.
    ###########################################################################
    def add_transition(self, tr):
        self.graph.add_edge(tr.origin, tr.destination, data=tr)

    ###########################################################################
    ### Return cycles in the graph.
    ### Cycles may not start from initial state, therefore do some permutation
    ### to be sure to start by the initial state.
    ###########################################################################
    def graph_cycles(self):
        # Cycles may not start from initial state, therefore do some permutation
        # to be sure to start by the initial state.
        cycles = []
        for cycle in list(nx.simple_cycles(self.graph)):
            index = -1
            # Initial state may have several transitions so search the first
            for n in self.graph.neighbors(self.initial_state):
                try:
                    index = cycle.index(n)
                    break
                except Exception as ValueError:
                    continue
            if index != -1:
                cycles.append(cycle[index:] + cycle[:index])
                cycles[-1].append(cycles[-1][0])
        return cycles

    ###########################################################################
    ### Iterate over edges in a depth-first-search (DFS).
    ###########################################################################
    def graph_dfs(self):
         return list(nx.dfs_edges(self.graph, source=self.initial_state))

    ###########################################################################
    ### Get all paths from all sources to sinks 
    ###########################################################################
    def graph_all_paths_to_sinks(self):
         all_paths = []
         sink_nodes = [node for node, outdegree in self.graph.out_degree(self.graph.nodes()) if outdegree == 0]
         source_nodes = [node for node, indegree in self.graph.in_degree(self.graph.nodes()) if indegree == 0]
         for (source, sink) in [(source, sink) for sink in sink_nodes for source in source_nodes]:
             for path in nx.all_simple_paths(self.graph, source=source, target=sink):
                all_paths.append(path)
         return all_paths

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
        self.fd.write('// This file as been generated the ')
        self.fd.write(date.today().strftime("%B %d, %Y\n"))
        if hpp:
            self.fd.write('#ifndef ' + self.class_name.upper() + '_HPP\n')
            self.fd.write('#  define ' + self.class_name.upper() + '_HPP\n\n')
            self.fd.write('#  include "StateMachine.hpp"\n\n')
            # FIXME broken indentation
            self.generate_custom_macro('// Custom header file to implement macros to complete the compilation.',
                                       '#  include "' + self.class_name + 'Macros.hpp"')
        else:
            self.fd.write('#include "StateMachine.hpp"\n\n')
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

    ###########################################################################
    ### Code generator: add the enum of the states of the state machine.
    ###########################################################################
    def generate_state_enums(self):
        self.generate_function_comment('States of the state machine.')
        self.fd.write('enum ' + self.enum_name + '\n{\n')
        self.fd.write('    // Client states\n')
        for state in list(self.graph.nodes):
            self.fd.write('    ' + self.state_name(state) + ',')
            comment = self.graph.nodes[state]['data'].comment
            if comment != '':
                self.fd.write(' //!< ' + comment)
            self.fd.write('\n')
        self.fd.write('    // Mandatory states\n')
        self.fd.write('    IGNORING_EVENT, CANNOT_HAPPEN, MAX_STATES\n')
        self.fd.write('};\n\n')

    ###########################################################################
    ### Code generator: add the function that stringify states.
    ###########################################################################
    def generate_stringify_function(self):
        self.generate_function_comment('Convert enum states to human readable string.')
        self.fd.write('static inline const char* stringify(' + self.enum_name + ' const state)\n')
        self.fd.write('{\n')
        self.fd.write('    static const char* s_states[] =\n')
        self.fd.write('    {\n')
        for state in list(self.graph.nodes):
            self.fd.write('        [' + self.enum_name + '::' + self.state_name(state) + '] = "' + state + '",\n')
        self.fd.write('    };\n')
        self.fd.write('\n')
        self.fd.write('    return s_states[state];\n')
        self.fd.write('};\n\n')

    ###########################################################################
    ### Convert the state name
    ###########################################################################
    def state_name(self, state):
        if state == '[*]':
            return 'CONSTRUCTOR'
        if state == '*':
            return 'DESTRUCTOR'
        return state

    ###########################################################################
    ### Code generator: add the state machine constructor method.
    ###########################################################################
    def generate_pointer_function(self, what, state):
        dict = {
                'guard' : 'onGuardingState',
                'entering' : 'onEnteringState',
                'leaving' : 'onLeavingState',
                'activity' : 'doActivityState',
                'onevent' : 'onEventState', # FIXME missing onEventXXXState once dealing with multiple events
        }
        self.fd.write('            .' + what +' = &' + self.class_name + '::' + dict[what] + self.state_name(state) + ',\n')

    ###########################################################################
    ### Code generator: add the state machine constructor method.
    ###########################################################################
    def generate_table_states(self, states):
        empty = True
        for state in states:
            if 'data' not in self.graph.nodes[state]:
                continue

            s = self.graph.nodes[state]['data']
            if (s.entering == '') and (s.leaving == '') and (s.event.name == ''):
                continue

            self.fd.write('        m_states[' + self.enum_name + '::' + self.state_name(s.name) + '] =\n')
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
        self.generate_method_comment('Default dummy constructor. Start from initial state and call it actions.')
        self.fd.write('    ' + self.class_name + '() : StateMachine(' + self.enum_name + '::' + self.state_name(self.initial_state) + ')\n')
        self.fd.write('    {\n')
        self.generate_table_states(states)
        self.generate_custom_macro('\n        // Complete your constructor',
                                   '        CUSTOM_' + self.class_name.upper() + '_CONSTRUCTOR')
        self.fd.write('        onEnteringState' + self.state_name(self.initial_state) + '();\n')
        self.fd.write('    }\n\n')

    ###########################################################################
    ### Code generator: add the state machine reset method.
    ###########################################################################
    def generate_reset(self):
        self.generate_method_comment('Reset the state machine.')
        self.fd.write('    void reset()\n')
        self.fd.write('    {\n')
        self.fd.write('        StateMachine::reset();\n')
        self.fd.write('        onEnteringState' + self.state_name(self.initial_state) + '();\n')
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
                    self.fd.write('                    &' + self.class_name + '::onGuardingTransition')
                    self.fd.write(self.state_name(origin) + '_' + self.state_name(destination) + ',\n')
                else:
                    self.fd.write('                    nullptr,\n')
                if tr.action != '':
                    self.fd.write('                    &' + self.class_name + '::onTransitioning')
                    self.fd.write(self.state_name(origin) + '_' + self.state_name(destination) + ',\n')
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
                self.fd.write('    bool onGuardingTransition' + self.state_name(origin) + '_' + self.state_name(destination) + '()\n')
                self.fd.write('    {\n')
                self.fd.write('        const bool guard = (' + tr.guard + ');\n')
                self.fd.write('        LOGD("[GUARD ' + origin + ' --> ' + destination + ': ' + tr.guard + '] result: %s\\n",\n')
                self.fd.write('             (guard ? "true" : "false"));\n')
                self.fd.write('        return guard;\n')
                self.fd.write('    }\n\n')

            if tr.action != '':
                self.generate_method_comment('Do the action when transitioning from state ' + origin + '\n    //! to state ' + destination + '.')
                self.fd.write('    void onTransitioning' + self.state_name(origin) + '_' + self.state_name(destination) + '()\n')
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
                self.fd.write('    void onEnteringState' + self.state_name(state.name) + '()\n')
                self.fd.write('    {\n')
                self.fd.write('        LOGD("[ENTERING STATE ' + state.name + ']\\n");\n')
                self.fd.write('        ' + state.entering)
                if state.entering[-2] != '}':
                    self.fd.write(';\n')
                self.fd.write('    }\n\n')

            if state.leaving != '':
                self.generate_method_comment('Do the action when leaving the state ' + state.name + '.')
                self.fd.write('    void onLeavingState' + self.state_name(state.name) + '()\n')
                self.fd.write('    {\n')
                self.fd.write('        LOGD("[LEAVING STATE ' + state.name + ']\\n");\n')
                self.fd.write('        ' + state.leaving + ';\n')
                self.fd.write('    }\n\n')

            if state.event.name != '':
                self.generate_method_comment('Do the action on event XXX ' + state.name + '.')
                self.fd.write('    void onEventState' + self.state_name(state.name) + '()\n')
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
    ### Generate code with its comment inside a #ifdef #endif
    ###########################################################################
    def generate_custom_macro(self, comment, code):
        self.fd.write(comment)
        self.fd.write('\n#if defined(CUSTOMIZE_STATE_MACHINE') # self.class_name.upper()
        self.fd.write(')\n')
        self.fd.write(code)
        self.fd.write('\n')
        self.fd.write('#endif\n')

    ###########################################################################
    ### Code generator: generate the header file which hold helper macros.
    ###########################################################################
    def generate_macros(self, cxxfile):
        filename = self.class_name + 'Macros.hpp'
        path = os.path.join(os.path.dirname(cxxfile), filename)
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
        self.fd.write('#  define CUSTOM_' + name + '_PREPARE_UNIT_TEST\n\n')
        self.fd.write('#  define CUSTOM_' + name + '_INIT_UNIT_TEST_VARIABLES\n\n')
        self.fd.write('#endif // ' + guard_name + '\n')
        self.fd.close()

    ###########################################################################
    ### Generate the header for the unit test file
    ###########################################################################
    def generate_unit_tests_header(self):
        self.fd.write('#include "' + self.class_name + '.hpp"\n')
        self.fd.write('#include <iostream>\n')
        self.fd.write('#include <cassert>\n')
        self.fd.write('#include <cstring>\n\n')

    ###########################################################################
    ### Generate the macro for the unit test file
    ###########################################################################
    def generate_unit_tests_macro(self):
        self.generate_custom_macro('    // Add here initial variables', '    CUSTOM_' + self.class_name.upper() + '_INIT_UNIT_TEST_VARIABLES')
        self.fd.write('\n')

    ###########################################################################
    ### Generate checks on initial state
    ###########################################################################
    def generate_unit_tests_check_initial_state(self):
        self.fd.write('    std::cout << "===========================================" << std::endl;\n')
        self.fd.write('    std::cout << "Check current state" << std::endl;\n')
        self.fd.write('    std::cout << "===========================================" << std::endl;\n')
        self.fd.write('    ' + self.class_name + ' ' + 'fsm;\n')
        # Initial state may have several transitions
        neighbors = list(self.graph.neighbors(self.initial_state))
        self.fd.write('    assert(fsm.state() == ' + self.enum_name + '::')
        l = [ self.state_name(e) for e in self.graph.neighbors(self.initial_state)]
        self.fd.write(('\n          || fsm.state() == ' + self.enum_name + '::').join(l))
        self.fd.write(');\n')

        self.fd.write('    assert(strcmp(fsm.c_str(), "' + neighbors[0] + '") == 0')
        for n in neighbors[1:]:
            self.fd.write('\n          || strcmp(fsm.c_str(), "' + n + '") == 0')
        self.fd.write(');\n')
        self.fd.write('    LOGD("Test: ok\\n");\n\n')

    ###########################################################################
    ### Generate checks on all cycles
    ###########################################################################
    def generate_unit_tests_check_cycles(self):
        cycles = self.graph_cycles()
        for cycle in cycles:
            self.fd.write('    std::cout << "===========================================" << std::endl;\n')
            self.fd.write('    std::cout << "Check cycle: [*]')
            for c in cycle:
                self.fd.write(' ' + c)
            self.fd.write('" << std::endl;\n')
            self.fd.write('    std::cout << "===========================================" << std::endl;\n')
            self.fd.write('    fsm.reset();')
            guard = self.graph[self.initial_state][cycle[0]]['data'].guard
            if guard != '':
                self.fd.write(' // If ' + guard)
            self.fd.write('\n')
            for i in range(len(cycle) - 1):
                event = self.graph[cycle[i]][cycle[i+1]]['data'].event
                if event.name != '':
                    guard = self.graph[cycle[i]][cycle[i+1]]['data'].guard
                    self.fd.write('    fsm.' + event.caller() + ';')
                    if guard != '':
                        self.fd.write(' // If ' + guard)
                    self.fd.write('\n')
                if (i == len(cycle) - 2):
                    if self.graph[cycle[i+1]][cycle[1]]['data'].event.name == '':
                        self.fd.write('    #warning "Malformed state machine: unreachable destination state"\n\n')
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

    ###########################################################################
    ### Generate checks on pathes to all sinks
    ###########################################################################
    def generate_unit_tests_pathes_to_sinks(self):
        pathes = self.graph_all_paths_to_sinks()
        for path in pathes:
            self.fd.write('    std::cout << "===========================================" << std::endl;\n')
            self.fd.write('    std::cout << "Check path:')
            for c in path:
                self.fd.write(' ' + c)
            self.fd.write('" << std::endl;\n')
            self.fd.write('    std::cout << "===========================================" << std::endl;\n')
            self.fd.write('    fsm.reset();')
            guard = self.graph[path[0]][path[1]]['data'].guard
            if guard != '':
                self.fd.write(' // If ' + guard)
            self.fd.write('\n')
            for i in range(len(path) - 1):
                event = self.graph[path[i]][path[i+1]]['data'].event
                if event.name != '':
                    guard = self.graph[path[i]][path[i+1]]['data'].guard
                    self.fd.write('    fsm.' + event.caller() + ';')
                    if guard != '':
                        self.fd.write(' // If ' + guard)
                    self.fd.write('\n')
                if (i == len(path) - 2):
                    self.fd.write('    std::cout << "Current state: " << fsm.c_str() << std::endl;\n')
                    self.fd.write('    assert(fsm.state() == ' + self.enum_name + '::' + path[i+1] + ');\n')
                    self.fd.write('    assert(strcmp(fsm.c_str(), "' + path[i+1] + '") == 0);\n')
                    self.fd.write('    LOGD("Assertions: ok\\n");\n\n')
                elif self.graph[path[i+1]][path[i+2]]['data'].event.name != '':
                    self.fd.write('    std::cout << "Current state: " << fsm.c_str() << std::endl;\n')
                    self.fd.write('    assert(fsm.state() == ' + self.enum_name + '::' + path[i+1] + ');\n')
                    self.fd.write('    assert(strcmp(fsm.c_str(), "' + path[i+1] + '") == 0);\n')
                    self.fd.write('    LOGD("Assertions: ok\\n");\n\n')

    ###########################################################################
    ### Generate the main function doing unit tests
    ###########################################################################
    def generate_unit_tests_main_function(self, filename):
        self.generate_custom_macro('// Add here code to prepare unit tests', 'CUSTOM_' + self.class_name.upper() + '_PREPARE_UNIT_TEST')
        self.fd.write('\n')
        self.generate_function_comment('Compile with one of the following line:\n' +
                                       '//! g++ --std=c++14 -Wall -Wextra -Wshadow -DFSM_DEBUG -DCUSTOMIZE_STATE_MACHINE ' + os.path.basename(filename))
        self.fd.write('int main()\n')
        self.fd.write('{\n')

        self.generate_unit_tests_macro()
        self.generate_unit_tests_check_initial_state()
        self.generate_unit_tests_check_cycles()
        self.generate_unit_tests_pathes_to_sinks()

        self.fd.write('    std::cout << "Unit test done with success" << std::endl;\n\n')
        self.fd.write('    return EXIT_SUCCESS;\n')
        self.fd.write('}\n\n')

    ###########################################################################
    ### Code generator: Add an example of how using this state machine. It
    ### gets all cycles in the graph and try them. This example can be used as
    ### partial unit test. Not all cases can be generated since I dunno how to
    ### parse guards to generate range of inputs.
    ### FIXME Manage guard logic to know where to pass in edges.
    ### FIXME Cycles does not make all test case possible
    ###########################################################################
    def generate_unit_tests(self, cxxfile):
        filename = self.class_name + 'Tests.cpp'
        self.fd = open(os.path.join(os.path.dirname(cxxfile), filename), 'w')
        self.generate_unit_tests_header()
        self.generate_unit_tests_main_function(filename)
        self.fd.close()

    ###########################################################################
    ### Code generator: generate the code of the state machine
    ###########################################################################
    def generate_state_machine(self, cxxfile):
        hpp = self.is_hpp_file(cxxfile)
        self.fd = open(cxxfile, 'w')
        self.generate_header(hpp)
        self.generate_state_enums()
        self.generate_stringify_function()
        self.generate_state_machine_class()
        self.generate_footer(hpp)
        self.fd.close()

    ###########################################################################
    ### Code generator: entry point generating C++ files: state machine, tests,
    ### macros ...
    ###########################################################################
    def generate_code(self, cxxfile):
        self.generate_state_machine(cxxfile)
        self.generate_unit_tests(cxxfile)
        self.generate_macros(cxxfile)

    ###########################################################################
    ### Manage transitions without events: we name them internal event and the
    ### transition to the next state is made. Since we cannot offer a public
    ### method 'no event' to make react the state machine we place the transition
    ### inside the source state as 'on entry' action. We also suppose that
    ### the state machine is well formed: meaning no several internal events are
    ### allowed (non determinist switch condition).
    ###########################################################################
    def manage_noevents(self):
        # Make unique the list of states that does not have event on their
        # output edges
        states = []
        for s in list(self.graph.nodes()):
            for d in list(self.graph.neighbors(s)):
                tr = self.graph[s][d]['data']
                if tr.event.name == '':
                    states.append(s)

        states = list(set(states))

        # Generate the internal transition in the entry action of the source state
        code = ''
        for state in states:
            count = 0 # count number of ways
            code = '\n        LOGD("[STATE ' + state +  '] Internal transition\\n");\n'
            for dest in list(self.graph.neighbors(state)):
                tr = self.graph[state][dest]['data']
                s = self.state_name(state)
                d = self.state_name(dest)
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
                elif tr.event.name == '':
                    # Several destination states possible: not determinist !
                    # We keep generating and add a C++ compilation warning.
                    if count == 1:
                        code += '\n#warning "Badly formed state machine: missing guard here"\n'
                        code += '        /* MISSING GUARD HERE */ {\n'
                    else:
                        code += '        {\n'
                    code += '            static StateMachine<' + self.class_name + ', ' + self.enum_name + '>::Transition tr =\n'
                    code += '            {\n'
                    code += '                .destination = ' + self.enum_name + '::' + d + ',\n'
                    if tr.action != '':
                        code += '                .action = &' + self.class_name + '::onTransitioning' + s + '_' + d + ',\n'
                    code += '            };\n'
                    code += '            transition(&tr);\n'
                    code += '            return ;\n'
                    code += '        }\n'
                else:
                    code += '\n#warning "Undeterminist State machine detected switching to state ' + d + '"\n'
                count += 1
            self.graph.nodes[state]['data'].entering += code

    ###########################################################################
    ### The state machine shall have an initial state.
    ###########################################################################
    def verify_initial_state(self):
        if self.initial_state == '':
            self.parse_error('Missing initial state')

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
    ### Verify for each state if transitions are dereminist.
    ### Case 1: each state having more than 1 transition in where one transition
    ###         does not have event and guard.
    ### Case 2: several transitions and guards does not check all cases (for
    ###         example the Richman case with init quarters < 0.
    ###########################################################################
    def verify_transitions(self):
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
        # Case 2: TODO

    ###########################################################################
    ### Entry point to check if the state machine is well formed (determinist).
    ### Do not exit the program or throw exception, just display warning on the
    ### console.
    ### TODO for each node: are transitions to output neighbors mutually exclusive ?
    ### TODO Are all states reachable ?
    ### TODO how to parse guards to do formal prooves ? Can formal proove be
    ### used in a networkx graph ?
    ###########################################################################
    def is_state_machine_determinist(self):
        self.verify_initial_state()
        self.verify_number_of_events()
        self.verify_transitions()
        pass

    ###########################################################################
    ### Entry point of graph reorganization.
    ### When parsing PlantUML we also create on the fly the graph structure but
    ### some reorganization on the graph may be needed after the parsing step.
    ### TBD: we can 'optimize' by suppressing nodes that do not have events but
    ### we prefer not modifying the graph that the user made in PlantUML. We
    ### add instead warnings to prevent him.
    ###########################################################################
    def finalize_machine(self):
        self.is_state_machine_determinist()
        self.manage_noevents()

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

        if self.tokens[1][-1] == '>':
            # Analyse the following plantUML code: "origin state -> destination state ..."
            tr.origin, tr.destination = self.tokens[0].upper(), self.tokens[2].upper()
        else:
            # Analyse the following plantUML code: "destination state <- origin state ..."
            tr.origin, tr.destination = self.tokens[2].upper(), self.tokens[0].upper()

        # Add nodes first to be sure to access them later
        self.add_state(tr.origin)
        self.add_state(tr.destination)

        # Initial/final states
        if tr.origin == '[*]':
            self.initial_state = '[*]'
        elif tr.destination == '[*]':
            self.final_state = '*'

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
                tr.action = ' '.join(self.tokens[i+1:])

            # Distinguish a transition cycling to its own state from the "on event" on the state
            if as_state and (tr.origin == tr.destination):
                if tr.action == '':
                    tr.action = '// Dummy action'
                self.graph.nodes[tr.origin]['data'].event.name = tr.action
                tr.action = ''

        # Store parsed information as edge of the graph
        self.add_transition(tr)

    ###########################################################################
    ### Parse the following plantUML code and store information of the analyse:
    ###    State : Entry / action
    ###    State : Exit / action
    ###    State : On event [ guard ] / action
    ###    State : Do / activity
    ### We also offering some unofficial alternative name:
    ###    State : Entering / action
    ###    State : Leaving / action
    ###    State : Event event [ guard ] / action
    ###    State : Comment / C++ comment
    ###########################################################################
    def parse_state(self):
        what = self.tokens[2].lower()
        name = self.tokens[0].upper()

        # Manage a pathological case:
        self.assert_valid_C_name(name)

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
        elif what in ['on', 'event']:
            self.tokens = [ name, '->', name, ':' ] + self.tokens[3:]
            self.parse_transition(True)
            return
        elif what == 'do':
            self.parse_error('do / activity not yet implemented')
        else:
            self.parse_error('Bad syntax describing a state. Unkown token "' + what + '"')

    ###########################################################################
    ### Read a single line, tokenize its symbols and store them in a list.
    ###########################################################################
    def parse_line(self):
        self.nb_tokens = 0
        # Iterate for each empty line
        while self.nb_tokens == 0:
            self.lines += 1
            line = self.fd.readline()
            if not line:
                return False
            # Replace substring to be sure to parse correctly (ugly hack)
            line = line.replace(':', ' : ')
            line = line.replace('/', ' / ')
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
            #print('\n=========\nparse_line: ' + line[:-1])
            #for t in self.tokens:
            #    print('token: "' + t + '"')
        return True

    ###########################################################################
    ### Parse plantUML file parser and create a graph structure.
    ###########################################################################
    def parse_plantuml_file(self, umlfile, cpp_or_hpp, classname):
        self.reset()
        self.fd = open(umlfile, 'r')
        self.name = Path(umlfile).stem
        self.class_name = self.name + classname
        self.enum_name = self.class_name + 'States'

        # PlantUML file shall start by '@startuml'
        if (not self.parse_line()) or (self.tokens[0] != '@startuml'):
           self.parse_error('Bad plantuml file: did not find @startuml')

        # Since PlantUML instruction by line read a line one by one
        while self.parse_line():
            if (self.nb_tokens >= 3) and (self.tokens[1] in ['->', '-->', '<-', '<--']):
                self.parse_transition()
            elif (self.nb_tokens >= 4) and (self.tokens[1] == ':'):
                self.parse_state()
            elif self.tokens[0] == '@enduml':
                break
            elif self.tokens[0] in ['hide', 'scale', 'skin']:
                continue
            else:
                self.parse_error('Bad line')

        self.fd.close()

    ###########################################################################
    ### Entry point for translating a plantUML file into a C++ source file.
    ### umlfile: path to the plantuml file.
    ### cpp_or_hpp: generated a C++ source file ('cpp') or a C++ header file ('hpp').
    ### classname: postfixe name for the state machine name.
    ###########################################################################
    def translate(self, umlfile, cpp_or_hpp, classname):
        if not os.path.isfile(umlfile):
            print('File path {} does not exist. Exiting...'.format(umlfile))
            sys.exit(-1)

        self.parse_plantuml_file(umlfile, cpp_or_hpp, classname)
        self.finalize_machine()
        self.generate_code(self.class_name + '.' + cpp_or_hpp)

###############################################################################
### Display command line usage
###############################################################################
def usage():
    print('Command line: ' + sys.argv[0] + ' <plantuml file> cpp|hpp [state machine name]')
    print('Where:')
    print('   <plantuml file>: the path of a plantuml statechart')
    print('   "cpp" or "hpp": to choose between generating a C++ source file or a C++ header file')
    print('   [state machine name]: is an optional name to postfix the name of the state machine class')
    print('Example:')
    print('   sys.argv[1] foo.plantuml cpp Bar')
    print('Will create a FooBar.cpp file with a state machine name FooBar')
    sys.exit(-1)

###############################################################################
### Entry point.
### argv[1] Mandatory: path of the state machine in plantUML format.
### argv[2] Mandatory: path of the C++ file to create.
### argv[3] Optional: Postfix name for the state machine class.
###############################################################################
def main():
    argc = len(sys.argv)
    if argc < 3:
        usage()
    if sys.argv[2] not in ['cpp', 'hpp']:
        print('Invalid ' + sys.argv[2] + '. Please set instead "cpp" (for generating a C++ source file) or "hpp" (for generating a C++ header file)')
        usage()

    p = Parser()
    p.translate(sys.argv[1], sys.argv[2], '' if argc == 3 else sys.argv[3])

if __name__ == '__main__':
    main()
