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
from lark import Lark, Transformer

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
        # state : do / activity
        self.activity = ''

    def __str__(self):
        return self.name + ': ' + self.entering + ' / ' + self.leaving

###############################################################################
### Add some extra C++ code in the generated code.
###############################################################################
class ExtraCode(object):

    ###########################################################################
    ### Default dummy constructor.
    ###########################################################################
    def __init__(self):
        # Add code on the footer of the code before the class definition.
        self.header = ''
        # Add code on the footer of the code after the class definition.
        self.footer = ''
        # Add argument to constructor
        self.argvs = ''
        # Add code for the class constructor, reset.
        self.init = ''
        # Add member functions and member variables in the class.
        self.functions = ''
        # Prepare the code for unit tests
        self.unit_tests = ''

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
        # Context-free language parser
        self.parser = None
        # Abstract Syntax Tree
        self.ast = None
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
        # List Cache the current line to display in error messages.
        self.lines = 0
        # Dictionnary of "event => (source, destination) states" needed to
        # compute tables of state transitions for each events.
        self.lookup_events = defaultdict(list)
        # Store all parsed information from plantUML file as a graph.
        # FIXME shall be nx.MultiDiGraph() since we cannot create several events
        # leaving and entering to the same state or two events from a source
        # state going to the same destination state.
        self.graph = nx.DiGraph()
        # Initial / final states
        self.initial_state = ''
        self.final_state = ''
        # Extra C++ code
        self.extra_code = ExtraCode()
        # Generate C++ warnings when missformed state machine is detected
        self.warnings = ''

    ###########################################################################
    ### Reset states.
    ### Note: self.parser is not reloaded since useless.
    ###########################################################################
    def reset(self):
        self.tokens = []
        self.ast = None
        self.line = ''
        self.lines = 0
        self.lookup_events = defaultdict(list)
        self.graph = nx.DiGraph() # TODO nx.MultiDiGraph()
        self.initial_state = ''
        self.final_state = ''
        self.extra_code = ExtraCode()
        self.warnings = ''

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
        self.warnings += msg
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
    def generate_line_separator(self, spaces, s, count, c):
        self.fd.write(s * spaces)
        self.fd.write('//')
        self.fd.write(c * count)
        self.fd.write('\n')

    ###########################################################################
    ### Code generator: add a function  or methodcomment.
    ###########################################################################
    def generate_comment(self, spaces, s, comment, c):
        final_comment = ('//! \\brief')
        if comment != '':
            final_comment += ' '
            final_comment += comment

        longest_list = max(len(elem) for elem in final_comment.split('\n'))
        N = max(longest_list, 80) - len(s) * spaces
        self.generate_line_separator(spaces, s, N, c)
        self.fd.write(s * spaces)
        self.fd.write(final_comment)
        self.fd.write('\n')
        self.generate_line_separator(spaces, s, N, c)

    ###########################################################################
    ### Code generator: add a dummy function comment.
    ###########################################################################
    def generate_function_comment(self, comment):
        self.generate_comment(0, ' ', comment, '*')

    ###########################################################################
    ### Code generator: add a dummy method comment.
    ###########################################################################
    def generate_method_comment(self, comment):
        self.generate_comment(4, ' ', comment, '-')

    ###########################################################################
    ### Identation.
    ###########################################################################
    def indent(self, count):
        self.fd.write(' ' * 4 * count)

    ###########################################################################
    ### You can add here your copyright, license ...
    ###########################################################################
    def generate_common_header(self):
        self.fd.write('// This file as been generated the ')
        self.fd.write(date.today().strftime("%B %d, %Y\n"))
        self.fd.write('// This code generation is still experimental. Some border cases may not be correctly managed!\n\n')

    ###########################################################################
    ### Code generator: add the header file.
    ### TODO include or insert custom header like done with flex/bison
    ###########################################################################
    def generate_header(self, hpp):
        self.generate_common_header()
        if hpp:
            self.fd.write('#ifndef ' + self.class_name.upper() + '_HPP\n')
            self.fd.write('#  define ' + self.class_name.upper() + '_HPP\n\n')
            self.fd.write('#  include "StateMachine.hpp"\n')
        else:
            self.fd.write('#include "StateMachine.hpp"\n')
        self.fd.write(self.extra_code.header)
        if self.extra_code.header != '':
            self.fd.write('\n')

    ###########################################################################
    ### Code generator: add the footer file.
    ### TODO include or insert custom footer like done with flex/bison
    ###########################################################################
    def generate_footer(self, hpp):
        if self.warnings != '':
            self.fd.write('#warning "' + self.warnings + '"\n\n')
        self.fd.write(self.extra_code.footer)
        if hpp:
            self.fd.write('#endif // ' + self.class_name.upper() + '_HPP')

    ###########################################################################
    ### Code generator: add the enum of the states of the state machine.
    ###########################################################################
    def generate_state_enums(self):
        self.generate_function_comment('States of the state machine.')
        self.fd.write('enum ' + self.enum_name + '\n{\n')
        self.indent(1), self.fd.write('// Client states:\n')
        for state in list(self.graph.nodes):
            self.indent(1), self.fd.write(self.state_name(state) + ',')
            comment = self.graph.nodes[state]['data'].comment
            if comment != '':
                self.fd.write(' //!< ' + comment)
            self.fd.write('\n')
        self.indent(1), self.fd.write('// Mandatory internal states:\n')
        self.indent(1), self.fd.write('IGNORING_EVENT, CANNOT_HAPPEN, MAX_STATES\n')
        self.fd.write('};\n\n')

    ###########################################################################
    ### Code generator: add the function that stringify states.
    ###########################################################################
    def generate_stringify_function(self):
        self.generate_function_comment('Convert enum states to human readable string.')
        self.fd.write('static inline const char* stringify(' + self.enum_name + ' const state)\n{\n')
        self.indent(1), self.fd.write('static const char* s_states[] =\n')
        self.indent(1), self.fd.write('{\n')
        for state in list(self.graph.nodes):
            self.indent(2), self.fd.write('[' + self.enum_name + '::' + self.state_name(state) + '] = "' + state + '",\n')
        self.indent(1), self.fd.write('};\n\n')
        self.indent(1), self.fd.write('return s_states[state];\n};\n\n')

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
        self.indent(3)
        self.fd.write('.' + what +' = &' + self.class_name + '::' + dict[what] + self.state_name(state) + ',\n')

    ###########################################################################
    ### Code generator: add the state machine constructor method.
    ###########################################################################
    def generate_table_states(self, states):
        empty = True
        for state in states:
            if 'data' not in self.graph.nodes[state]:
                continue

            s = self.graph.nodes[state]['data']
            if (s.entering == '') and (s.leaving == ''):
                continue

            self.indent(2), self.fd.write('m_states[' + self.enum_name + '::' + self.state_name(s.name) + '] =\n')
            self.indent(2), self.fd.write('{\n')
            if s.entering != '':
                self.generate_pointer_function('entering', s.name)
            if s.leaving != '':
                self.generate_pointer_function('leaving', s.name)
            if s.activity != '':
                self.generate_pointer_function('activity', s.name)
            self.indent(2), self.fd.write('};\n')
            empty = False
        if empty:
            self.indent(2), self.fd.write('// Note: no table of states created since no state will do actions!\n')

    ###########################################################################
    ### Code generator: add the state machine constructor method.
    ###########################################################################
    def generate_constructor(self):
        states = list(self.graph.nodes)
        self.generate_method_comment('Default constructor. Start from initial state and call it actions.')
        self.indent(1), self.fd.write(self.class_name + '(' + self.extra_code.argvs + ')\n')
        self.indent(2), self.fd.write(': StateMachine(' + self.enum_name + '::' + self.state_name(self.initial_state) + ')\n')
        self.indent(1), self.fd.write('{\n')
        self.generate_table_states(states)
        self.fd.write(self.extra_code.init)
        self.indent(2), self.fd.write('onEnteringState' + self.state_name(self.initial_state) + '();\n')
        self.indent(1), self.fd.write('}\n\n')

    ###########################################################################
    ### Code generator: add the state machine reset method.
    ###########################################################################
    def generate_reset(self):
        self.generate_method_comment('Reset the state machine.')
        self.indent(1), self.fd.write('void start()\n')
        self.indent(1), self.fd.write('{\n')
        self.indent(2), self.fd.write('StateMachine::start();\n')
        self.fd.write(self.extra_code.init)
        self.indent(2), self.fd.write('onEnteringState' + self.state_name(self.initial_state) + '();\n')
        self.indent(1), self.fd.write('}\n\n')

    ###########################################################################
    ### Code generator: add all methods associated with external events.
    ###########################################################################
    def generate_external_events(self):
        for event, arcs in self.lookup_events.items():
            if event.name == '':
                continue

            self.generate_method_comment('External event.')
            self.indent(1), self.fd.write(event.header() + '\n')
            self.indent(1), self.fd.write('{\n')
            self.indent(2), self.fd.write('LOGD("[EVENT %s]\\n", __func__);\n\n')
            self.indent(2), self.fd.write('static Transitions s_transitions =\n')
            self.indent(2), self.fd.write('{\n')
            for origin, destination in arcs:
                tr = self.graph[origin][destination]['data']
                self.indent(3), self.fd.write('{\n')
                self.indent(3), self.fd.write(self.enum_name + '::' + self.state_name(origin) + ',\n')
                self.indent(3), self.fd.write('{\n')
                self.indent(5), self.fd.write(self.enum_name + '::' + self.state_name(destination) + ',\n')
                if tr.guard != '':
                    self.indent(5), self.fd.write('&' + self.class_name + '::onGuardingTransition')
                    self.fd.write(self.state_name(origin) + '_' + self.state_name(destination) + ',\n')
                else:
                    self.indent(5), self.fd.write('nullptr,\n')
                if tr.action != '':
                    self.indent(5), self.fd.write('&' + self.class_name + '::onTransitioning')
                    self.fd.write(self.state_name(origin) + '_' + self.state_name(destination) + ',\n')
                else:
                    self.indent(5), self.fd.write('nullptr,\n')
                self.indent(4), self.fd.write('},\n')
                self.indent(3), self.fd.write('},\n')
            self.indent(2), self.fd.write('};\n\n')
            self.indent(2), self.fd.write('transition(s_transitions);\n')
            self.indent(1), self.fd.write('}\n\n')

    ###########################################################################
    ### Code generator: Transitions reactions.
    ###########################################################################
    def generate_states_transitions_reactions(self):
        transitions = list(self.graph.edges)
        for origin, destination in transitions:
            tr = self.graph[origin][destination]['data']
            if tr.guard != '':
                self.generate_method_comment('Guard the transition from state ' + origin  + ' to state ' + destination + '.')
                self.indent(1), self.fd.write('MOCKABLE bool onGuardingTransition' + self.state_name(origin) + '_' + self.state_name(destination) + '()\n')
                self.indent(1), self.fd.write('{\n')
                self.indent(2), self.fd.write('const bool guard = (' + tr.guard + ');\n')
                self.indent(2), self.fd.write('LOGD("[GUARD ' + origin + ' --> ' + destination + ': ' + tr.guard + '] result: %s\\n",\n')
                self.indent(3), self.fd.write('(guard ? "true" : "false"));\n')
                self.indent(2), self.fd.write('return guard;\n')
                self.indent(1), self.fd.write('}\n\n')

            if tr.action != '':
                self.generate_method_comment('Do the action when transitioning from state ' + origin + ' to state ' + destination + '.')
                self.indent(1), self.fd.write('MOCKABLE void onTransitioning' + self.state_name(origin) + '_' + self.state_name(destination) + '()\n')
                self.indent(1), self.fd.write('{\n')
                self.indent(2), self.fd.write('LOGD("[TRANSITION ' + origin + ' --> ' + destination + ': ' + tr.action + ']\\n");\n')
                self.indent(2), self.fd.write(tr.action + ';\n')
                self.indent(1), self.fd.write('}\n\n')

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
                self.indent(1), self.fd.write('MOCKABLE void onEnteringState' + self.state_name(state.name) + '()\n')
                self.indent(1), self.fd.write('{\n')
                self.indent(2), self.fd.write('LOGD("[ENTERING STATE ' + state.name + ']\\n");\n')
                self.fd.write(state.entering)
                self.indent(1), self.fd.write('}\n\n')

            if state.leaving != '':
                self.generate_method_comment('Do the action when leaving the state ' + state.name + '.')
                self.indent(1), self.fd.write('MOCKABLE void onLeavingState' + self.state_name(state.name) + '()\n')
                self.indent(1), self.fd.write('{\n')
                self.indent(2), self.fd.write('LOGD("[LEAVING STATE ' + state.name + ']\\n");\n')
                self.fd.write(state.leaving)
                self.indent(1), self.fd.write('}\n\n')

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
        self.fd.write(self.extra_code.functions)
        self.fd.write('};\n\n')

    ###########################################################################
    ### Generate the header for the unit test file
    ###########################################################################
    def generate_unit_tests_header(self):
        self.generate_common_header()
        self.fd.write('#define MOCKABLE virtual\n')
        self.fd.write('#include "' + self.class_name + '.hpp"\n')
        self.fd.write('#include <gmock/gmock.h>\n')
        self.fd.write('#include <gtest/gtest.h>\n')
        self.fd.write('#include <cstring>\n\n')
        self.fd.write(self.extra_code.unit_tests)
        if self.extra_code.unit_tests != '':
            self.fd.write('\n')

    ###########################################################################
    ### Generate the mocked class
    ###########################################################################
    def generate_unit_tests_mocked_class(self):
        self.generate_function_comment('Mocked state machine')
        self.fd.write('class Mock' + self.class_name + ' : public ' + self.class_name)
        self.fd.write('\n{\npublic:\n')
        transitions = list(self.graph.edges)
        for origin, destination in transitions:
            tr = self.graph[origin][destination]['data']
            if tr.guard != '':
                self.fd.write('    MOCK_METHOD(bool, onGuardingTransition' + self.state_name(origin) + '_' + self.state_name(destination) + ', (), (override));\n')
        #for s in self.states:
        #    if s.entering != '':
        #        self.fd.write('    MOCK_METHOD(void, ' + s.entering + ', (), (override));\n')
        #    if s.leaving != '':
        #        self.fd.write('    MOCK_METHOD(void, ' + s.leaving + ', (), (override));\n')
        self.fd.write('};\n\n')

    ###########################################################################
    ### Generate the footer for the unit test file
    ###########################################################################
    def generate_unit_tests_footer(self):
        pass

    ###########################################################################
    ### Generate checks on initial state.
    ### Initial state may have several transitions.
    ###########################################################################
    def generate_unit_tests_assertions_initial_state(self):
        # List of possible state enums
        neighbors = list(self.graph.neighbors(self.initial_state))
        self.fd.write('    ASSERT_TRUE(fsm.state() == ' + self.enum_name + '::')
        l = [ self.state_name(e) for e in self.graph.neighbors(self.initial_state)]
        self.fd.write(('\n          || fsm.state() == ' + self.enum_name + '::').join(l))
        self.fd.write(');\n')
        # List of possible state strings
        self.indent(1), self.fd.write('ASSERT_TRUE(strcmp(fsm.c_str(), "' + neighbors[0] + '") == 0')
        for n in neighbors[1:]:
            self.fd.write('\n          || strcmp(fsm.c_str(), "' + n + '") == 0')
        self.fd.write(');\n')

    ###########################################################################
    ### Generate checks on initial state
    ###########################################################################
    def generate_unit_tests_check_initial_state(self):
        self.generate_line_separator(0, ' ', 80, '-')
        self.fd.write('TEST(' + self.class_name + 'Tests, TestInitialSate)\n{\n')
        self.indent(1), self.fd.write('LOGD("===============================================\\n");\n')
        self.indent(1), self.fd.write('LOGD("Check initial state after constructor or reset.\\n");\n')
        self.indent(1), self.fd.write('LOGD("===============================================\\n");\n')
        self.indent(1), self.fd.write(self.class_name + ' ' + 'fsm; // Not mocked !\n')
        self.indent(1), self.fd.write('fsm.start();\n')
        self.generate_unit_tests_assertions_initial_state()
        self.fd.write('}\n\n')

    ###########################################################################
    ### Generate checks on all cycles
    ###########################################################################
    def generate_unit_tests_check_cycles(self):
        count = 0
        cycles = self.graph_cycles()
        for cycle in cycles:
            self.generate_line_separator(0, ' ', 80, '-')
            self.fd.write('TEST(' + self.class_name + 'Tests, TestCycle' + str(count) + ')\n{\n')
            count += 1
            # Print the cycle
            self.indent(1), self.fd.write('LOGD("===========================================\\n");\n')
            self.indent(1), self.fd.write('LOGD("Check cycle: [*]')
            for c in cycle:
                self.fd.write(' ' + c)
            self.fd.write('\\n");\n')
            self.indent(1), self.fd.write('LOGD("===========================================\\n");\n')

            # Reset the state machine and print the guard supposed to reach this state
            self.indent(1), self.fd.write('Mock' + self.class_name + ' ' + 'fsm;\n')
            self.indent(1), self.fd.write('fsm.start();')
            guard = self.graph[self.initial_state][cycle[0]]['data'].guard
            if guard != '':
                self.fd.write(' // If ' + guard)
            self.fd.write('\n\n')

            # Iterate on all nodes of the cycle
            for i in range(len(cycle) - 1):
                # External event not leaving the current state
                if self.graph.has_edge(cycle[i], cycle[i]) and (cycle[i] != cycle[i+1]):
                    tr = self.graph[cycle[i]][cycle[i]]['data']
                    if tr.event.name != '':
                        self.indent(1), self.fd.write('LOGD("// Event ' + tr.event.name + ' [' + tr.guard + ']: ' + cycle[i] + ' <--> ' + cycle[i] + '\\n");\n')
                        self.indent(1), self.fd.write('fsm.' + tr.event.caller() + ';')
                        if tr.guard != '':
                            self.fd.write(' // If ' + tr.guard)
                        self.fd.write('\n')
                        self.indent(1), self.fd.write('LOGD("Current state: %s\\n", fsm.c_str());\n')
                        self.indent(1), self.fd.write('ASSERT_EQ(fsm.state(), ' + self.enum_name + '::' + self.state_name(cycle[i]) + ');\n')
                        self.indent(1), self.fd.write('ASSERT_STREQ(fsm.c_str(), "' + cycle[i] + '");\n')

                # External event: print the name of the event + its guard
                tr = self.graph[cycle[i]][cycle[i+1]]['data']
                if tr.event.name != '':
                    self.indent(1)
                    self.fd.write('LOGD("// Event ' + tr.event.name + ' [' + tr.guard + ']: ' + cycle[i] + ' ==> ' + cycle[i + 1] + '\\n");\n')
                    self.indent(1), self.fd.write('fsm.' + tr.event.caller() + ';')
                    if tr.guard != '':
                        self.fd.write(' // If ' + tr.guard)
                    self.fd.write('\n')

                if (i == len(cycle) - 2):
                    # Cycle of non external evants => malformed state machine
                    # I think this case is not good
                    if self.graph[cycle[i+1]][cycle[1]]['data'].event.name == '':
                        self.indent(1), self.fd.write('#warning "Malformed state machine: unreachable destination state"\n\n')
                    else:
                        # No explicit event => direct internal transition to the state if an explicit event can occures.
                        self.indent(1), self.fd.write('LOGD("Current state: %s\\n", fsm.c_str());\n')
                        self.indent(1), self.fd.write('ASSERT_EQ(fsm.state(), ' + self.enum_name + '::' + self.state_name(cycle[i+1]) + ');\n')
                        self.indent(1), self.fd.write('ASSERT_STREQ(fsm.c_str(), "' + cycle[i+1] + '");\n')

                # No explicit event => direct internal transition to the state if an explicit event can occures.
                # Else skip test for the destination state since we cannot test its internal state
                elif self.graph[cycle[i+1]][cycle[i+2]]['data'].event.name != '':
                    self.indent(1), self.fd.write('LOGD("Current state: %s\\n", fsm.c_str());\n')
                    self.indent(1), self.fd.write('ASSERT_EQ(fsm.state(), ' + self.enum_name + '::' + self.state_name(cycle[i+1]) + ');\n')
                    self.indent(1), self.fd.write('ASSERT_STREQ(fsm.c_str(), "' + cycle[i+1] + '");\n')
            self.fd.write('}\n\n')

    ###########################################################################
    ### Generate checks on pathes to all sinks
    ###########################################################################
    def generate_unit_tests_pathes_to_sinks(self):
        count = 0
        pathes = self.graph_all_paths_to_sinks()
        for path in pathes:
            self.generate_line_separator(0, ' ', 80, '-')
            self.fd.write('TEST(' + self.class_name + 'Tests, TestPath' + str(count) + ')\n{\n')
            count += 1
            # Print the path
            self.indent(1), self.fd.write('LOGD("===========================================\\n");\n')
            self.indent(1), self.fd.write('LOGD("Check path:')
            for c in path:
                self.fd.write(' ' + c)
            self.fd.write('\\n");\n')
            self.indent(1), self.fd.write('LOGD("===========================================\\n");\n')

            # Reset the state machine and print the guard supposed to reach this state
            self.indent(1), self.fd.write('Mock' + self.class_name + ' ' + 'fsm;\n')
            self.indent(1), self.fd.write('fsm.start();')
            guard = self.graph[path[0]][path[1]]['data'].guard
            if guard != '':
                self.fd.write(' // If ' + guard)
            self.fd.write('\n')

            # Iterate on all nodes of the path
            for i in range(len(path) - 1):
                event = self.graph[path[i]][path[i+1]]['data'].event
                if event.name != '':
                    guard = self.graph[path[i]][path[i+1]]['data'].guard
                    self.indent(1), self.fd.write('fsm.' + event.caller() + ';')
                    if guard != '':
                        self.fd.write(' // If ' + guard)
                    self.fd.write('\n')
                if (i == len(path) - 2):
                    self.indent(1), self.fd.write('LOGD("Current state: %s\\n", fsm.c_str());\n')
                    self.indent(1), self.fd.write('ASSERT_EQ(fsm.state(), ' + self.enum_name + '::')
                    self.indent(1), self.fd.write(self.state_name(path[i+1]) + ');\n')
                    self.indent(1), self.fd.write('ASSERT_STREQ(fsm.c_str(), "' + path[i+1] + '");\n')
                elif self.graph[path[i+1]][path[i+2]]['data'].event.name != '':
                    self.indent(1), self.fd.write('LOGD("Current state: %s\\n", fsm.c_str());\n')
                    self.indent(1), self.fd.write('ASSERT_EQ(fsm.state(), ' + self.enum_name + '::')
                    self.fd.write(self.state_name(path[i+1]) + ');\n')
                    self.indent(1), self.fd.write('ASSERT_STREQ(fsm.c_str(), "' + path[i+1] + '");\n')
            self.fd.write('}\n\n')

    ###########################################################################
    ### Generate the main function doing unit tests
    ###########################################################################
    def generate_unit_tests_main_function(self, filename):
        self.generate_function_comment('Compile with one of the following line:\n' +
                                       '//! g++ --std=c++14 -Wall -Wextra -Wshadow ' +
                                       '-I../../include -DFSM_DEBUG ' + os.path.basename(filename) +
                                       ' `pkg-config --cflags --libs gtest gmock`')
        self.fd.write('int main(int argc, char *argv[])\n{\n')
        self.indent(1), self.fd.write('// The following line must be executed to initialize Google Mock\n')
        self.indent(1), self.fd.write('// (and Google Test) before running the tests.\n')
        self.indent(1), self.fd.write('::testing::InitGoogleMock(&argc, argv);\n')
        self.indent(1), self.fd.write('return RUN_ALL_TESTS();\n')
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
        self.generate_unit_tests_mocked_class()
        self.generate_unit_tests_check_initial_state()
        self.generate_unit_tests_check_cycles()
        self.generate_unit_tests_pathes_to_sinks()
        self.generate_unit_tests_footer()
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
            for dest in list(self.graph.neighbors(state)):
                tr = self.graph[state][dest]['data']
                s = self.state_name(state)
                d = self.state_name(dest)

                if tr.guard != '':
                    code += '        if (onGuardingTransition' + s + '_' + d + '())\n'
                elif tr.event.name == '': # Dummy event and dummy guard
                    if count == 1:
                        code += '\n#warning "Missformed state machine: missing guard from state ' + s + ' to state ' + d + '"\n'
                        code += '        /* MISSING GUARD: if (guard) */\n'
                    elif count > 1:
                        code += '\n#warning "Undeterminist State machine detected switching from state ' + s + ' to state ' + d + '"\n'

                if tr.event.name == '': # and state != self.initial_state:
                    code += '        {\n'
                    code += '            LOGD("[STATE ' + s +  '] Internal transition to state ' + d + '\\n");\n'
                    code += '            static StateMachine<' + self.class_name + ', ' + self.enum_name + '>::Transition tr =\n'
                    code += '            {\n'
                    code += '                .destination = ' + self.enum_name + '::' + d + ',\n'
                    if tr.guard != '':
                        code += '                // .guard = &' + self.class_name + '::onGuardingTransition' + s + '_' + d + ',\n'
                    if tr.action != '':
                        code += '                .action = &' + self.class_name + '::onTransitioning' + s + '_' + d + ',\n'
                    code += '            };\n'
                    code += '            transition(&tr);\n'
                    code += '            return ;\n'
                    code += '        }\n'
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
        for e in self.lookup_events:
            if e.name != '':
                return

        cycle = list(nx.simple_cycles(self.graph))
        if len(cycle) == 0:
            self.warning('The state machine shall have at least one event.')
            return
        str = ''
        for c in cycle[0]:
            str += ' ' + c
        self.warning('The state machine shall have at least one event to prevent infinite loop. ' +
                     'For example:' + str)

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
                tr = self.graph[state][d]['data']
                if (tr.event.name == '') and (tr.guard == ''):
                    self.warning('The state ' + state + ' has an issue with its transitions: it has' +
                                 ' several possible ways while the way to state ' + d +
                                 ' is always true and therefore will be always a candidate and transition' +
                                 ' to other states is non determinist.')
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

        # Initial/final states
        if tr.origin == '[*]':
            self.initial_state = '[*]'
        elif tr.destination == '[*]':
            tr.destination = '*'
            self.final_state = '*'

        # Add nodes first to be sure to access them later
        self.add_state(tr.origin)
        self.add_state(tr.destination)

        # Analyse the following optional plantUML code: ": event [ guard ] / action"
        for i in range(3, len(self.tokens)):
            if self.tokens[i] == 'event':
                self.parse_event(tr.event, self.tokens[i + 1])
                # Events are optional. If not given, we use them as anonymous internal event.
                # Store them in a dictionary: "event => (origin, destination) states" to create
                # the state transition for each event.
                self.lookup_events[tr.event].append((tr.origin, tr.destination))
            elif self.tokens[i] == 'guard':
                tr.guard = self.tokens[i + 1]
            elif self.tokens[i] == 'action':
                tr.action = self.tokens[i + 1]

            # Distinguish a transition cycling to its own state from the "on event" on the state
            if as_state and (tr.origin == tr.destination):
                if tr.action == '':
                    tr.action = '// Dummy action\n'
                    tr.action += '#warning "no state ' + tr.origin + ' reaciton to event ' + tr.event.name + '"'

        # Store parsed information as edge of the graph
        self.add_transition(tr)

    ###########################################################################
    ### Parse the following plantUML code and store information of the analyse:
    ### FIXME: limitation only one "State : on event [ guard ] / action" allowed!
    ###    State : entry / action
    ###    State : exit / action
    ###    State : on event [ guard ] / action
    ###    State : do / activity
    ### We also offering some unofficial alternative name:
    ###    State : entering / action
    ###    State : leaving / action
    ###    State : event event [ guard ] / action
    ###    State : activity / activity
    ###    State : comment / C++ comment
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
        state = self.graph.nodes[name]['data']
        if (what in ['entry', 'entering']) and (self.tokens[3] in ['/', ':']):
            state.entering += '        '
            state.entering += ' '.join(self.tokens[4:]) + ';\n'
        elif (what in ['exit', 'leaving']) and (self.tokens[3] in ['/', ':']):
            state.leaving += '        '
            state.leaving += ' '.join(self.tokens[4:]) + ';\n'
        elif what == 'comment':
            state.comment += ' '.join(self.tokens[4:])
        # 'on event' is not sugar syntax to a real transition: since it disables
        # 'entry' and 'exit' actions but we want create a real graph edege to
        # help us on graph theory traversal algorithm (like finding cycles).
        elif what in ['on', 'event']:
            self.tokens = [ name, '->', name, ':' ] + self.tokens[3:]
            self.parse_transition(True)
        elif what in ['do', 'activity']:
            state.activity += ' '.join(self.tokens[4:])
        else:
            self.parse_error('Bad syntax describing a state. Unkown token "' + what + '"')

    ###########################################################################
    ### Extend the PlantUML single-line comments to add extra commands to help
    ### generating C++ code. For examples:
    ### Add code before and after the generated code:
    ###   'header #include <foo>
    ###   'footer class Foo {
    ###   'footer private: ...
    ###   'footer };
    ### Add extra member functions or member variables:
    ###   'code private:
    ###   'code void extra_method();
    ### Add extra arguments to the constructor:
    ###   'param Foo foo
    ###   'param Bar bar
    ### Add code in the constructor
    ###   'init bar.x = 42;
    ### Unit tests:
    ###   'test ...
    ###########################################################################
    def parse_extra_code(self, what, code):
        if what == '[header]':
            self.extra_code.header += code
        elif what == '[footer]':
            self.extra_code.footer += code
        elif what == '[param]':
            if self.extra_code.argvs != '':
                self.extra_code.argvs += ', '
            self.extra_code.argvs += code
        elif what == '[init]':
            self.extra_code.init += '        '
            self.extra_code.init += code
        elif what == '[code]':
            self.extra_code.functions += '    '
            self.extra_code.init += code
        elif what == '[test]':
            self.extra_code.unit_tests += code
        else:
            self.fatal('Token ' + what + ' not yet managed')

    ###########################################################################
    ### Traverse the Abstract Syntax Tree of the PlantUML file
    ###########################################################################
    def visit_ast(self, inst):
        if inst.data == 'state_diagram':  # FIXME To be removed when creating the AST
            for c in inst.children:
                self.visit_ast(c)
        elif inst.data == 'cpp_code':
            self.parse_extra_code(str(inst.children[0]))
        elif inst.data == 'transition':
            self.tokens = [inst.children[0], inst.children[1], inst.children[2]]
            for i in range(3, len(inst.children)):
                self.tokens.append(inst.children[i])
                self.tokens.append(inst.children[i].children[0])
            self.parse_transition()
        elif inst.data in ['comment', 'skin', 'state_entry', 'state_exit', 'state_comment', 'state_event']: ############# FIXME
            return
        else:
            self.fatal('Token ' + inst.data + ' not yet managed')

    ###########################################################################
    ### Load the PlantUML statechart grammar file
    ###########################################################################
    def load_plantuml_grammar_file(self, grammar_file):
        try:
            self.fd = open(grammar_file)
            self.parser = Lark(self.fd.read())
            self.fd.close()
        except Exception as FileNotFoundError:
            self.fatal('Failed loading grammar file for parsing plantuml statechart')

    ###########################################################################
    ### Parse plantUML file parser and create a graph structure.
    ###########################################################################
    def parse_plantuml_file(self, umlfile, cpp_or_hpp, classname):
        self.reset()
        self.name = Path(umlfile).stem
        self.class_name = self.name + classname
        self.enum_name = self.class_name + 'States'
        # Make the plantUMl file read by the parser
        if self.parser == None:
            self.load_plantuml_grammar_file('/home/qq/MyGitHub/StateMachine/tool/statechart.ebnf')
        self.fd = open(umlfile, 'r')
        self.ast = self.parser.parse(self.fd.read())
        self.fd.close()
        # Traverse the AST to create the graph structure of the state machine
        for inst in self.ast.children:
            self.visit_ast(inst)

    ###########################################################################
    ### Entry point for translating a plantUML file into a C++ source file.
    ### umlfile: path to the plantuml file.
    ### cpp_or_hpp: generated a C++ source file ('cpp') or a C++ header file ('hpp').
    ### classname: postfix name for the state machine name.
    ###########################################################################
    def translate(self, umlfile, cpp_or_hpp, classname):
        if not os.path.isfile(umlfile):
            print('File path ' + umlfile + ' does not exist. Exiting!')
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
