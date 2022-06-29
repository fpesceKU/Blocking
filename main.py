import numpy as np
from scipy.optimize import minimize
from block_tools import *
from scipy.stats import gaussian_kde
from scipy.stats import norm

class BlockAnalysis:

    def __init__(self, x, multi=1, weights=None, bias=None, T=None, interval_low=None, interval_up=None, dt=1):
        self.multi = multi
        self.x = check(x, self.multi)
        self.w = weights
        
        self.interval = []
        self.interval.append(self.x.min() if interval_low is None else interval_low)
        self.interval.append(self.x.max() if interval_up is None else interval_up)      

        if (self.w is None) and (bias is not None):
            bias -= np.max(bias)
            self.kbT = 0.008314463*T
            self.w = np.exp(bias/(self.kbT))
            self.w = check(x, self.multi)

        if self.w is None:
            self.stat = blocking(self.x, self.multi)
            self.av = self.x.mean()
        else:
            self.w /= self.w.sum()
            self.stat = fblocking(self.x, self.w, self.kbT, self.multi, self.interval)

        self.stat[...,0] /= dt

    def SEM(self):

        def find_n_intersect(x,stat):
                c=0
                for i,p in enumerate(stat):
                    if (x <= p[1]+p[2]) and (x >= p[1]-p[2]):
                        c += 1
                        #c += norm(p[1],p[2]).pdf(x)
                return -c

        c = np.zeros(len(self.stat))
        for i,b in enumerate(self.stat):
            lower_bound = b[1]-b[2]
            upper_bound = b[1]+b[2]
            bnds = [(lower_bound, upper_bound)]
            c[i] -= minimize( fun=find_n_intersect, x0=b[1], args=self.stat[self.stat[...,0] > b[0]], bounds=bnds ).fun
       	self.bs = self.stat[...,0][np.argmax(c)]
        self.sem = self.stat[...,1][np.argmax(c)]
 
    def get_pdf(self):

        min_ = self.interval[0]
        max_ = self.interval[1]
        x = np.linspace( min_, max_, num = 100 )
        u = gaussian_kde( self.x, bw_method = "silverman", weights = self.w ).evaluate(x)

        N = int(len(self.x))
        Nb = int(N / self.bs)

        W = self.w.sum()
        S = (self.w**2).sum()        

        blocks_pi = []
        for n in range(1, Nb+1):
            end = int( self.bs * n )
            start = int( end - self.bs )
            pdf_i = gaussian_kde( self.x[start:end], bw_method = "silverman", weights = self.w[start:end] ).evaluate(x)
            wi = self.w[start:end].sum()
            blocks_pi.append( wi*(pdf_i-u)**2 )
    
        blocks_pi = np.array(blocks_pi)
        e = np.sqrt( blocks_pi.sum(axis=0) / (Nb*(W-S/W)) )
    
        return x, u, e

    def get_fes(self):
        x, H, E = self.get_pdf()
        F = -self.kbT * np.log(H)
        FE = self.kbT * E / H
        return x, F, FE

    def get_av_err(self):
        x, H, E = self.get_pdf()
        H /= H.sum()
        av = np.average(x, weights=H)
        err = np.sqrt((H**2*E**2).sum())
        return av, err
