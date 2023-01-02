# -*- coding: utf-8 -*-
"""
Created on Tue Jan 18 09:36:52 2022

@author: Thibault
"""

from FitModule.fit_module import FitBase
import numpy as np

class Fit(FitBase):
    
    @staticmethod
    def cavity_reflection(x, params):
        '''Fit function for the MW cavity in reflection.'''
        Fit.cavity_reflection.keys= ['x0', 'kappa_c_hz',
                                     'kappa_hz', 'K', 'elec', 'phi', 'phi2']
        x0, kappa_c_hz, kappa_hz, K, elec, phi, phi2 = params
        return np.exp(1j*(elec*(x-x[0])+phi))*K*(
            -1.+kappa_c_hz*np.exp(1j*phi2)/(
                1j*(x-x0)+0.5*kappa_hz))

    @staticmethod
    def cavity_reflection_guess(x, y):
        '''Extract initial guess parameters for the cavity fit, from the reflection data.'''
        elec_guess = (np.angle(y[-1]) - np.angle(y[0])) / (x[-1] - x[0])
        phi_guess = np.pi + np.angle(y[0])
        arg_x0 = np.argmin(np.abs(y))
        x0_guess = x[arg_x0]
        kappa_guess = np.max(x) - np.min(x)  # np.max(x_res)-np.min(x_res)
        K_guess = np.mean(np.abs(y))
        y_res = y[arg_x0]
        y_far_away = (y[0] + y[-1]) / 2.
        # alpha = abs(y_res  / y_far_away)
        alpha = (y_res - y_far_away) / y_far_away
        # kappa_c_guess = 0.5 * kappa_guess * (1 + alpha)
        kappa_c_guess = 0.5 * kappa_guess * abs(alpha)
        res = x0_guess, kappa_c_guess, kappa_guess, K_guess, elec_guess, phi_guess, 0
        return res