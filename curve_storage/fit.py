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
    
    @staticmethod
    def lorentzian_triplets(x, params):
        Fit.lorentzian_triplets.keys= ['offset', 'x0_1',
                                                 'height_1', 'dx_1',
                                                 'x0_2',
                                                 'height_2', 'dx_2',
                                                 'x0_3',
                                                 'height_3', 'dx_3']
        offset, x0_1, height_1, dx_1, x0_2, height_2, dx_2, x0_3, height_3, dx_3=params
        # remember np.pi*dx is Gamma_m/2
        return offset + height_1* (1 + (x-x0_1)**2/dx_1**2)**-1\
               +height_2*(1 + (x-x0_2)**2/dx_2**2)**-1\
               +height_3*(1 + (x-x0_3)**2/dx_3**2)**-1

    @staticmethod
    def lorentzian_triplets_guess(x, y):
        offset_guess=0.5*(np.mean(y[:10])+np.mean(y[-10:]))
        height_guess=np.nanmax(y)-offset_guess
        x0_guess=x[np.nanargmax(y)]
        dx_guess=(np.max(x)-np.min(x))/10
        detuning=3*dx_guess
        return (offset_guess, x0_guess, height_guess, dx_guess, x0_guess-detuning, height_guess, dx_guess,
               x0_guess+detuning, height_guess, dx_guess)

    
    @staticmethod
    def ringdown(x, params):
        '''Fit function for individual ringdowns.
        A fit to an exponential plus a constant background'''
        Fit.ringdown.keys= ['offset', 'slope',
                                      'noise']
        offset, slope, noise=params
        return np.abs(offset)*np.exp(-np.abs(slope)*(x-x[0]))+np.abs(noise)

    @staticmethod
    def ringdown_guess(x, y):
        '''Function to extract initial guesses from the data for the fitfunction.'''
        y=np.abs(y)
        x=np.abs(x)
        noise_guess=np.mean(y[-10:])
        offset_guess=np.mean(y[:10])-noise_guess
        x, y = x[abs(y)!=0.],  20.*np.log10(np.abs(y[abs(y)!=0.]))
        slope_guess, offset_guess_bis=np.polyfit(x[:20], y[:20], 1)
        return offset_guess, slope_guess, noise_guess
    
    @staticmethod
    def lorentzian(x, params):
        Fit.lorentzian.keys= ['offset', 'x0',
                              'height', 'dx']
        offset, x0, height, dx=params
        # remember np.pi*dx is Gamma_m/2
        return offset + np.abs(height)* (1 + (x-x0)**2/dx**2)**-1

    @staticmethod
    def lorentzian_guess(x, y):
        offset_guess=0.5*(np.mean(y[:10])+np.mean(y[-10:]))
        height_guess=np.nanmax(y)-offset_guess
        x0_guess=x[np.nanargmax(y)]
        dx_guess=(np.max(x)-np.min(x))/10
        return (offset_guess, x0_guess, height_guess, dx_guess)
    
    @staticmethod
    def lorentzian_db(x, params):
        Fit.lorentzian_db.keys= ['offset', 'x0',
                              'height', 'dx']
        offset, x0, height, dx=params
        # remember np.pi*dx is Gamma_m/2
        return 10*np.log10(1000*(np.abs(offset) + np.abs(height)* (1 + (x-x0)**2/dx**2)**(-1)))

    @staticmethod
    def lorentzian_db_guess(x, y):
        y=1e-3*10**(y/10)
        offset_guess=0.5*(np.mean(y[:10])+np.mean(y[-10:]))
        height_guess=np.nanmax(y)-offset_guess
        x0_guess=x[np.nanargmax(y)]
        dx_guess=(np.max(x)-np.min(x))/10
        return (offset_guess, x0_guess, height_guess, dx_guess)
    
    @staticmethod
    def reflection_optical(x, params):
        Fit.reflection_optical.keys= ['offset', 'x0',
                              'height', 'dx']
        offset, x0, height, dx=params
        # remember np.pi*dx is Gamma_m/2
        return offset + height* (1 + (x-x0)**2/dx**2)**-1

    @staticmethod
    def reflection_optical_guess(x, y):
        offset_guess=0.5*(np.mean(y[:10])+np.mean(y[-10:]))
        height_guess=np.nanmin(y)-offset_guess
        x0_guess=x[np.nanargmin(y)]
        dx_guess=(np.max(x)-np.min(x))/10
        return (offset_guess, x0_guess, height_guess, dx_guess)

    @staticmethod
    def reflection_optical_Fano(x, params):
        Fit.reflection_optical_Fano.keys= ['offset', 'x0',
                              'height', 'dx', 'q']
        offset, x0, height, dx, q=params
        # remember np.pi*dx is Gamma_m/2
        return offset + height*(1-q**2-q/dx*(x-x0))*(1 + (x-x0)**2/dx**2)**-1

    @staticmethod
    def reflection_optical_Fano_guess(x, y):
        offset_guess=0.5*(np.mean(y[:10])+np.mean(y[-10:]))
        height_guess=np.nanmin(y)-offset_guess
        x0_guess=x[np.nanargmin(y)]
        dx_guess=(np.max(x)-np.min(x))/10
        q=0
        return (offset_guess, x0_guess, height_guess, dx_guess, q)
    
    @staticmethod
    def PDH(x, params):
        Fit.PDH.keys= ['offset', 'x0', 'Omega',
                       'height', 'r', 'FSR']
        offset, x0, Omega, height, r, FSR=params
        # remember np.pi*dx is Gamma_m/2
        def F(omega, FSR, r):
            return r*(np.exp(1j*omega/FSR)-1)/(1-r**2*np.exp(1j*omega/FSR))
        return offset + height*(F(x, FSR, r)*np.conjugate(F(x+Omega, FSR, r))
                                -np.conjugate(F(x, FSR, r))*F(x-Omega, FSR, r))
        
    @staticmethod
    def PDH_guess(x, y):
        offset_guess=0.5*(np.mean(y[:10])+np.mean(y[-10:]))
        height_guess=(np.nanmax(y)-np.nanmin(y))/2
        x0_guess=x[np.nanargmin(y)]
        FSR_guess=600*(np.max(x)-np.min(x))
        r_guess=0.99999
        Omega_guess=(np.max(x)-np.min(x))/4
        return (offset_guess, x0_guess, Omega_guess,
                height_guess, r_guess, FSR_guess)
    
    
