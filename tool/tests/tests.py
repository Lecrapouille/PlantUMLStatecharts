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

def run_instruction(inst):
    if inst.data == 'state_diagram':
        for c in inst.children:
            run_instruction(c)
    elif inst.data == 'comment':
        pass
    elif inst.data == 'cpp_code':
        print("C++ code:", str(inst.children[0]))
    elif inst.data == 'transition':
        tr = Transition()
        if inst.children[1][-1] == '>':
            tr.origin, tr.destination = inst.children[0].upper(), inst.children[2].upper()
        else:
            tr.origin, tr.destination = inst.children[2].upper(), inst.children[0].upper()
        for i in range(3, len(inst.children)):
            if inst.children[i].data == 'event':
                tr.event = ' '.join(inst.children[i].children[:])
            elif inst.children[i].data == 'guard':
                tr.guard = inst.children[i].children[0]
            elif inst.children[i].data == 'action':
                tr.action = inst.children[i].children[0]
        print(tr)
            
    else:
        print("FIXME not yet managed:", inst.data)
        pass

def main():
    f = open('grammar.ebnf')
    parser = Lark(f.read())
    f = open(sys.argv[1])
    ast = parser.parse(f.read())
    print("AST:", ast.pretty())
    for inst in ast.children:
        run_instruction(inst)

if __name__ == '__main__':
    main()
