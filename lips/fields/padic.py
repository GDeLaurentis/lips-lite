# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import functools
import numpy

from .finite_field import ModP

recover_precision_from_exact_powers_of_p = False

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #


def to_base(num, p):
    if num < p:
        return (num, )
    else:
        return (num % p, ) + (to_base(num // p, p))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #


def padicfy(func):
    @functools.wraps(func)
    def wrapper_padicfy(self, other):
        if type(other) is PAdic:
            return func(self, other)
        elif type(other) in [int, ModP, numpy.int64] or str(type(other)) == "long":
            return func(self, PAdic(other, self.p, (self.k + self.n) if (self.k + self.n) > 0 else 0))
        else:
            return NotImplemented
    return wrapper_padicfy


def check_orderable(func):
    @functools.wraps(func)
    def wrapper_check_orderable(self, other):
        if type(self) != type(other):
            raise TypeError("unorderable types: {} < {}".format(type(self), type(other)))
        if self.p != other.p:
            raise Exception("unorderable padics over different primes: {}, {}.".format(self.p, other.p))
        return func(self, other)
    return wrapper_check_orderable


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #


class PAdic(object):

    """PAdic numbers, with p prime, k digits, n valuation."""

    def __init__(self, num, p=None, k=None, n=0, from_addition=False):
        """0 ≤ num ≤ p ^ k - 1; p: prime; k: significant digits; n: power of prefactors of p (valuation)."""
        if p is not None and k is not None:
            self.p = p
            factors_of_p = next((i for i, j in enumerate(to_base(num, p)) if j != 0), 0)
            self.k = k - from_addition * factors_of_p
            num = int(num // p ** factors_of_p) % (p ** self.k)
            self.n = factors_of_p + n
            self.num = num
            if recover_precision_from_exact_powers_of_p is True and num == 1 and factors_of_p > 0:
                print("!Warning! recovering a digit.")
                self.k = self.k + factors_of_p
        else:
            raise Exception("Invalid p-adic initialisation")

    # GETTERS and SETTERS

    @property
    def num(self):
        """0 ≤ num ≤ p ^ k - 1"""
        return self._num

    @num.setter
    def num(self, value):
        if value < 0:
            raise Exception("Padic num should be non-negative")
        self._num = value

    @property
    def p(self):
        """p: prime for the padic."""
        return self._p

    @p.setter
    def p(self, value):
        if value <= 0:
            raise Exception("Padic p should be positive, got: {}.".format(value))
        self._p = value

    @property
    def k(self):
        return self._k

    @k.setter
    def k(self, value):
        """k: number of significant digits."""
        if value < 0:
            value = 0
        self._k = value

    @property
    def as_tuple(self):
        return (to_base(int(self), self.p) + tuple([0 for i in range(self.k)]))[:self.k]

    def __getstate__(self):
        return (int(self), self.p, self.k, self.n)

    def __setstate__(self, state):
        self.__init__(*state)

    def __str__(self):
        if self.k == 0:
            return "O({}^{})".format(self.p, self.n)
        else:
            return " + ".join(filter(lambda x: x is not None,
                                     ["{}".format(i) if (j == 0 and i != 0) else
                                      "{}*{}".format(i, self.p) if (j == 1 and i != 0) else
                                      "{}*{}^{}".format(i, self.p, j) if (i != 0) else None
                                      for i, j in zip(self.as_tuple, range(self.n, self.n + self.k))])) + " + O({}^{})".format(self.p, self.n + self.k)

    def __repr__(self):
        return str(self)

    # COMPARISON

    @check_orderable
    def __eq__(self, other):
        return all([int(self) == int(other), self.p == other.p, self.k == other.k, self.n == other.n])
    #  or all([int(self) == int(other) == 0, self.p == other.p, self.k + self.n == other.k]))  # e.g. 0 * p + O(p^2) == 0 + O(p^2)

    @check_orderable
    def __le__(self, other):
        return self.n >= other.n

    @check_orderable
    def __lt__(self, other):
        return self.n > other.n

    @check_orderable
    def __ge__(self, other):
        return self.n <= other.n

    @check_orderable
    def __gt__(self, other):
        return self.n < other.n

    # ALGEBRA

    def __int__(self):
        return self.num

    def __abs__(self):
        return PAdic(0, self.p, 0, self.n)

    @padicfy
    def __add__(self, other):
        if self.n > other.n:
            return other + self
        else:
            return PAdic((int(self) + int(other) * self.p ** (other.n - self.n)), self.p,
                         self.k if self.k < (other.n - self.n) + other.k else (other.n - self.n) + other.k, self.n, from_addition=True)
#                         ((self.k + self.n) if (self.k + self.n) < (other.k + other.n) else (other.k + other.n)) - self.n, self.n, from_addition=True)

    @padicfy
    def __radd__(self, other):
        return other + self

    @padicfy
    def __sub__(self, other):
        return self + (- other)

    @padicfy
    def __rsub__(self, other):
        return - (self - other)

    @padicfy
    def __mul__(self, other):
        return PAdic((int(self) * int(other)) % self.p ** self.k, self.p, min([self.k, other.k]), self.n + other.n)

    @padicfy
    def __rmul__(self, other):
        return self * other

    @padicfy
    def __truediv__(self, other):
        return PAdic((int(self) * ModP(int(other), other.p ** other.k)._inv()) % self.p ** self.k, self.p, min([self.k, other.k]), self.n - other.n)

    @padicfy
    def __div__(self, other):
        return self.__truediv__(other)

    @padicfy
    def __rtruediv__(self, other):
        return other / self

    @padicfy
    def __rdiv__(self, other):
        return self.__rtruediv__(other)

    def __neg__(self):
        return PAdic((-1 * int(self)) % self.p ** self.k, self.p, self.k, self.n)

    def __pow__(self, n):
        assert(isinstance(n, int) or n.is_integer())
        if n == 0:
            return PAdic(1, self.p, self.k)
        elif n % 2 == 0:
            root_2_res = self ** (n / 2)
            return root_2_res * root_2_res
        else:
            return self * (self ** (n - 1))
