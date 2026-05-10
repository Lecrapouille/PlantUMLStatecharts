#!/usr/bin/env python3
###############################################################################
## PlantUML Statecharts translator targeting the in-tree ``statechart`` C++
## library.
##
## Copyright (c) 2022 - 2026 Quentin Quadrat <lecrapouille@gmail.com>
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
###############################################################################
"""
Translator from PlantUML state diagrams to modern C++ using the
``statechart`` library shipped in this project.

For each ``foo.plantuml`` the script writes:
- ``foo.hpp``      : the generated state-machine class.
- ``fooTests.cpp`` : a small GoogleTest suite that smoke-tests the FSM.

Only flat finite state machines are currently supported. Composite
states (PlantUML ``state Foo { ... }``) and orthogonal regions raise an
explicit error.
"""

import os
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import networkx as nx
from lark import Lark


###############################################################################
# Console colours (purely cosmetic).
###############################################################################
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'


###############################################################################
# Small data classes
###############################################################################
class Event:
    """A parsed PlantUML event (``setSpeed`` or ``set speed(x, y)``)."""

    def __init__(self):
        self.name = ''
        self.params = []  # list of parameter names (no type info)

    def parse(self, tokens):
        """Parse the list of tokens belonging to an ``event`` rule.

        Examples of input tokens::

            ['set', 'speed']                        -> name='setSpeed'
            ['setSpeed']                            -> name='setSpeed'
            ['setSpeed', '(x, y)']                  -> name='setSpeed', params=['x','y']
            ['set', 'speed', '(x, y)']              -> name='setSpeed', params=['x','y']
        """
        self.name = ''
        self.params = []
        n = len(tokens)
        if n == 0:
            return
        for i, tok in enumerate(tokens):
            if tok.startswith('('):
                if i != n - 1:
                    raise ValueError(f'Mismatched parenthesis in event tokens: {tokens}')
                inner = tok[1:-1].strip()
                if inner:
                    self.params = [p.strip() for p in inner.split(',') if p.strip()]
            elif i == 0:
                # First word: keep as-is if it is the only event name word, else lowercase.
                if i < n - 1 and not tokens[i + 1].startswith('('):
                    self.name = tok.lower()
                else:
                    self.name = tok
            else:
                self.name += tok.capitalize()

    def cpp_class_name(self):
        """C++ class name derived from the event (``setSpeed`` -> ``EvSetSpeed``)."""
        if not self.name:
            return ''
        return 'Ev' + self.name[0].upper() + self.name[1:]

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, Event) and self.name == other.name

    def __repr__(self):
        return f"Event({self.name!r}, params={self.params})"


class Transition:
    """A graph edge between two states."""

    def __init__(self):
        self.origin = ''
        self.destination = ''
        self.event = Event()
        self.guard = ''
        self.action = ''
        self.arrow = ''
        # True when the transition is the body of a ``state : on event`` line
        # (i.e. an internal transition that must not exit/re-enter the state).
        self.is_internal = False


class State:
    """A graph node in the parsed FSM."""

    def __init__(self, name):
        self.name = name
        self.comment = ''
        self.entering = ''
        self.leaving = ''
        self.activity = ''


class ExtraCode:
    """User-supplied C++ snippets injected into the generated file."""

    def __init__(self):
        self.brief = ''
        self.header = ''
        self.footer = ''
        self.argvs = ''        # constructor argument list (raw, comma-separated)
        self.cons = ''         # constructor initializer list (raw)
        self.init = ''         # constructor body
        self.code = ''         # extra members / methods (raw, indented by user)
        self.test = ''         # extra code for the test mock subclass


###############################################################################
# Parser
###############################################################################
class Parser:
    """Reads a PlantUML file and builds a directed graph (Networkx)."""

    def __init__(self):
        self.lark = None
        self.uml_file = ''
        self.graph = nx.DiGraph()
        self.initial_state = ''      # name of the destination of the [*] -> X edge
        self.has_final_state = False
        self.lookup_events = defaultdict(list)  # event -> list of (origin, dst)
        self.extra = ExtraCode()
        self.warnings = []
        self.class_name = ''
        self.tokens = []  # scratch buffer (legacy AST flattening)

    # ----------------------------------------------------------------- helpers
    def fatal(self, msg):
        print(f'{Colors.FAIL}FATAL: {msg}{Colors.END}', file=sys.stderr)
        sys.exit(2)

    def warning(self, msg):
        self.warnings.append(msg)
        print(f'{Colors.WARN}WARN: {msg}{Colors.END}', file=sys.stderr)

    def add_state(self, name):
        if name and not self.graph.has_node(name):
            self.graph.add_node(name, data=State(name))

    def add_transition(self, tr):
        self.graph.add_edge(tr.origin, tr.destination, data=tr)

    # --------------------------------------------------------------- AST visit
    def visit_ast(self, inst):
        kind = inst.data
        if kind == 'cpp':
            self.parse_extra_code(str(inst.children[0]), inst.children[1].strip())
        elif kind == 'transition':
            self.tokens = [str(inst.children[0]), str(inst.children[1]), str(inst.children[2])]
            for i in range(3, len(inst.children)):
                child = inst.children[i]
                self.tokens.append('#' + str(child.data))
                if child.data != 'event':
                    self.tokens.append(str(child.children[0]))
                else:
                    self.tokens.append(str(len(child.children)))
                    for j in child.children:
                        self.tokens.append(str(j))
            self.parse_transition(as_state=False)
        elif kind.startswith('state_'):
            self.parse_state_action(inst)
        elif kind in ('comment', 'skin', 'hide'):
            return
        elif kind == 'state_block':
            self.fatal(
                'Composite state "state ' + str(inst.children[0]) + ' { ... }" detected. '
                'This translator currently only supports flat (non-hierarchical) FSMs.')
        elif kind == 'ortho_block':
            self.fatal(
                'Orthogonal region (--/||) detected. This translator currently only '
                'supports flat (non-hierarchical) FSMs.')
        else:
            self.fatal(f'Unsupported PlantUML construct: {kind}')

    def parse_transition(self, as_state):
        tr = Transition()
        tr.arrow = self.tokens[1]
        if tr.arrow.endswith('>'):
            tr.origin = self.tokens[0].upper()
            tr.destination = self.tokens[2].upper()
        else:
            tr.origin = self.tokens[2].upper()
            tr.destination = self.tokens[0].upper()
        tr.is_internal = as_state

        if tr.origin == '[*]':
            self.initial_state = tr.destination
        elif tr.destination == '[*]':
            tr.destination = '__FINAL__'
            self.has_final_state = True

        self.add_state(tr.origin)
        self.add_state(tr.destination)

        i = 3
        while i < len(self.tokens):
            tag = self.tokens[i]
            if tag == '#event':
                count = int(self.tokens[i + 1])
                tr.event.parse(self.tokens[i + 2:i + 2 + count])
                self.lookup_events[tr.event].append((tr.origin, tr.destination))
                i += 2 + count
                continue
            if tag == '#guard':
                tr.guard = self.tokens[i + 1][1:-1].strip()
                i += 2
                continue
            if tag == '#uml_action':
                tr.action = self.tokens[i + 1].lstrip('/').strip()
                i += 2
                continue
            if tag == '#std_action':
                tr.action = self.tokens[i + 1][6:].strip()
                i += 2
                continue
            i += 1

        self.add_transition(tr)
        self.tokens = []

    def parse_state_action(self, inst):
        kind = inst.data[6:]  # strip leading 'state_'
        name = inst.children[0].upper()
        self.add_state(name)
        state = self.graph.nodes[name]['data']

        if kind in ('entry', 'entering'):
            state.entering += inst.children[1].children[0].lstrip('/').strip()
            if not state.entering.endswith(';'):
                state.entering += ';'
            state.entering += '\n'
        elif kind in ('exit', 'leaving'):
            state.leaving += inst.children[1].children[0].lstrip('/').strip()
            if not state.leaving.endswith(';'):
                state.leaving += ';'
            state.leaving += '\n'
        elif kind == 'comment':
            if len(inst.children) > 1:
                state.comment = inst.children[1].children[0].lstrip('/').strip()
        elif kind in ('do', 'activity'):
            state.activity += inst.children[1].children[0].lstrip('/').strip()
            if not state.activity.endswith(';'):
                state.activity += ';'
            state.activity += '\n'
        elif kind in ('on', 'event'):
            self.tokens = [name, '->', name]
            for child in inst.children[1:]:
                self.tokens.append('#' + str(child.data))
                if child.data != 'event':
                    self.tokens.append(str(child.children[0]))
                else:
                    self.tokens.append(str(len(child.children)))
                    for j in child.children:
                        self.tokens.append(str(j))
            self.parse_transition(as_state=True)
        else:
            self.fatal(f'Unsupported state action: {inst.data}')

    def parse_extra_code(self, token, code):
        token = token.strip()
        if token == '[brief]':
            if self.extra.brief:
                self.extra.brief += '\n//! '
            self.extra.brief += code
        elif token == '[header]':
            self.extra.header += code + '\n'
        elif token == '[footer]':
            self.extra.footer += code + '\n'
        elif token == '[param]':
            self.extra.argvs += (', ' if self.extra.argvs else '') + code
        elif token == '[cons]':
            self.extra.cons += ',\n          ' + code
        elif token == '[init]':
            self.extra.init += '        ' + code + '\n'
        elif token == '[code]':
            self.extra.code += code + '\n'
        elif token == '[test]':
            self.extra.test += code + '\n'
        else:
            self.fatal(f'Unknown directive: {token}')

    # ------------------------------------------------------------------ public
    def parse_file(self, uml_path):
        grammar_file = Path(__file__).resolve().parent / 'statecharts.ebnf'
        if not grammar_file.is_file():
            self.fatal(f'Grammar file not found: {grammar_file}')
        with open(grammar_file, 'r', encoding='utf-8') as fh:
            self.lark = Lark(fh.read())

        self.uml_file = str(uml_path)
        if not Path(uml_path).is_file():
            self.fatal(f'PlantUML file not found: {uml_path}')
        with open(uml_path, 'r', encoding='utf-8') as fh:
            ast = self.lark.parse(fh.read())

        for child in ast.children:
            self.visit_ast(child)

        self._sanity_checks()

    def _sanity_checks(self):
        if not self.initial_state:
            self.warning(f'No initial state ([*] -> X) found in {self.uml_file}; '
                         'using the first declared state.')


###############################################################################
# Generator
###############################################################################
def cpp_state_id(name):
    """Map a raw PlantUML state name to a safe C++ identifier suffix."""
    if name == '[*]':
        return 'Start'
    if name == '__FINAL__':
        return 'Final'
    return re.sub(r'[^A-Za-z0-9_]', '_', name)


def sanitize_identifier(name):
    """Map an arbitrary string (e.g. a file stem) to a valid C++ identifier.

    - Replaces invalid chars with ``_``.
    - Prepends ``Sm`` (state machine) when the result would start with a
      digit, which is illegal in C++.
    """
    sanitized = re.sub(r'[^A-Za-z0-9_]', '_', name)
    if sanitized and sanitized[0].isdigit():
        sanitized = 'Sm' + sanitized
    return sanitized


class Generator:
    """Emits C++ source files from a parsed FSM."""

    HEADER_INCLUDES = (
        '#include <statechart/Statechart.hpp>\n'
        '#include <statechart/State.hpp>\n'
        '#include <statechart/PseudoState.hpp>\n'
        '#include <statechart/FinalState.hpp>\n'
        '#include <statechart/Transition.hpp>\n'
        '#include <statechart/InternalTransition.hpp>\n'
        '#include <statechart/Event.hpp>\n'
        '#include <statechart/Metadata.hpp>\n'
        '#include <statechart/Parameter.hpp>\n'
        '\n'
        '#include <memory>\n'
        '#include <string>\n'
        '#include <unordered_set>\n'
        '\n'
        '// Compatibility shim with the legacy code-base: silence the LOGD\n'
        '// macro when it is referenced from user-supplied [code] blocks.\n'
        '#ifndef LOGD\n'
        '#  define LOGD(...) ((void)0)\n'
        '#endif\n'
    )

    def __init__(self, parser, output_dir):
        self.p = parser
        self.out_dir = Path(output_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        # collected event-parameter -> upper-cased type for member declaration
        self.event_param_types = {}
        for ev in self.p.lookup_events.keys():
            for pn in ev.params:
                self.event_param_types.setdefault(pn, pn.upper())

    # ----------------------------------------------------------------- helpers
    @staticmethod
    def _state_member(name):
        return 'm_state_' + cpp_state_id(name)

    @staticmethod
    def _start_member():
        return 'm_state__start'

    def _all_states(self):
        """Iterate over states to be modelled as ``statechart::State``.

        Excludes ``[*]`` (modelled as a PseudoState) and ``__FINAL__``
        (modelled as a FinalState if present).
        """
        for name in self.p.graph.nodes:
            if name in ('[*]', '__FINAL__'):
                continue
            yield name

    def _has_final(self):
        return '__FINAL__' in self.p.graph.nodes

    # ---------------------------------------------------------------- header
    def emit_header(self, hpp_path):
        cls = self.p.class_name
        guard = cls.upper() + '_HPP'
        with open(hpp_path, 'w', encoding='utf-8') as fh:
            fh.write(f'// Generated on {date.today():%B %d, %Y} from {Path(self.p.uml_file).name}\n')
            fh.write('// Do not edit by hand: regenerate with tools/translator/statecharts.py\n\n')
            fh.write(f'#ifndef {guard}\n#define {guard}\n\n')
            fh.write(self.HEADER_INCLUDES)
            fh.write('\n')
            if self.p.warnings:
                for w in self.p.warnings:
                    fh.write(f'// WARNING: {w}\n')
                fh.write('\n')
            if self.p.extra.header.strip():
                fh.write('// User [header]:\n')
                fh.write(self.p.extra.header)
                fh.write('\n')

            self._emit_event_classes(fh)
            self._emit_fsm_class(fh)

            if self.p.extra.footer.strip():
                fh.write('\n// User [footer]:\n')
                fh.write(self.p.extra.footer)

            fh.write(f'\n#endif // {guard}\n')

    # ---------------------------------------------------------- event classes
    def _emit_event_classes(self, fh):
        events = [ev for ev in self.p.lookup_events.keys() if ev.name]
        if not events:
            return
        fh.write('// ===== Generated event classes =====\n')
        for ev in events:
            cls = ev.cpp_class_name()
            fh.write(f'class {cls} : public statechart::Event {{\n')
            fh.write(f'public:\n    {cls}() : statechart::Event("{ev.name}") {{}}\n')
            fh.write('};\n\n')

    # ------------------------------------------------------------- FSM class
    def _emit_fsm_class(self, fh):
        cls = self.p.class_name
        if self.p.extra.brief.strip():
            fh.write(f'/**\n * \\brief {self.p.extra.brief}\n */\n')
        fh.write(f'class {cls} {{\n')

        # --- private members FIRST (member declaration order matters for
        # initialiser lists; user [code] members may be referenced by [cons]
        # which runs before m_chart construction) -----------------------------
        fh.write('protected:\n')
        # event params (stashed before dispatch). Declared first so user
        # [code] can reference them, and so they are initialised before
        # m_chart in the implicit member-initialisation order.
        for pname, ptype in sorted(self.event_param_types.items()):
            fh.write(f'    {ptype} {pname}{{}};\n')
        # user [code] members (kept in protected to allow Mock subclass access)
        if self.p.extra.code.strip():
            fh.write('\n    // ----- User [code] -----\n')
            for line in self.p.extra.code.splitlines():
                if line.startswith(('public:', 'protected:', 'private:')):
                    fh.write(line + '\n')
                else:
                    fh.write('    ' + line + '\n')
        # state pointers
        fh.write('\nprotected:\n')
        fh.write(f'    statechart::PseudoState* {self._start_member()} = nullptr;\n')
        for name in self._all_states():
            fh.write(f'    statechart::State* {self._state_member(name)} = nullptr;\n')
        if self._has_final():
            fh.write(f'    statechart::FinalState* {self._state_member("__FINAL__")} = nullptr;\n')
        # chart/data/param come last to be initialised last
        fh.write('    std::unique_ptr<statechart::Statechart> m_chart;\n')
        fh.write('    statechart::Metadata m_data;\n')
        fh.write('    statechart::Parameter m_param;\n')

        # --- public section --------------------------------------------------
        fh.write('\npublic:\n')
        self._emit_constructor(fh)
        self._emit_destructor(fh)
        self._emit_lifecycle(fh)
        self._emit_query(fh)
        self._emit_event_methods(fh)
        self._emit_counters(fh)

        fh.write('};\n')

    # --------------------------------------------------------------- ctor/dtor
    def _emit_constructor(self, fh):
        cls = self.p.class_name
        fh.write(f'    {cls}({self.p.extra.argvs})\n')
        # User [cons] entries refer to members declared early (event params,
        # user [code] members) and must come before m_chart in the
        # initialiser list to match the declaration order and silence GCC's
        # -Wreorder warning.
        if self.p.extra.cons.strip():
            # ``self.p.extra.cons`` already starts with ``,\n          ``;
            # strip the leading comma here so we can place the entries first.
            cons = self.p.extra.cons.lstrip(',').strip()
            fh.write(f'      : {cons},\n')
            fh.write(f'        m_chart(std::make_unique<statechart::Statechart>("{cls}", 2, false))')
        else:
            fh.write(f'      : m_chart(std::make_unique<statechart::Statechart>("{cls}", 2, false))')
        fh.write('\n    {\n')

        # 1. create states
        fh.write(f'        {self._start_member()} = m_chart->create<statechart::PseudoState>(\n')
        fh.write(f'            "__start", m_chart.get(), statechart::PseudoStateType::Start);\n')
        for name in self._all_states():
            self._emit_state_create(fh, name)
        if self._has_final():
            fh.write(f'        {self._state_member("__FINAL__")} = m_chart->create<statechart::FinalState>(\n')
            fh.write(f'            "__final", m_chart.get());\n')

        # 2. transitions
        fh.write('\n')
        # initial pseudo-state -> initial state
        if self.p.initial_state:
            fh.write(f'        m_chart->createTransition({self._start_member()}, {self._state_member(self.p.initial_state)});\n')
        # all other transitions
        for src, dst, data in self.p.graph.edges(data='data'):
            if src == '[*]':
                continue
            self._emit_transition(fh, src, dst, data)

        # 3. user [init]
        if self.p.extra.init.strip():
            fh.write('\n        // User [init]:\n')
            fh.write(self.p.extra.init)

        fh.write('    }\n\n')

    def _emit_destructor(self, fh):
        fh.write(f'    ~{self.p.class_name}() {{ if (m_chart) m_chart->shutdown(); }}\n\n')

    # ------------------------------------------------------------- state ctor
    def _emit_state_create(self, fh, name):
        st = self.p.graph.nodes[name]['data']
        member = self._state_member(name)
        fh.write(f'        {member} = m_chart->create<statechart::State>(\n')
        fh.write(f'            "{name}", m_chart.get()')
        if st.entering or st.activity or st.leaving:
            fh.write(',\n            ')
            fh.write(self._lambda_action_or_empty(self._compose_actions(st.entering, f'++m_count_entering_{cpp_state_id(name)};')))
            fh.write(',\n            ')
            fh.write(self._lambda_action_or_empty(st.activity))
            fh.write(',\n            ')
            fh.write(self._lambda_action_or_empty(self._compose_actions(st.leaving, f'++m_count_leaving_{cpp_state_id(name)};')))
        fh.write(');\n')

    @staticmethod
    def _compose_actions(*snippets):
        return '\n            '.join(s.strip() for s in snippets if s and s.strip())

    @staticmethod
    def _lambda_action_or_empty(body):
        if not body or not body.strip():
            return 'statechart::Action{}'
        return ('statechart::Action{[this](statechart::Metadata&, statechart::Parameter&) {\n'
                '                ' + body.replace('\n', '\n                ') + '\n'
                '            }}')

    # ------------------------------------------------------- transition emit
    def _emit_transition(self, fh, src, dst, tr):
        if tr.is_internal:
            self._emit_internal_transition(fh, src, tr)
            return
        edge_id = f'{cpp_state_id(src)}_{cpp_state_id(dst)}'
        src_mem = self._state_member(src)
        dst_mem = self._state_member(dst)
        fh.write(f'        m_chart->createTransition({src_mem}, {dst_mem}')
        if tr.event.name:
            ev_cls = tr.event.cpp_class_name()
            fh.write(f',\n            m_chart->createEvent<{ev_cls}>()')
        if tr.guard:
            fh.write(',\n            ')
            fh.write(self._lambda_guard(tr.guard, edge_id))
        if tr.action:
            fh.write(',\n            ')
            fh.write(self._lambda_action(tr.action, edge_id))
        fh.write(');\n')

    def _emit_internal_transition(self, fh, src, tr):
        if not tr.event.name:
            self.p.warning(f'Skipping internal transition without event on state {src}.')
            return
        edge_id = f'{cpp_state_id(src)}_{cpp_state_id(src)}'
        src_mem = self._state_member(src)
        ev_cls = tr.event.cpp_class_name()
        fh.write(f'        m_chart->createInternalTransition({src_mem},\n')
        fh.write(f'            m_chart->createEvent<{ev_cls}>()')
        if tr.guard:
            fh.write(',\n            ')
            fh.write(self._lambda_guard(tr.guard, edge_id))
        else:
            # InternalTransition requires either (event, action) or (event, guard, action).
            pass
        fh.write(',\n            ')
        body = tr.action if tr.action else '/* internal transition has no action */'
        fh.write(self._lambda_action(body, edge_id))
        fh.write(');\n')

    def _lambda_guard(self, expr, edge_id):
        # Wrapped in ``statechart::Guard{...}`` to disambiguate with the
        # ``Action`` overload of ``Transition`` (a bool-returning lambda is
        # implicitly convertible to ``std::function<void(...)>`` as well).
        return ('statechart::Guard{[this](statechart::Metadata&, statechart::Parameter&) -> bool {\n'
                f'                ++m_count_guard_{edge_id};\n'
                f'                return ({expr});\n'
                '            }}')

    def _lambda_action(self, body, edge_id):
        body = body.strip()
        if body and not body.endswith(';'):
            body += ';'
        return ('statechart::Action{[this](statechart::Metadata&, statechart::Parameter&) {\n'
                f'                ++m_count_action_{edge_id};\n'
                f'                {body}\n'
                '            }}')

    # ------------------------------------------------------------ lifecycle
    def _emit_lifecycle(self, fh):
        fh.write('    bool enter() { return m_chart->start(m_data, m_param); }\n')
        fh.write('    void leave() { m_chart->shutdown(); }\n\n')

    # --------------------------------------------------------------- query
    def _emit_query(self, fh):
        fh.write('    bool isInState(const std::string& p_name) const {\n')
        fh.write('        return m_data.isActive(p_name);\n')
        fh.write('    }\n\n')
        fh.write('    /// Returns the name of the deepest non-pseudo, non-root active state.\n')
        fh.write('    std::string state() const {\n')
        fh.write('        for (auto* s : m_data.getActiveStates()) {\n')
        fh.write('            if (s == nullptr) continue;\n')
        fh.write('            if (dynamic_cast<statechart::PseudoState*>(s)) continue;\n')
        fh.write('            // Skip the root Statechart (also a State) which is named\n')
        fh.write('            // after this generated FSM and is not interesting here.\n')
        fh.write('            if (dynamic_cast<statechart::Statechart*>(s)) continue;\n')
        fh.write('            return s->name();\n')
        fh.write('        }\n')
        fh.write('        return std::string{};\n')
        fh.write('    }\n\n')

    # ---------------------------------------------------------- event methods
    def _emit_event_methods(self, fh):
        events = [ev for ev in self.p.lookup_events.keys() if ev.name]
        for ev in events:
            cls = ev.cpp_class_name()
            params = ', '.join(f'{self.event_param_types[p]} const& p_{p}' for p in ev.params)
            fh.write(f'    void {ev.name}({params}) {{\n')
            for p in ev.params:
                fh.write(f'        {p} = p_{p};\n')
            fh.write(f'        {cls} ev;\n')
            fh.write('        m_chart->dispatch(m_data, &ev, m_param);\n')
            fh.write('    }\n\n')

    # --------------------------------------------------------------- counters
    def _emit_counters(self, fh):
        fh.write('    // ----- Test instrumentation counters -----\n')
        for name in self._all_states():
            sid = cpp_state_id(name)
            fh.write(f'    int m_count_entering_{sid} = 0;\n')
            fh.write(f'    int m_count_leaving_{sid} = 0;\n')
        for src, dst, data in self.p.graph.edges(data='data'):
            if src == '[*]':
                continue
            edge_id = f'{cpp_state_id(src)}_{cpp_state_id(dst)}'
            fh.write(f'    int m_count_guard_{edge_id} = 0;\n')
            fh.write(f'    int m_count_action_{edge_id} = 0;\n')

    # ----------------------------------------------------------- test driver
    def emit_tests(self, test_path, hpp_name):
        cls = self.p.class_name
        with open(test_path, 'w', encoding='utf-8') as fh:
            fh.write(f'// Generated test for {cls} on {date.today():%B %d, %Y}.\n')
            fh.write('// Do not edit by hand: regenerate with tools/translator/statecharts.py\n\n')
            fh.write(f'#include "{hpp_name}"\n')
            fh.write('#include <gtest/gtest.h>\n\n')

            # Test subclass to host an optional default-construct override. The
            # legacy [test] directive (which referenced the legacy class name
            # with a postfix) is preserved here as a comment for reference but
            # not compiled, since the integrated build does not honour the
            # legacy ``--postfix`` convention.
            if self.p.extra.test.strip():
                fh.write('// Legacy [test] block from PlantUML source (kept for reference):\n')
                for line in self.p.extra.test.splitlines():
                    fh.write(f'//     {line}\n')
                fh.write('\n')

            fh.write(f'class Test{cls} : public {cls} {{\n')
            fh.write('public:\n')
            # Default-construct the FSM with empty values for user [param]s.
            argvs = self.p.extra.argvs.strip()
            if argvs:
                # Map "Type name, Type2 name2" to "{}, {}" placeholders.
                count = argvs.count(',') + 1
                placeholders = ', '.join(['{}'] * count)
                fh.write(f'    Test{cls}() : {cls}({placeholders}) {{}}\n')
            else:
                fh.write(f'    Test{cls}() = default;\n')
            fh.write('};\n\n')

            self._emit_initial_state_test(fh, cls)
            self._emit_smoke_test(fh, cls)

    def _emit_initial_state_test(self, fh, cls):
        # Many FSMs immediately consume completion transitions (no event)
        # at start time, so we cannot universally assert ``state() == initial``.
        # We assert instead that the FSM resolved to **some** non-empty state.
        fh.write(f'TEST({cls}Tests, EntersWithoutThrowing) {{\n')
        fh.write(f'    Test{cls} fsm;\n')
        fh.write('    fsm.enter();\n')
        fh.write('    EXPECT_FALSE(fsm.state().empty());\n')
        fh.write('    fsm.leave();\n')
        fh.write('}\n\n')

    def _emit_smoke_test(self, fh, cls):
        fh.write(f'TEST({cls}Tests, SmokeFireAllEvents) {{\n')
        fh.write(f'    Test{cls} fsm;\n')
        fh.write('    fsm.enter();\n')
        for ev in self.p.lookup_events.keys():
            if not ev.name:
                continue
            args = ', '.join(self._default_arg(p) for p in ev.params)
            fh.write(f'    fsm.{ev.name}({args});\n')
        fh.write('    fsm.leave();\n')
        fh.write('    SUCCEED();\n')
        fh.write('}\n')

    @staticmethod
    def _default_arg(_p_name):
        # All event params are typed by their upper-cased name in the
        # generator; default-construct via ``{}``.
        return '{}'


###############################################################################
# CLI
###############################################################################
def usage():
    print('Usage: statecharts.py <plantuml-file> hpp [postfix] [--outdir DIR]')
    print('  Generates <ClassName>.hpp + <ClassName>Tests.cpp in --outdir')
    print('  (current directory by default).')
    sys.exit(2)


def main():
    args = sys.argv[1:]
    if not args:
        usage()

    outdir = '.'
    if '--outdir' in args:
        idx = args.index('--outdir')
        outdir = args[idx + 1]
        del args[idx:idx + 2]

    if len(args) < 2:
        usage()

    uml_file = args[0]
    lang = args[1]
    if lang not in ('hpp', 'cpp'):
        print('Only "hpp" output is supported by this generator.', file=sys.stderr)
        sys.exit(2)
    postfix = args[2] if len(args) >= 3 else ''

    parser = Parser()
    raw_name = Path(uml_file).stem + postfix
    parser.class_name = sanitize_identifier(raw_name)
    parser.parse_file(uml_file)

    gen = Generator(parser, outdir)
    # Output files keep the sanitized class name so any downstream build
    # system (CMake, makefile, ...) can find them via simple glob patterns.
    hpp_name = parser.class_name + '.hpp'
    test_name = parser.class_name + 'Tests.cpp'
    gen.emit_header(Path(outdir) / hpp_name)
    gen.emit_tests(Path(outdir) / test_name, hpp_name)
    print(f'{Colors.OKGREEN}OK{Colors.END}: wrote {hpp_name} and {test_name} in {outdir}')


if __name__ == '__main__':
    main()
