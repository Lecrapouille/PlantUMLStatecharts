#!/usr/bin/env python3

from lark import Lark, Transformer
import os, sys

class Transition(object):
    def __init__(self):
        self.origin = ''
        self.destination = ''
        self.event = ''
        self.guard = ''
        self.action = ''
    def __str__(self):
        return "Tr " + self.origin + ' ==> ' + self.destination + ' : ' + self.event + ' [ ' + self.guard + ' ] ' + ' / ' + self.action

def check(exp):
    if not exp:
        raise Exception()

def check_AST(root):
    check(root.data == 'state_diagram')
    check(len(root.children) == 3)

    # State1 --> State2 : eee [ a[0] + b] / action = 1/3
    c0 = root.children[0]
    check(c0.data == 'transition')
    check(len(c0.children) == 6)
    check(c0.children[0] == 'State1')
    check(c0.children[1] == '-->')
    check(c0.children[2] == 'State2')

    c03 = c0.children[3]
    check(len(c03.children) == 1)
    check(c03.data == 'event')
    check(len(c03.children) == 1)
    check(c03.children[0] == 'eee')

    c04 = c0.children[4]
    check(len(c04.children) == 1)
    check(c04.data == 'guard')
    check(len(c04.children) == 1)
    check(c04.children[0] == '[ a[0] + b]')

    c05 = c0.children[5]
    check(len(c05.children) == 1)
    check(c05.data == 'uml_action')
    check(len(c05.children) == 1)
    check(c05.children[0] == '/ action = 1/3')

    # State2 <-- State3
    c1 = root.children[1]
    check(c1.data == 'transition')
    check(len(c1.children) == 3)
    check(c1.children[0] == 'State2')
    check(c1.children[1] == '<--')
    check(c1.children[2] == 'State3')

    # state State4 {
    #   [*] -> ON
    #   ON -> OFF : off
    #   OFF -> ON : on
    # }
    c2 = root.children[2]
    check(c2.data == 'state_block')
    check(len(c2.children) == 2)
    check(c2.children[0] == 'State4')
    check(c2.children[1].data == 'state_diagram')
    
    c21 = c2.children[1]
    check(len(c21.children) == 3)

    c210 = c21.children[0]
    check(c210.data == 'transition')
    check(len(c210.children) == 3)
    check(c210.children[0] == '[*]')
    check(c210.children[1] == '->')
    check(c210.children[2] == 'ON')

    c211 = c21.children[1]
    check(c211.data == 'transition')
    check(len(c211.children) == 4)
    check(c211.children[0] == 'ON')
    check(c211.children[1] == '->')
    check(c211.children[2] == 'OFF')

    c2113 = c211.children[3]
    check(len(c2113.children) == 1)
    check(c2113.data == 'event')
    check(len(c2113.children) == 1)
    check(c2113.children[0] == 'off')

    c212 = c21.children[2]
    check(c212.data == 'transition')
    check(len(c212.children) == 4)
    check(c212.children[0] == 'OFF')
    check(c212.children[1] == '->')
    check(c212.children[2] == 'ON')

    c2123 = c212.children[3]
    check(len(c2123.children) == 1)
    check(c2123.data == 'event')
    check(len(c2123.children) == 1)
    check(c2123.children[0] == 'on')


def main():
    f = open('../statecharts.ebnf')
    parser = Lark(f.read())
    f = open('grammar.plantuml')
    ast = parser.parse(f.read())
    print("AST:", ast.pretty())
    check(len(ast.children) == 1)
    check_AST(ast.children[0])

if __name__ == '__main__':
    main()
