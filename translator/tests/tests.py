#!/usr/bin/env python3

from lark import Lark, Transformer
import os, sys

def check(exp):
    if not exp:
        raise Exception()

def check_AST(root):
    check(root.data == 'state_diagram')
    check(len(root.children) == 21)
    c = 0

    # ' ceci est un commentaire
    check(root.children[c].data == 'comment')
    c += 1

    # '[header] ceci est un header 1
    check(root.children[c].data == 'cpp_code')
    check(len(root.children[c].children) == 2)
    check(root.children[c].children[0] == '[header]')
    check(root.children[c].children[1].strip() == 'ceci est un header 1')
    c += 1

    # '[header] ceci est un header 2
    check(root.children[c].data == 'cpp_code')
    check(len(root.children[c].children) == 2)
    check(root.children[c].children[0] == '[header]')
    check(root.children[c].children[1].strip() == 'ceci est un header 2')
    c += 1

    # '[footer] ceci est un footer 1
    check(root.children[c].data == 'cpp_code')
    check(len(root.children[c].children) == 2)
    check(root.children[c].children[0] == '[footer]')
    check(root.children[c].children[1].strip() == 'ceci est un footer 1')
    c += 1

    # '[footer] ceci est un footer 2
    check(root.children[c].data == 'cpp_code')
    check(len(root.children[c].children) == 2)
    check(root.children[c].children[0] == '[footer]')
    check(root.children[c].children[1].strip() == 'ceci est un footer 2')
    c += 1

    # '[init] a = 0;
    check(root.children[c].data == 'cpp_code')
    check(len(root.children[c].children) == 2)
    check(root.children[c].children[0] == '[init]')
    check(root.children[c].children[1].strip() == 'a = 0;')
    c += 1

    # '[init] b = "ff";
    check(root.children[c].data == 'cpp_code')
    check(len(root.children[c].children) == 2)
    check(root.children[c].children[0] == '[init]')
    check(root.children[c].children[1].strip() == 'b = "ff";')
    c += 1

    # '[code] int foo();
    check(root.children[c].data == 'cpp_code')
    check(len(root.children[c].children) == 2)
    check(root.children[c].children[0] == '[code]')
    check(root.children[c].children[1].strip() == 'int foo();')
    c += 1

    # '[code] virtual std::string foo(std::foo<Bar> const& arg[]) = 0;
    check(root.children[c].data == 'cpp_code')
    check(len(root.children[c].children) == 2)
    check(root.children[c].children[0] == '[code]')
    check(root.children[c].children[1].strip() == 'virtual std::string foo(std::foo<Bar> const& arg[]) = 0;')
    c += 1

    # [*] --> State1
    check(root.children[c].data == 'transition')
    check(len(root.children[c].children) == 3)
    check(root.children[c].children[0] == '[*]')
    check(root.children[c].children[1] == '-->')
    check(root.children[c].children[2] == 'State1')
    c += 1

    # State1 --> State2
    check(root.children[c].data == 'transition')
    check(len(root.children[c].children) == 3)
    check(root.children[c].children[0] == 'State1')
    check(root.children[c].children[1] == '-->')
    check(root.children[c].children[2] == 'State2')
    c += 1

    # State2 -> State3 : / action = 1/3
    check(root.children[c].data == 'transition')
    check(len(root.children[c].children) == 4)
    check(root.children[c].children[0] == 'State2')
    check(root.children[c].children[1] == '->')
    check(root.children[c].children[2] == 'State3')
    check(root.children[c].children[3].data == 'uml_action')
    check(len(root.children[c].children[3].children) == 1)
    check(root.children[c].children[3].children[0] == '/ action = 1/3')
    c += 1

    # State3 <- State4 : [a[0] + b[] + c(3)]
    check(root.children[c].data == 'transition')
    check(len(root.children[c].children) == 4)
    check(root.children[c].children[0] == 'State3')
    check(root.children[c].children[1] == '<-')
    check(root.children[c].children[2] == 'State4')
    check(root.children[c].children[3].data == 'guard')
    check(len(root.children[c].children[3].children) == 1)
    check(root.children[c].children[3].children[0] == '[a[0] + b[] + c(3)]')
    c += 1

    # State4 <-- State5 : [a[0] + b[] + c(3)] / action = 1/3
    check(root.children[c].data == 'transition')
    check(len(root.children[c].children) == 5)
    check(root.children[c].children[0] == 'State4')
    check(root.children[c].children[1] == '<--')
    check(root.children[c].children[2] == 'State5')
    check(root.children[c].children[3].data == 'guard')
    check(len(root.children[c].children[3].children) == 1)
    check(root.children[c].children[3].children[0] == '[a[0] + b[] + c(3)]')
    check(root.children[c].children[4].data == 'uml_action')
    check(len(root.children[c].children[4].children) == 1)
    check(root.children[c].children[4].children[0] == '/ action = 1/3')
    c += 1

    # State5 --> State6 : setpoint(x, y)
    check(root.children[c].data == 'transition')
    check(len(root.children[c].children) == 4)
    check(root.children[c].children[0] == 'State5')
    check(root.children[c].children[1] == '-->')
    check(root.children[c].children[2] == 'State6')
    check(root.children[c].children[3].data == 'event')
    check(len(root.children[c].children[3].children) == 2)
    check(root.children[c].children[3].children[0] == 'setpoint')
    check(root.children[c].children[3].children[1] == '(x, y)')
    c += 1

    # State6 --> State7 : foo bar()
    check(root.children[c].data == 'transition')
    check(len(root.children[c].children) == 4)
    check(root.children[c].children[0] == 'State6')
    check(root.children[c].children[1] == '-->')
    check(root.children[c].children[2] == 'State7')
    check(root.children[c].children[3].data == 'event')
    check(len(root.children[c].children[3].children) == 3)
    check(root.children[c].children[3].children[0] == 'foo')
    check(root.children[c].children[3].children[1] == 'bar')
    check(root.children[c].children[3].children[2] == '()')
    c += 1

    # State8 <- State7 : foo bar / foo(a, 2[]) + "bar"; gg
    check(root.children[c].data == 'transition')
    check(len(root.children[c].children) == 5)
    check(root.children[c].children[0] == 'State8')
    check(root.children[c].children[1] == '<-')
    check(root.children[c].children[2] == 'State7')
    check(root.children[c].children[3].data == 'event')
    check(len(root.children[c].children[3].children) == 2)
    check(root.children[c].children[3].children[0] == 'foo')
    check(root.children[c].children[3].children[1] == 'bar')
    check(root.children[c].children[4].data == 'uml_action')
    check(len(root.children[c].children[4].children) == 1)
    check(root.children[c].children[4].children[0] == '/ foo(a, 2[]) + "bar"; gg')
    c += 1

    # State9 <- State8 : foo bar [a[0] + b[] + c(3)]
    check(root.children[c].data == 'transition')
    check(len(root.children[c].children) == 5)
    check(root.children[c].children[0] == 'State9')
    check(root.children[c].children[1] == '<-')
    check(root.children[c].children[2] == 'State8')
    check(root.children[c].children[3].data == 'event')
    check(len(root.children[c].children[3].children) == 2)
    check(root.children[c].children[3].children[0] == 'foo')
    check(root.children[c].children[3].children[1] == 'bar')
    check(root.children[c].children[4].data == 'guard')
    check(len(root.children[c].children[4].children) == 1)
    check(root.children[c].children[4].children[0] == '[a[0] + b[] + c(3)]')
    c += 1

    # State10 --> State9 : foo bar [a[0] + b[] + c(3)] / foo(a, a[2] / 2) + "bar"; gg
    # FIXME broken grammar:
    # FIXME guard shall be: [a[0] + b[] + c(3)]
    # FIXME action shall be: / foo(a, a[2] / 2) + "bar"; gg
    check(root.children[c].data == 'transition')
    check(len(root.children[c].children) == 6)
    check(root.children[c].children[0] == 'State10')
    check(root.children[c].children[1] == '-->')
    check(root.children[c].children[2] == 'State9')
    check(root.children[c].children[3].data == 'event')
    check(len(root.children[c].children[3].children) == 2)
    check(root.children[c].children[3].children[0] == 'foo')
    check(root.children[c].children[3].children[1] == 'bar')
    check(root.children[c].children[4].data == 'guard')
    check(len(root.children[c].children[4].children) == 1)
    check(root.children[c].children[4].children[0] == '[a[0] + b[] + c(3)] / foo(a, a[2]')
    check(root.children[c].children[5].data == 'uml_action')
    check(len(root.children[c].children[5].children) == 1)
    check(root.children[c].children[5].children[0] == '/ 2) + "bar"; gg')
    c += 1

    # state State11 {
    #   [*] -> ON
    #   ON -> OFF : off
    #   OFF -> ON : on
    # }
    check(root.children[c].data == 'state_block')
    check(len(root.children[c].children) == 2)
    check(root.children[c].children[0] == 'State11')
    check(root.children[c].children[1].data == 'state_diagram')
    check(len(root.children[c].children[1].children) == 3)

    c0 = root.children[c].children[1].children[0]
    check(c0.data == 'transition')
    check(len(c0.children) == 3)
    check(c0.children[0] == '[*]')
    check(c0.children[1] == '->')
    check(c0.children[2] == 'ON')

    c1 = root.children[c].children[1].children[1]
    check(c1.data == 'transition')
    check(len(c1.children) == 4)
    check(c1.children[0] == 'ON')
    check(c1.children[1] == '->')
    check(c1.children[2] == 'OFF')
    check(len(c1.children[3].children) == 1)
    check(c1.children[3].data == 'event')
    check(len(c1.children[3].children) == 1)
    check(c1.children[3].children[0] == 'off')

    c2 = root.children[c].children[1].children[2]
    check(c2.data == 'transition')
    check(len(c2.children) == 4)
    check(c2.children[0] == 'OFF')
    check(c2.children[1] == '->')
    check(c2.children[2] == 'ON')
    check(len(c2.children[3].children) == 1)
    check(c2.children[3].data == 'event')
    check(len(c2.children[3].children) == 1)
    check(c2.children[3].children[0] == 'on')
    c += 1


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
