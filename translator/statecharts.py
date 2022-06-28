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
### Console color for print
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
###    getQuarter
###    getQuarter()
###    get quarter
###    get quarter()
###    setSpeed(x)
###    fooBar(x, y)
###############################################################################
class Event(object):
    def __init__(self):
        # Unique name of the event
        self.name = ''
        # List of optional arguments (data to the event)
        self.params = []

    ###########################################################################
    ### Generate the definition of the C++ method.
    ###########################################################################
    def header(self):
        params = ''
        for p in self.params:
            if params != '':
                params += ', '
            params += p.upper() + ' const& ' + p
        return 'void ' + self.name + '(' + params + ')'

    ###########################################################################
    ### Generate the call of the C++ method.
    ###########################################################################
    def caller(self):
        i = 0
        params = ''
        for p in self.params:
            if params != '':
                params += ', ' + self.name.lower() + '_x[' + str(i) + ']'
                i += 1
            params += p.lower()
        return self.name + '(' + params + ')'

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
        # Event name and arguments
        self.event = Event()
        # Guard code (boolean expression)
        self.guard = ''
        # Action code (C++ code or pseudo code)
        self.action = ''
        # Expected number of times the mock is called
        self.count_guard = 0
        self.count_action = 0

    def __str__(self):
        return self.origin + ' ==> ' + self.destination + ' : ' + \
               self.event.name + ' [' + self.guard + '] / ' + self.action

###############################################################################
### Structure holding information after having parsed a PlantUML state.
### Example of PlantUML state:
###     state : entry / action
###     state : exit / action
###     state : do / activity
###     state : on event [ guard ] / action (note this case will be converted
### into a graph edge instead of graph node).
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
        # State activity.
        self.activity = ''
        # Internal transition when no events are explicitely set.
        self.internal = ''
        # Expected number of times the mock is called0
        self.count_entering = 0
        self.count_leaving = 0

    def __str__(self):
        return self.name + ': ' + self.entering + ' / ' + self.leaving

###############################################################################
### Structure holding extra C++ code to be merged within the generated code.
###############################################################################
class ExtraCode(object):
    def __init__(self):
        # Code to be placed on the header of the generated code (before the
        # state machine class definition).
        self.header = ''
        # Code to be placed on the footer of the generated code (after the
        # state machine class definition).
        self.footer = ''
        # Arguments to the state machine class constructor method.
        self.argvs = ''
        # Code to be placed inside the class constructor method and the reset
        # method.
        self.init = ''
        # Code to be placed inside the state machine class to define extra
        # member functions and extra member variables.
        self.functions = ''
        # Code to be placed inside the unit tests file to prepare tests.
        self.unit_tests = ''

###############################################################################
### Context of the parser translating a PlantUML file depicting a state machine
### into a C++ file state machine holding some unit tests.
### See https://plantuml.com/fr/state-diagram
###############################################################################
class Parser(object):
    def __init__(self):
        # Context-free language parser (Lark lib)
        self.parser = None
        # Abstract Syntax Tree (Lark lib)
        self.ast = None
        # List of tokens split from the AST (ugly hack !!!).
        self.tokens = []
        # File descriptor of the opened file (plantUML, generated files).
        self.fd = None
        # Name of the plantUML file (input of the tool).
        self.umlfile = ''
        # Stem of the plantUML file.
        self.name = ''
        # The name of the generated C++ state machine class.
        self.class_name = ''
        # The name of the generated C++ state machine enum.
        self.enum_name = ''
        # Store the graph of the state machine.
        # FIXME shall be nx.MultiDiGraph() since we cannot create several events
        # leaving and entering to the same state or two events from a source
        # state going to the same destination state.
        self.graph = nx.DiGraph()
        # Dictionnary of "event => (source state, destination state)" needed for
        # computing tables of state transitions for each events.
        self.lookup_events = defaultdict(list)
        # Memorize the initial state of the state machine.
        self.initial_state = ''
        # Memorize the final state of the state machine.
        self.final_state = ''
        # Extra C++ code to be merged inside the generated file.
        self.extra_code = ExtraCode()
        # Generate C++ warnings inside the generated file when missformed state
        # machine is detected.
        self.warnings = ''

    ###########################################################################
    ### Reset states.
    ### Note: self.parser is not reloaded since we only parse statecharts.
    ###########################################################################
    def reset(self):
        self.ast = None
        self.tokens = []
        self.name = ''
        self.class_name = ''
        self.enum_name = ''
        self.graph = nx.DiGraph() # TODO nx.MultiDiGraph()
        self.lookup_events = defaultdict(list)
        self.initial_state = ''
        self.final_state = ''
        self.extra_code = ExtraCode()
        self.warnings = ''

    ###########################################################################
    ### Is the generated file should be a C++ source file or header file ?
    ### param[in] file path of the file to be generated.
    ### return True if the file extension matches for a C++ header file.
    ###########################################################################
    def is_hpp_file(self, file):
        filename, extension = os.path.splitext(file)
        return True if extension in ['.h', '.hpp', '.hh', '.hxx'] else False

    ###########################################################################
    ### Print a warning message on the console.
    ### param[in] msg the message to print.
    ###########################################################################
    def warning(self, msg):
        self.warnings += msg
        print(f"{bcolors.WARNING}   WARNING in the state machine " + self.name \
              + ": "  + msg + f"{bcolors.ENDC}")

    ###########################################################################
    ### Print a general error message on the console and exit the application.
    ### param[in] msg the message to print.
    ###########################################################################
    def fatal(self, msg):
        print(f"{bcolors.FAIL}   FATAL in the state machine " + self.name + \
              ": " + msg + f"{bcolors.ENDC}")
        sys.exit(-1)

    ###########################################################################
    ### Add a graph node with a dummy attribute named 'data' of type State.
    ### The node is created if and only if it does not belong to the graph.
    ### param[in] name the name of the state.
    ###########################################################################
    def add_state(self, name):
        if not self.graph.has_node(name):
            self.graph.add_node(name, data = State(name))

    ###########################################################################
    ### Add a graph edge with the given attribute named 'data' of type Transition
    ### Note: the graph source node and the graph source destination shall have
    ### been inserted first.
    ### param[in] tr the state machine transition.
    ###########################################################################
    def add_transition(self, tr):
        self.graph.add_edge(tr.origin, tr.destination, data=tr)

    ###########################################################################
    ### Return all cycles in the graph (list of list of nodes).
    ### Cycles may not start from initial state, therefore do some permutation
    ### are made to be sure to give a list starting with the initial state.
    ### return list of list of nodes.
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
    ### Return the list of graph edges in a depth-first-search (DFS).
    ###########################################################################
    def graph_dfs(self):
         return list(nx.dfs_edges(self.graph, source=self.initial_state))

    ###########################################################################
    ### Return all paths from all sources to sinks (list of list of nodes).
    ### This is a general algorithm since a state machine starts from a single
    ### entry node.
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
    ### Generate a separator line for function.
    ### param[in] spaces the number of spaces char to print.
    ### param[in] the space character to print.
    ### param[in] count the number of character to print a line of comment.
    ### param[in] c the comment line character to print.
    ###########################################################################
    def generate_line_separator(self, spaces, s, count, c):
        self.fd.write(s * spaces)
        self.fd.write('//')
        self.fd.write(c * count)
        self.fd.write('\n')

    ###########################################################################
    ### Generate a function or a method comment with its text and lines as
    ### separtor. Comment separator follows the comment size (80 as min size).
    ### param[in] spaces the number of spaces char to print.
    ### param[in] the space character to print.
    ### param[in] comment the message in the comment.
    ### param[in] c the comment line character to print.
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
    ### Generate function comment with its text.
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
    ### param[in] count the depth of indentation.
    ###########################################################################
    def indent(self, depth):
        self.fd.write(' ' * 4 * depth)

    ###########################################################################
    ### You can add here your copyright, license ...
    ###########################################################################
    def generate_common_header(self):
        self.fd.write('// This file as been generated the ')
        self.fd.write(date.today().strftime("%B %d, %Y"))
        self.fd.write(' from the PlantUML statechart ' + self.umlfile)
        self.fd.write('\n// This code generation is still experimental. Some '
                      'border cases may not be correctly managed!\n\n')

    ###########################################################################
    ### Code generator: add the header file.
    ### param[in] hpp set to True if generated file is a C++ header file.
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
        self.fd.write('\n')

    ###########################################################################
    ### Code generator: add the footer file.
    ### param[in] hpp set to True if generated file is a C++ header file.
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
        self.fd.write('static inline const char* stringify(' + self.enum_name + \
                      ' const state)\n{\n')
        self.indent(1), self.fd.write('static const char* s_states[] =\n')
        self.indent(1), self.fd.write('{\n')
        for state in list(self.graph.nodes):
            self.indent(2), self.fd.write('[' + self.state_enum(state) + '] = "' + state + '",\n')
        self.indent(1), self.fd.write('};\n\n')
        self.indent(1), self.fd.write('return s_states[state];\n};\n\n')

    ###########################################################################
    ### Convert the state name (PlantUML name to C++ name)
    ### param[in] state the PlantUML name of the state.
    ### return the C++ name.
    ###########################################################################
    def state_name(self, state):
        if state == '[*]':
            return 'CONSTRUCTOR'
        if state == '*':
            return 'DESTRUCTOR'
        return state

    ###########################################################################
    ### Return the C++ enum for the given state.
    ### param[in] state the PlantUML name of the state.
    ###########################################################################
    def state_enum(self, state):
        return self.enum_name + '::' + self.state_name(state)

    ###########################################################################
    ### Return the C++ method for transition guards.
    ### param[in] source the origin state (PlantUML name).
    ### param[in] destination the destination state (PlantUML name).
    ### param[in] class_name if True prepend the class name.
    ###########################################################################
    def guard_function(self, source, destination, class_name=False):
        s = self.class_name + '::' if class_name else ''
        return s + 'onGuarding_' + self.state_name(source) + '_' + self.state_name(destination)

    ###########################################################################
    ### Return the C++ method for transition actions.
    ### param[in] source the origin state (PlantUML name).
    ### param[in] destination the destination state (PlantUML name).
    ### param[in] class_name if True prepend the class name.
    ###########################################################################
    def transition_function(self, source, destination, class_name=False):
        s = self.class_name + '::' if class_name else ''
        return s + 'onTransitioning_' + self.state_name(source) + '_' + self.state_name(destination)

    ###########################################################################
    ### Return the C++ method for entering state actions.
    ### param[in] state the PlantUML name of the state.
    ### param[in] entering if True for entering actions else for leaving action.
    ###########################################################################
    def state_entering_function(self, state, class_name=True):
        s = self.class_name + '::' if class_name else ''
        return s + 'onEntering_' + self.state_name(state)

    ###########################################################################
    ### Return the C++ method for leaving state actions.
    ### param[in] state the PlantUML name of the state.
    ### param[in] entering if True for entering actions else for leaving action.
    ###########################################################################
    def state_leaving_function(self, state, class_name=True):
        s = self.class_name + '::' if class_name else ''
        return s + 'onLeaving_' + self.state_name(state)

    ###########################################################################
    ### Return the C++ method for internal state transition.
    ### param[in] state the PlantUML name of the state.
    ### param[in] entering if True for entering actions else for leaving action.
    ###########################################################################
    def state_internal_function(self, state, class_name=True):
        s = self.class_name + '::' if class_name else ''
        return s + 'onInternal_' + self.state_name(state)

    ###########################################################################
    ### Generate the table of states holding their entering or leaving actions.
    ### Note: the table may be empty (all states do not actions) in this case
    ### the table is not generated.
    ###########################################################################
    def generate_table_of_states(self):
        for state in list(self.graph.nodes):
            s = self.graph.nodes[state]['data']
            # Sparse notation: nullptr are inmplicit so skip it
            if (s.name == '[*]'):
                continue
            if s.entering == '' and s.leaving == '' and s.internal == '':
                continue
            self.indent(2), self.fd.write('m_states[' + self.state_enum(s.name) + '] =\n')
            self.indent(2), self.fd.write('{\n')
            if s.leaving != '':
                self.indent(3), self.fd.write('.leaving = &')
                self.fd.write(self.state_leaving_function(state, True))
                self.fd.write(',\n')
            if s.entering != '':
                self.indent(3), self.fd.write('.entering = &')
                self.fd.write(self.state_entering_function(state, True))
                self.fd.write(',\n')
            if s.internal != '':
                self.indent(3), self.fd.write('.internal = &')
                self.fd.write(self.state_internal_function(state, True))
                self.fd.write(',\n')
            #if s.activity != '':
            #    self.generate_pointer_function('activity', s.name)
            self.indent(2), self.fd.write('};\n')

    ###########################################################################
    ### Generate the code of the state machine constructor method.
    ###########################################################################
    def generate_constructor_method(self):
        self.generate_method_comment('Default constructor. Start from initial '
                                     'state and call it actions.')
        self.indent(1)
        self.fd.write(self.class_name + '(' + self.extra_code.argvs + ')\n')
        self.indent(2), self.fd.write(': StateMachine(' + self.state_enum(self.initial_state) + ')\n')
        self.indent(1), self.fd.write('{\n')
        self.generate_table_of_states()
        self.fd.write(self.extra_code.init)
        self.indent(1), self.fd.write('}\n\n')

    ###########################################################################
    ### Generate the code of the state machine destructor method.
    ###########################################################################
    def generate_destructor_method(self):
        self.fd.write('#if defined(MOCKABLE)\n')
        self.generate_method_comment('Needed because of virtual methods.')
        self.indent(1)
        self.fd.write('virtual ~' + self.class_name + '(' + self.extra_code.argvs + ') = default;\n')
        self.fd.write('#endif\n\n')

    ###########################################################################
    ### Generate the state machine start method (equivalent to a reset).
    ###########################################################################
    def generate_reset_method(self):
        self.generate_method_comment('Reset the state machine.')
        self.indent(1), self.fd.write('void start()\n')
        self.indent(1), self.fd.write('{\n')
        self.indent(2), self.fd.write('StateMachine::start();\n')
        self.fd.write(self.extra_code.init)
        self.indent(2), self.fd.write('onInternal_CONSTRUCTOR();\n')
        self.indent(1), self.fd.write('}\n\n')

    ###########################################################################
    ### Generate external events to the state machine (public methods).
    ###########################################################################
    def generate_event_methods(self):
        for event, arcs in self.lookup_events.items():
            if event.name == '':
                continue

            self.generate_method_comment('External event.')
            self.indent(1), self.fd.write(event.header() + '\n')
            self.indent(1), self.fd.write('{\n')
            self.indent(2), self.fd.write('LOGD("[' + self.class_name.upper() + '][EVENT %s]\\n", __func__);\n\n')
            self.indent(2), self.fd.write('static const Transitions s_transitions =\n')
            self.indent(2), self.fd.write('{\n')
            for origin, destination in arcs:
                tr = self.graph[origin][destination]['data']
                self.indent(3), self.fd.write('{\n')
                self.indent(4), self.fd.write(self.state_enum(origin) + ',\n')
                self.indent(4), self.fd.write('{\n')
                self.indent(5), self.fd.write('.destination = ' + self.state_enum(destination) + ',\n')
                if tr.guard != '':
                    self.indent(5), self.fd.write('.guard = &' + self.guard_function(origin, destination, True) + ',\n')
                if tr.action != '':
                    self.indent(5), self.fd.write('.action = &' + self.transition_function(origin, destination, True) + ',\n')
                self.indent(4), self.fd.write('},\n')
                self.indent(3), self.fd.write('},\n')
            self.indent(2), self.fd.write('};\n\n')
            self.indent(2), self.fd.write('transition(s_transitions);\n')
            self.indent(1), self.fd.write('}\n\n')

    ###########################################################################
    ### Generate guards and actions on transitions.
    ###########################################################################
    def generate_transition_methods(self):
        transitions = list(self.graph.edges)
        for origin, destination in transitions:
            tr = self.graph[origin][destination]['data']
            if tr.guard != '':
                self.generate_method_comment('Guard the transition from state ' + origin  + ' to state ' + destination + '.')
                self.indent(1), self.fd.write('MOCKABLE bool ' + self.guard_function(origin, destination) + '()\n')
                self.indent(1), self.fd.write('{\n')
                self.indent(2), self.fd.write('const bool guard = (' + tr.guard + ');\n')
                self.indent(2), self.fd.write('LOGD("[' + self.class_name.upper() + '][GUARD ' + origin + ' --> ' + destination + ': ' + tr.guard + '] result: %s\\n",\n')
                self.indent(3), self.fd.write('(guard ? "true" : "false"));\n')
                self.indent(2), self.fd.write('return guard;\n')
                self.indent(1), self.fd.write('}\n\n')

            if tr.action != '':
                self.generate_method_comment('Do the action when transitioning from state ' + origin + ' to state ' + destination + '.')
                self.indent(1), self.fd.write('MOCKABLE void ' + self.transition_function(origin, destination) + '()\n')
                self.indent(1), self.fd.write('{\n')
                self.indent(2), self.fd.write('LOGD("[' + self.class_name.upper() + '][TRANSITION ' + origin + ' --> ' + destination)
                if tr.action[0:2] != '//':
                    self.fd.write(': ' + tr.action + ']\\n");\n')
                else: # Cannot display action since contains comment + warnings
                    self.fd.write(']\\n");\n')
                self.indent(2), self.fd.write(tr.action + ';\n')
                self.indent(1), self.fd.write('}\n\n')

    ###########################################################################
    ### Generate leaving and entering actions associated to states.
    ###########################################################################
    def generate_state_methods(self):
        nodes = list(self.graph.nodes)
        for node in nodes:
            state = self.graph.nodes[node]['data']
            if state.entering != '':
                self.generate_method_comment('Do the action when entering the state ' + state.name + '.')
                self.indent(1), self.fd.write('MOCKABLE void ' + self.state_entering_function(node, False) + '()\n')
                self.indent(1), self.fd.write('{\n')
                self.indent(2), self.fd.write('LOGD("[' + self.class_name.upper() + '][ENTERING STATE ' + state.name + ']\\n");\n')
                self.fd.write(state.entering)
                self.indent(1), self.fd.write('}\n\n')

            if state.leaving != '':
                self.generate_method_comment('Do the action when leaving the state ' + state.name + '.')
                self.indent(1), self.fd.write('MOCKABLE void ' + self.state_leaving_function(node, False) + '()\n')
                self.indent(1), self.fd.write('{\n')
                self.indent(2), self.fd.write('LOGD("[' + self.class_name.upper() + '][LEAVING STATE ' + state.name + ']\\n");\n')
                self.fd.write(state.leaving)
                self.indent(1), self.fd.write('}\n\n')

            if state.internal != '':
                self.generate_method_comment('Do the internal transition when leaving the state ' + state.name + '.')
                self.indent(1), self.fd.write('void ' + self.state_internal_function(node, False) + '()\n')
                self.indent(1), self.fd.write('{\n')
                self.indent(2), self.fd.write('LOGD("[' + self.class_name.upper() + '][INTERNAL TRANSITION FROM STATE ' + node + ']\\n");\n')
                self.fd.write(state.internal)
                self.indent(1), self.fd.write('}\n\n')

    ###########################################################################
    ### Entry point to generate the whole state machine class and all its methods.
    ###########################################################################
    def generate_state_machine_class(self):
        self.generate_function_comment('State machine concrete implementation.')
        self.fd.write('class ' + self.class_name + ' : public StateMachine<')
        self.fd.write(self.class_name + ', ' + self.enum_name + '>\n')
        self.fd.write('{\n')
        self.fd.write('public: // Constructor and external events\n\n')
        self.generate_constructor_method()
        self.generate_destructor_method()
        self.generate_reset_method()
        self.generate_event_methods()
        self.fd.write('private: // Guards and actions on transitions\n\n')
        self.generate_transition_methods()
        self.generate_state_methods()
        self.fd.write(self.extra_code.functions)
        self.fd.write('};\n\n')

    ###########################################################################
    ### Generate the header part of the unit test file.
    ###########################################################################
    def generate_unit_tests_header(self):
        self.generate_common_header()
        self.fd.write('#define MOCKABLE virtual\n')
        self.fd.write('#include "' + self.class_name + '.hpp"\n')
        self.fd.write('#include <gmock/gmock.h>\n')
        self.fd.write('#include <gtest/gtest.h>\n')
        self.fd.write('#include <cstring>\n\n')
        self.fd.write('using namespace ::testing;\n\n')
        self.fd.write(self.extra_code.unit_tests)
        if self.extra_code.unit_tests != '':
            self.fd.write('\n')

    ###########################################################################
    ### Generate the footer part of the unit test file.
    ###########################################################################
    def generate_unit_tests_footer(self):
        pass

    ###########################################################################
    ### Generate the mocked state machine class.
    ###########################################################################
    def generate_unit_tests_mocked_class(self):
        self.generate_function_comment('Mocked state machine')
        self.fd.write('class Mock' + self.class_name + ' : public ' + self.class_name)
        self.fd.write('\n{\npublic:\n')
        transitions = list(self.graph.edges)
        for origin, destination in transitions:
            tr = self.graph[origin][destination]['data']
            if tr.guard != '':
                self.fd.write('    MOCK_METHOD(bool, ' + self.guard_function(origin, destination))
                self.fd.write(', (), (override));\n')
            if tr.action != '':
                self.fd.write('    MOCK_METHOD(void, ' + self.transition_function(origin, destination))
                self.fd.write(', (), (override));\n')
        for node in list(self.graph.nodes):
            state = self.graph.nodes[node]['data']
            if state.entering != '':
                self.fd.write('    MOCK_METHOD(void, ' + self.state_entering_function(node, False) + ', (), (override));\n')
            if state.leaving != '':
                self.fd.write('    MOCK_METHOD(void, ' + self.state_leaving_function(node, False) + ', (), (override));\n')
        self.fd.write('};\n\n')

    ###########################################################################
    ### Reset mock counters.
    ###########################################################################
    def reset_mock_counters(self):
        transitions = list(self.graph.edges)
        for origin, destination in transitions:
            tr = self.graph[origin][destination]['data']
            if tr.guard != '':
                tr.count_guard = 0
            if tr.action != '':
                tr.count_action = 0
        nodes = list(self.graph.nodes)
        for node in nodes:
            state = self.graph.nodes[node]['data']
            if state.entering != '':
                state.count_entering = 0
            if state.leaving != '':
                state.count_leaving = 0

    ###########################################################################
    ### Count the number of times the entering and leaving actions are called.
    ###########################################################################
    def count_mocked_guards(self, cycle):
        self.reset_mock_counters()
        for i in range(len(cycle) - 1):
            tr = self.graph[cycle[i]][cycle[i+1]]['data'];
            if tr.guard != '':
                tr.count_guard += 1
            if tr.action != '':
                tr.count_action += 1
            source = self.graph.nodes[cycle[i]]['data']
            destination = self.graph.nodes[cycle[i+1]]['data']
            if source.leaving != '' and source.name != destination.name:
                source.count_leaving += 1
            if destination.entering != '' and source.name != destination.name:
                destination.count_entering += 1

    ###########################################################################
    ### Generate mock guards.
    ###########################################################################
    def generate_mocked_guards(self):
        transitions = list(self.graph.edges)
        for origin, destination in transitions:
            tr = self.graph[origin][destination]['data']
            if tr.guard != '':
                self.fd.write('    EXPECT_CALL(fsm, ' + self.guard_function(origin, destination) + '())')
                if tr.count_guard == 0:
                    self.fd.write('.WillRepeatedly(Return(false));\n')
                else:
                    self.fd.write('.WillRepeatedly(Return(true));\n')
            if tr.action != '':
                self.fd.write('    EXPECT_CALL(fsm, ' + self.transition_function(origin, destination, False) + '())')
                self.fd.write('.Times(' + str(tr.count_action) + ');\n')
        nodes = list(self.graph.nodes)
        for node in nodes:
            state = self.graph.nodes[node]['data']
            if state.entering != '':
                self.fd.write('    EXPECT_CALL(fsm, ' + self.state_entering_function(node, False) + '())')
                self.fd.write('.Times(' + str(state.count_entering) + ');\n')
            if state.leaving != '':
                self.fd.write('    EXPECT_CALL(fsm, ' + self.state_leaving_function(node, False) + '())')
                self.fd.write('.Times(' + str(state.count_leaving) + ');\n')

    ###########################################################################
    ### Generate mock guards.
    ###########################################################################
    def generate_mocked_actions(self, cycle):
        for i in range(len(cycle) - 1):
            tr = self.graph[cycle[i]][cycle[i+1]]['data'];
            if tr.guard != '':
                tr.count_guard += 1
            if tr.action != '':
                tr.count_action += 1
        for node in cycle:
            state = self.graph.nodes[node]['data']
            if state.entering != '':
                state.count_entering += 1
            if state.leaving != '':
                state.count_leaving += 1

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
        self.indent(1), self.fd.write('fsm.start();\n\n')
        self.generate_unit_tests_assertions_initial_state()
        self.fd.write('}\n\n')

    ###########################################################################
    ### Generate checks on all cycles
    ###########################################################################
    def generate_unit_tests_check_cycles(self):
        count = 0
        cycles = self.graph_cycles()
        for cycle in cycles:
            self.count_mocked_guards(['[*]'] + cycle)
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
            self.generate_mocked_guards()
            self.fd.write('\n'), self.indent(1), self.fd.write('fsm.start();\n')
            guard = self.graph[self.initial_state][cycle[0]]['data'].guard
            self.indent(1), self.fd.write('LOGD("[UNIT TEST] Current state: %s\\n", fsm.c_str());\n')
            self.indent(1), self.fd.write('ASSERT_EQ(fsm.state(), ' + self.state_enum(cycle[0]) + ');\n')
            self.indent(1), self.fd.write('ASSERT_STREQ(fsm.c_str(), "' + cycle[0] + '");\n')

            # Iterate on all nodes of the cycle
            for i in range(len(cycle) - 1):
# FIXME
#                # External event not leaving the current state
#                if self.graph.has_edge(cycle[i], cycle[i]) and (cycle[i] != cycle[i+1]):
#                    tr = self.graph[cycle[i]][cycle[i]]['data']
#                    if tr.event.name != '':
#                        self.indent(1), self.fd.write('LOGD("[' + self.class_name.upper() + ']// Event ' + tr.event.name + ' [' + tr.guard + ']: ' + cycle[i] + ' <--> ' + cycle[i] + '\\n");\n')
#                        self.indent(1), self.fd.write('fsm.' + tr.event.caller() + ';')
#                        if tr.guard != '':
#                            self.fd.write(' // If ' + tr.guard)
#                        self.fd.write('\n')
#                        self.indent(1), self.fd.write('LOGD("[' + self.class_name.upper() + '] Current state: %s\\n", fsm.c_str());\n')
#                        self.indent(1), self.fd.write('ASSERT_EQ(fsm.state(), ' + self.state_enum(cycle[i]) + ');\n')
#                        self.indent(1), self.fd.write('ASSERT_STREQ(fsm.c_str(), "' + cycle[i] + '");\n')

                # External event: print the name of the event + its guard
                tr = self.graph[cycle[i]][cycle[i+1]]['data']
                if tr.event.name != '':
                    self.fd.write('\n'), self.indent(1)
                    self.fd.write('LOGD("\\n[' + self.class_name.upper() + '] Triggering event ' + tr.event.name + ' [' + tr.guard + ']: ' + cycle[i] + ' ==> ' + cycle[i + 1] + '\\n");\n')
                    self.indent(1), self.fd.write('fsm.' + tr.event.caller() + ';\n')

                if (i == len(cycle) - 2):
                    # Cycle of non external evants => malformed state machine
                    # I think this case is not good
                    if self.graph[cycle[i+1]][cycle[1]]['data'].event.name == '':
                        self.indent(1), self.fd.write('#warning "Malformed state machine: unreachable destination state"\n\n')
                    else:
                        # No explicit event => direct internal transition to the state if an explicit event can occures.
                        self.indent(1), self.fd.write('LOGD("[UNIT TEST] Current state: %s\\n", fsm.c_str());\n')
                        self.indent(1), self.fd.write('ASSERT_EQ(fsm.state(), ' + self.state_enum(cycle[i+1]) + ');\n')
                        self.indent(1), self.fd.write('ASSERT_STREQ(fsm.c_str(), "' + cycle[i+1] + '");\n')

                # No explicit event => direct internal transition to the state if an explicit event can occures.
                # Else skip test for the destination state since we cannot test its internal state
                elif self.graph[cycle[i+1]][cycle[i+2]]['data'].event.name != '':
                    self.indent(1), self.fd.write('LOGD("[UNIT TEST] Current state: %s\\n", fsm.c_str());\n')
                    self.indent(1), self.fd.write('ASSERT_EQ(fsm.state(), ' + self.state_enum(cycle[i+1]) + ');\n')
                    self.indent(1), self.fd.write('ASSERT_STREQ(fsm.c_str(), "' + cycle[i+1] + '");\n')
            self.fd.write('}\n\n')

    ###########################################################################
    ### Generate checks on pathes to all sinks
    ###########################################################################
    def generate_unit_tests_pathes_to_sinks(self):
        count = 0
        pathes = self.graph_all_paths_to_sinks()
        for path in pathes:
            self.count_mocked_guards(path)
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
            self.generate_mocked_guards()
            self.fd.write('\n'), self.indent(1), self.fd.write('fsm.start();\n')

            # Iterate on all nodes of the path
            for i in range(len(path) - 1):
                event = self.graph[path[i]][path[i+1]]['data'].event
                if event.name != '':
                    guard = self.graph[path[i]][path[i+1]]['data'].guard
                    self.fd.write('\n'), self.indent(1)
                    self.fd.write('LOGD("[' + self.class_name.upper() + ']\\nEvent ' + event.name + ' [' + guard + ']: ' + path[i] + ' ==> ' + path[i + 1] + '\\n");\n')
                    self.fd.write('\n'), self.indent(1), self.fd.write('fsm.' + event.caller() + ';\n')
                if (i == len(path) - 2):
                    self.indent(1), self.fd.write('LOGD("[UNIT TEST] Current state: %s\\n", fsm.c_str());\n')
                    self.indent(1), self.fd.write('ASSERT_EQ(fsm.state(), ' + self.state_enum(path[i+1]) + ');\n')
                    self.indent(1), self.fd.write('ASSERT_STREQ(fsm.c_str(), "' + path[i+1] + '");\n')
                elif self.graph[path[i+1]][path[i+2]]['data'].event.name != '':
                    self.indent(1), self.fd.write('LOGD("[UNIT TEST] Current state: %s\\n", fsm.c_str());\n')
                    self.indent(1), self.fd.write('ASSERT_EQ(fsm.state(), ' + self.state_enum(path[i+1]) + ');\n')
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
        #self.generate_unit_tests_check_initial_state()
        self.generate_unit_tests_check_cycles()
        self.generate_unit_tests_pathes_to_sinks()
        self.generate_unit_tests_main_function(filename)
        self.generate_unit_tests_footer()
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
        for state in list(self.graph.nodes()):
            for dest in list(self.graph.neighbors(state)):
                tr = self.graph[state][dest]['data']
                if (tr.event.name == '') and (state not in states):
                    states.append(state)

        # Generate the internal transition in the entry action of the source state
        for state in states:
            count = 0 # count number of ways
            code = ''
            for dest in list(self.graph.neighbors(state)):
                tr = self.graph[state][dest]['data']
                s = self.state_name(state)
                d = self.state_name(dest)

                if tr.guard != '':
                    code += '        if (' + self.guard_function(state, dest) + '())\n'
                elif tr.event.name == '': # Dummy event and dummy guard
                    if count == 1:
                        code += '\n#warning "Missformed state machine: missing guard from state ' + s + ' to state ' + d + '"\n'
                        code += '        /* MISSING GUARD: if (guard) */\n'
                    elif count > 1:
                        code += '\n#warning "Undeterminist State machine detected switching from state ' + s + ' to state ' + d + '"\n'

                if tr.event.name == '': # and state != self.initial_state:
                    code += '        {\n'
                    code += '            LOGD("[' + self.class_name.upper() + '][STATE ' + state +  '] Candidate for internal transitioning to state ' + dest + '\\n");\n'
                    code += '            static const Transition tr =\n'
                    code += '            {\n'
                    code += '                .destination = ' + self.state_enum(dest) + ',\n'
                    if tr.action != '':
                        code += '                .action = &' + self.transition_function(state, dest, True) + ',\n'
                    code += '            };\n'
                    code += '            transition(&tr);\n'
                    code += '            return ;\n'
                    code += '        }\n'
                    count += 1
            self.graph.nodes[state]['data'].internal += code

    ###########################################################################
    ### The state machine shall have an initial state.
    ###########################################################################
    def verify_initial_state(self):
        if self.initial_state == '':
            self.fatal('Missing initial state')

    ###########################################################################
    ### Count the total number of events which shall be > 1
    ###########################################################################
    def verify_number_of_events(self):
        for e in self.lookup_events:
            if e.name != '':
                return
        self.warning('The state machine shall have at least one event.')

    ###########################################################################
    ### Check infinite loops
    ###########################################################################
    def verify_infinite_loops(self):
        cycles = self.graph_cycles()
        for cycle in cycles:
            find = True
            if len(cycle) == 1:
                find = False
                continue
            for i in range(len(cycle) - 1):
                if self.graph[cycle[i]][cycle[i+1]]['data'].event.name != '':
                    find = False
                    break
            if find == True:
                str = ' '.join(cycle) + ' '
                self.warning('The state machine has an infinite loop: ' + str + '. Add an event!')
                return

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
        self.verify_infinite_loops()

    ###########################################################################
    ### Parse an event.
    ### TODO for the moment we do not manage boolean expression
    ### TODO manage builtins such as "when(event)" or "after(x)"
    ### This algorithm is not good ie ['setSpeed', '(refSpeed)']
    ###########################################################################
    def parse_event(self, event, tokens):
        event.params = []
        N = len(tokens)
        if N == 0: # No event
            event.name = ''
            return
        # Concat all tokens into a single one
        if tokens[N-1][-1] != ')':
            # The last token does not have params
            event.name = tokens[0].lower()
            for t in tokens[1:]:
                event.name += t.capitalize()
        else: # The last token has params
            if N == 1:
                splits = tokens[-1].split('(')
                print(N, splits)
                event.name = splits[0]
                event.params = splits[1][:-1].split(',')
            else:
                event.name = tokens[0].lower()
                for t in tokens[1:-1]:
                    event.name += t.capitalize()
                splits = tokens[N-1].split('(')
                print(N, splits)
                event.name += splits[0].capitalize()
                event.params = splits[1][:-1].split(',')

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
            if self.tokens[i] == '#event':
                N = int(self.tokens[i+1])
                self.parse_event(tr.event, self.tokens[i+2:i+2+N])
                # Events are optional. If not given, we use them as anonymous internal event.
                # Store them in a dictionary: "event => (origin, destination) states" to create
                # the state transition for each event.
                self.lookup_events[tr.event].append((tr.origin, tr.destination))
            elif self.tokens[i] == '#guard':
                tr.guard = self.tokens[i + 1][1:-1].strip() # Remove [ and ]
            elif self.tokens[i] == '#uml_action':
                tr.action = self.tokens[i + 1][1:].strip() # Remove /
            elif self.tokens[i] == '#std_action':
                tr.action = self.tokens[i + 1][6:].strip() # Remove \n--\n

            # Distinguish a transition cycling to its own state from the "on event" on the state
            if as_state and (tr.origin == tr.destination):
                if tr.action == '':
                    tr.action = '// Dummy action\n'
                    tr.action += '#warning "no reaction to event ' + tr.event.name
                    tr.action += ' for internal transition ' + tr.origin + ' -> '
                    tr.action += tr.origin + '"\n'

        # Store parsed information as edge of the graph
        self.add_transition(tr)
        self.tokens = []

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
    def parse_state(self, inst):
        what = inst.data[6:]
        name = inst.children[0].upper()

        # Create first a node if it does not exist. This is the simplest way
        # preventing smashing previously initialized values.
        self.add_state(name)

        # Update state fields
        state = self.graph.nodes[name]['data']
        if what in ['entry', 'entering']:
            state.entering += '        '
            state.entering += inst.children[1].children[0][1:].strip()
            state.entering += ';\n'
        elif what in ['exit', 'leaving']:
            state.leaving += '        '
            state.leaving += inst.children[1].children[0][1:].strip()
            state.leaving += ';\n'
        elif what == 'comment':
            state.comment += inst.children[1].children[0][1:].strip()
        elif what in ['do', 'activity']:
            state.activity += inst.children[1].children[0][1:].strip()
        # 'on event' is not sugar syntax to a real transition: since it disables
        # 'entry' and 'exit' actions but we want create a real graph edege to
        # help us on graph theory traversal algorithm (like finding cycles).
        elif what in ['on', 'event']:
            self.tokens = [ name, '->', name ]
            for i in range(1, len(inst.children)):
                self.tokens.append('#' + str(inst.children[i].data))
                if inst.children[i].data != 'event':
                    self.tokens.append(str(inst.children[i].children[0]))
                else:
                    self.tokens.append(str(len(inst.children[i].children)))
                    for j in inst.children[i].children:
                        self.tokens.append(str(j))
            self.parse_transition(True)
        else:
            self.fatal('Bad syntax describing a state. Unkown token "' + what + '"')

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
    def parse_extra_code(self, token, code):
        if token == '[header]':
            self.extra_code.header += code
            self.extra_code.header += '\n'
        elif token == '[footer]':
            self.extra_code.footer += code
            self.extra_code.footer += '\n'
        elif token == '[param]':
            if self.extra_code.argvs != '':
                self.extra_code.argvs += ', '
            self.extra_code.argvs += code
        elif token == '[init]':
            self.extra_code.init += '        '
            self.extra_code.init += code
            self.extra_code.init += '\n'
        elif token == '[code]':
            if code not in ['public:', 'protected:', 'private:']:
                self.extra_code.functions += '    '
            self.extra_code.functions += code
            self.extra_code.functions += '\n'
        elif token == '[test]':
            self.extra_code.unit_tests += code
            self.extra_code.unit_tests += '\n'
        else:
            self.fatal('Token ' + token + ' not yet managed')

    ###########################################################################
    ### Traverse the Abstract Syntax Tree of the PlantUML file
    ###########################################################################
    def visit_ast(self, inst):
        if inst.data == 'state_diagram':  # FIXME To be removed when creating the AST
            for c in inst.children:
                self.visit_ast(c)
        elif inst.data == 'cpp_code':
            self.parse_extra_code(str(inst.children[0]), inst.children[1].lstrip())
        elif inst.data == 'transition':
            # Note: we have to convert into a list of tokens since parse_state()
            # can call parse_transition() with a generated code and we do not
            # reuse the parser to create a temporary AST, instead we pass list
            # of tokens.
            self.tokens = [str(inst.children[0]), str(inst.children[1]),
                           str(inst.children[2])]
            for i in range(3, len(inst.children)):
                self.tokens.append('#' + str(inst.children[i].data))
                if inst.children[i].data != 'event':
                    self.tokens.append(str(inst.children[i].children[0]))
                else:
                    self.tokens.append(str(len(inst.children[i].children)))
                    for j in inst.children[i].children:
                        self.tokens.append(str(j))
            self.parse_transition(False)
        elif inst.data[0:6] == 'state_':
            self.parse_state(inst)
        elif inst.data in ['comment', 'skin', 'hide']:
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
            self.fatal('Failed loading grammar file ' + grammar_file + ' for parsing plantuml statechart')

    ###########################################################################
    ### Parse plantUML file parser and create a graph structure.
    ###########################################################################
    def parse_plantuml_file(self, umlfile, cpp_or_hpp, classname):
        self.reset()
        self.umlfile = umlfile
        self.name = Path(umlfile).stem
        self.class_name = self.name + classname
        self.enum_name = self.class_name + 'States'
        # Make the plantUMl file read by the parser
        if self.parser == None:
            self.load_plantuml_grammar_file(os.path.join(os.getcwd(), 'statecharts.ebnf'))
        self.fd = open(umlfile, 'r')
        self.ast = self.parser.parse(self.fd.read())
        self.fd.close()
        # Debug: uncomment to see AST
        # print(self.ast.pretty())
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
