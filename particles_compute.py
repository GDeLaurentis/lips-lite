#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   ___          _   _    _          ___                     _
#  | _ \__ _ _ _| |_(_)__| |___ ___ / __|___ _ __  _ __ _  _| |_ ___
#  |  _/ _` | '_|  _| / _| / -_|_-<| (__/ _ \ '  \| '_ \ || |  _/ -_)
#  |_| \__,_|_|  \__|_\__|_\___/__(_)___\___/_|_|_| .__/\_,_|\__\___|
#                                                 |_|

# Author: Giuseppe


from __future__ import unicode_literals

import sys
import numpy as np
import re

from antares.core.tools import MinkowskiMetric, pSijk, pd5, pDijk, pOijk, pPijk, pA2, pS2, pNB


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #


class Particles_Compute:

    def ldot(self, A, B):
        """Lorentz dot product: P_A^μ * η_μν * P_B^ν."""
        p_lowered_index = np.dot(MinkowskiMetric, self[B].four_mom)
        p_lowered_index = np.transpose(p_lowered_index)
        return np.dot(self[A].four_mom, p_lowered_index)

    def compute(self, temp_string):
        """Computes spinor strings.\n
        Available variables: ⟨a|b⟩, [a|b], ⟨a|b+c|d], ⟨a|b+c|d+e|f], ..., s_ijk, Δ_ijk, Ω_ijk, Π_ijk"""
        self.check_consistency(temp_string)                         # Check consistency of string

        if pOijk.findall(temp_string) != []:                        # Ω_ijk
            ijk = map(int, pOijk.findall(temp_string)[0])
            nol = self.ijk_to_3NonOverlappingLists(ijk)
            Omega = (2 * self.compute("s_" + "".join(map(unicode, nol[2]))) * self.compute("s_" + "".join(map(unicode, nol[1]))) -
                     (self.compute("s_" + "".join(map(unicode, nol[2]))) + self.compute("s_" + "".join(map(unicode, nol[1]))) -
                      self.compute("s_" + "".join(map(unicode, nol[0])))) * self.compute("s_" + "".join(map(unicode, nol[2] + [nol[0][0]]))))
            return Omega

        if pPijk.findall(temp_string) != []:                        # Π_ijk, eg: Π_351 = s_123-s124
            ijk = map(int, pPijk.findall(temp_string)[0])
            nol = self.ijk_to_3NonOverlappingLists(ijk)
            Pi = (self.compute("s_" + "".join(map(unicode, nol[2] + [nol[0][0]]))) - self.compute("s_" + "".join(map(unicode, nol[2] + [nol[0][1]]))))
            return Pi

        if pDijk.findall(temp_string) != []:                        # Δ_ijk
            ijk = map(int, pDijk.findall(temp_string)[0])
            temp_oParticles = self.ijk_to_3Ks(ijk)
            Delta = temp_oParticles.ldot(1, 2)**2 - temp_oParticles.ldot(1, 1) * temp_oParticles.ldot(2, 2)
            return Delta

        if pd5.findall(temp_string) != []:
            return (2 * self.compute("s_12") * self.compute("s_23") * self.compute("s_34") * self.compute("s_45") +
                    2 * self.compute("s_12") * self.compute("s_23") * self.compute("s_34") * self.compute("s_51") +
                    2 * self.compute("s_12") * self.compute("s_23") * self.compute("s_45") * self.compute("s_51") -
                    2 * self.compute("s_12") * self.compute("s_23") * self.compute("s_23") * self.compute("s_34") +
                    2 * self.compute("s_12") * self.compute("s_34") * self.compute("s_45") * self.compute("s_51") -
                    2 * self.compute("s_12") * self.compute("s_45") * self.compute("s_51") * self.compute("s_51") -
                    2 * self.compute("s_12") * self.compute("s_12") * self.compute("s_23") * self.compute("s_51") +
                    1 * self.compute("s_12") * self.compute("s_12") * self.compute("s_23") * self.compute("s_23") +
                    1 * self.compute("s_12") * self.compute("s_12") * self.compute("s_51") * self.compute("s_51") +
                    2 * self.compute("s_23") * self.compute("s_34") * self.compute("s_45") * self.compute("s_51") -
                    2 * self.compute("s_23") * self.compute("s_34") * self.compute("s_34") * self.compute("s_45") +
                    1 * self.compute("s_23") * self.compute("s_23") * self.compute("s_34") * self.compute("s_34") -
                    2 * self.compute("s_34") * self.compute("s_45") * self.compute("s_45") * self.compute("s_51") +
                    1 * self.compute("s_34") * self.compute("s_34") * self.compute("s_45") * self.compute("s_45") +
                    1 * self.compute("s_45") * self.compute("s_45") * self.compute("s_51") * self.compute("s_51"))

        elif pSijk.findall(temp_string) != []:                      # S_ijk...
            ijk = map(int, pSijk.findall(temp_string)[0])
            s = 0
            for i in range(len(ijk)):
                for j in range(i + 1, len(ijk)):
                    s = s + 2 * self.ldot(ijk[i], ijk[j])
            return s

        elif pA2.findall(temp_string) != []:                        # ⟨A|B⟩ -- contraction is up -> down : lambda[A]^alpha.lambda[B]_alpha
            A, B = map(int, pA2.findall(temp_string)[0])
            return np.dot(self[A].r_sp_u, self[B].r_sp_d)[0, 0]

        elif pS2.findall(temp_string) != []:                        # [A|B] -- contraction is down -> up : lambda_bar[A]_alpha_dot.lambda_bar[B]^alpha_dot
            A, B = map(int, pS2.findall(temp_string)[0])
            return np.dot(self[A].l_sp_d, self[B].l_sp_u)[0, 0]

        elif pNB.findall(temp_string) != []:                        # ⟨A|(B+C+..)..|D]
            abcd = pNB.search(temp_string)
            a = int(abcd.group('start'))
            bc = abcd.group('middle')
            d = int(abcd.group('end'))
            bc = re.split('[\)|\|]', bc)
            bc = [entry.replace('|', '') for entry in bc]
            bc = [entry.replace('(', '') for entry in bc]
            bc = [entry for entry in bc if entry != '']
            a_or_s = temp_string[0]
            if a_or_s == '⟨':
                result = self[a].r_sp_u
            elif a_or_s == '[':
                result = self[a].l_sp_d
            else:
                print "Critical error: string must start with ⟨ or [."
                sys.exit('Invalid string in compute.')
            for i in range(len(bc)):
                comb_mom = re.sub(r'(\d)', r'self[\1].four_mom', bc[i])
                comb_mom = eval(comb_mom)
                if a_or_s == "⟨":
                    result = np.dot(result, self._four_mom_to_r2_sp_bar(comb_mom))
                    a_or_s = "["                                    # needs to alternate
                elif a_or_s == "[":
                    result = np.dot(result, self._four_mom_to_r2_sp(comb_mom))
                    a_or_s = "⟨"                                    # needs to alternate
            if a_or_s == "⟨":
                result = np.dot(result, self[d].r_sp_d)
            elif a_or_s == "[":
                result = np.dot(result, self[d].l_sp_u)
            return result[0][0]
        else:
            print "Critical error: string {} is not implemented.".format(temp_string)
            sys.exit('Invalid string in compute.')
