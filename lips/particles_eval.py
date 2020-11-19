#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Giuseppe

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys
import re
import ast
import mpmath
import operator as op

from lips.fields import GaussianRational, ModP, PAdic

operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
             ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
             ast.USub: op.neg}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #


pA2 = re.compile(r'(?:\u27e8)(\d+)(?:\|)(\d+)(?:\u27e9)')
pA2bis = re.compile(r'(?:(?:\u27e8)(\d)(\d)(?:\u27e9))')
pS2 = re.compile(r'(?:\[)(\d+)(?:\|)(\d+)(?:\])')
pS2bis = re.compile(r'(?:\[)(\d)(\d)(?:\])')
pSijk = re.compile(r'(?:s|S)(?:_){0,1}(\d+)')
pOijk = re.compile(r'(?:Ω_)(\d+)')
pPijk = re.compile(r'(?:Π_)(\d+)')
pDijk_adjacent = re.compile(r'(?:Δ_(\d+)(?![\d\|]))')
pDijk_non_adjacent = re.compile(r'(?:Δ_(\d+)\|(\d+)\|(\d+))')
p3B = re.compile(r'(?:\u27e8|\[)(\d+)(?:\|\({0,1})([\d+[\+|-]*]*)(?:\){0,1}\|)(\d+)(?:\u27e9|\])')
ptr5 = re.compile(r'(?:tr5_)(\d+)')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #


class Particles_Eval:

    @staticmethod
    def _parse(string, field):
        string = string.replace("^", "**").replace(" ", "").replace("\n", "")
        string = pA2bis.sub(r"⟨\1|\2⟩", string)
        string = pA2.sub(r"oPs.compute('⟨\1|\2⟩')", string)
        string = pS2bis.sub(r"[\1|\2]", string)
        string = pS2.sub(r"oPs.compute('[\1|\2]')", string)
        string = pSijk.sub(r"oPs.compute('s_\1')", string)
        string = pOijk.sub(r"oPs.compute('Ω_\1')", string)
        string = pPijk.sub(r"oPs.compute('Π_\1')", string)
        string = ptr5.sub(r"oPs.compute('tr5_\1')", string)
        string = pDijk_adjacent.sub(r"oPs.compute('Δ_\1')", string)
        string = pDijk_non_adjacent.sub(r"oPs.compute('Δ_\1|\2|\3')", string)
        string = p3B.sub(r"oPs.compute('⟨\1|(\2)|\3]')", string)
        string = re.sub(r'(\d)s', r'\1*s', string)
        string = re.sub(r'(\d)o', r'\1*o', string)
        string = string.replace(')s', ')*s').replace(')o', ')*o')
        string = string.replace(')(', ')*(')
        re_rat_nbr = re.compile(r"(?<!\*\*)(\d+)\/(\d+)")
        if field.name == "padic":
            string = re_rat_nbr.sub(r"PAdic(\1,{characteristic},{digits})/PAdic(\2,{characteristic},{digits})".format(
                characteristic=field.characteristic, digits=field.digits), string)
        elif field.name == "finite field":
            string = re_rat_nbr.sub(r"ModP(\1,{characteristic})/ModP(\2,{characteristic})".format(
                characteristic=field.characteristic), string)
        elif field.name == 'mpc':
            string = re_rat_nbr.sub(r"mpmath.mpf(\1)/mpmath.mpf(\2)", string)
        return string

    def _eval(self, string):
        return ast_eval_expr(self._parse(string, self.field), {'oPs': self})


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #


def ast_eval_expr(expr, locals_={}):
    return _eval_node(ast.parse(expr, mode='eval').body, locals_=locals_)


def _eval_node(node, locals_={}):
    locals().update(locals_)
    if isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.BinOp):
        return operators[type(node.op)](_eval_node(node.left, locals_), _eval_node(node.right, locals_))
    elif isinstance(node, ast.UnaryOp):
        return operators[type(node.op)](_eval_node(node.operand, locals_))
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.value.id == 'oPs' and node.func.attr == 'compute':
            function, method = node.func.value.id, node.func.attr
            argument = node.args[0].s if sys.version_info[0] > 2 else node.args[0].s.decode('utf-8')
            allowed_func_call = "{function}.{method}('{argument}')".format(function=function, method=method, argument=argument)
        elif isinstance(node.func, ast.Attribute) and node.func.value.id == 'mpmath' and node.func.attr in ['mpf', 'sqrt']:
            function, method = 'mpmath', node.func.attr
            if hasattr(node.args[0], 'id'):
                argument = ast_eval_expr(node.args[0].id, locals_)
            else:
                argument = _eval_node(node.args[0], locals_)
            allowed_func_call = "{function}.{method}('{argument}')".format(function=function, method=method, argument=argument)
        elif isinstance(node.func, ast.Name) and node.func.id == 'PAdic':
            function, arguments = 'PAdic', [arg.n for arg in node.args]
            allowed_func_call = "{function}({arguments})".format(function=function, arguments=", ".join(map(str, arguments)))
        else:
            raise TypeError(node)
        return eval(allowed_func_call)
    elif isinstance(node, ast.Name):
        if node.id in locals() and type(locals()[node.id]) in [int, float, GaussianRational, PAdic, ModP, mpmath.mpc, mpmath.mpc]:
            return eval(node.id)
        else:
            raise TypeError(node)
    else:
        raise TypeError(node)
