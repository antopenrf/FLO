from math import pi
from .utility import prompt_out
from .port import Port
from .library import *
from decimal import *
#getcontext().prec = 200

def _S_lambda(spara, z):
    """Return s-parameter lambdas from given impedance."""
    if spara in ('11', '22'):
        return lambda f: z(float(f)) / ( z(float(f)) + 100.0)##Decimal(100) )

    elif spara in ('21', '12'):
        return lambda f: 100.0 / (z(float(f)) + 100.0)##Decimal(100) / ( z(f) + 100)##Decimal(100) )  ##100.0 is 2xZo (100)

    else: 
        pass


class Element(object):
    """
    The class to instantiate element objects.

    Attributes (instance):
    name -- element name, such as 'C1', 'L1', 'R1'
    value -- element values

    Methods:
    """
    
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.element_type = '_' + self.__class__.__name__
        self.unit = 'ohm'  ## default unit
        
    def __repr__(self):
        return "{n}: {t}({v} {u})".format(t = self.element_type[1:], n = self.name, v = self.value, u = self.unit)

    def __str__(self):
        return "{name}, {value} {u}, connects from p{p1} to p{p2}".format(name = self.name, value = self.value, u = self.unit, p1 = self.ports[0], p2 = self.ports[1])
    
    def _S(self, para, freq = None):
        """Return Spara lambda if no assigned freq, or Spara value if frequencies are given."""
        _lambda = _S_lambda(para, self.z)
        if freq == None:
            return para ## need to be fixed!!
        elif type(freq) in (Decimal, int, float):
            freq = float(freq)
            #freq = Decimal(freq)
            return _lambda(freq)
        elif type(freq) in (list, tuple):
            return [_lambda(each_f) for each_f in freq]
        else:
            pass


class EnP(object):
    def __init__(self, ports = (0, 0)):
        self.ports = list(ports)
        self.originals = list(ports)

        self.updatePorts()
        

    def reFlow(self, leading):
        n = self.ports.index(leading)
        self.ports[n] = self.ports[0]
        self.ports[0] = leading
        self.makeNodes()
        self.makeFlow()

    def updatePorts(self):
        ports = self.ports
        ### --- node_nos (node numbers in string) are to give names for Node instance.
        ### --- Positive nodes correspond to schematic ports (self.ports).
        ### --- Negative porrs for the other direction      
        ## All four ports are listed as '+1', '+2', '-1', '-2'
        self.makeNodes()
        self.makeFlow()        

    def makeNodes(self):
        ports = self.ports
        self.node_nos = [ '+' + str(n) for n in ports ] + [ '-' + str(n) for n in ports ]
        
    def makeFlow(self):
        self._flow_map = {}        
        n = len(self.ports)
        for into in range(1, n+1):
            if into == 1:
                inode = self.node_nos[into - 1]
            else:
                inode = self.node_nos[into + n - 1]
                
            for outof in range(1, n+1):
                if outof == 1:
                    onode = self.node_nos[outof + n - 1]
                else:
                    onode = self.node_nos[outof - 1]
                sij = str(outof) + str(into)
                self._flow_map[(inode, onode)] = sij


        
class Cap(Element, EnP):
    """Capacitor"""
    def __init__(self, name, value, ports):
        Element.__init__(self, name, value)
        EnP.__init__(self, ports)  ### 'ports' are the two ports assigned to 2-port element.
        self.z = C_lambda(value)
        self.unit = 'pF'
        
class Ind(Element, EnP):
    """Inductor"""
    def __init__(self, name, value, ports):
        Element.__init__(self, name, value)
        EnP.__init__(self, ports)  ### 'ports' are the two ports assigned to 2-port element.
        self.z = L_lambda(value)
        self.unit = 'nH'

class Res(Element, EnP):
    """Resistor"""
    def __init__(self, name, value, ports):
        Element.__init__(self, name, value)
        EnP.__init__(self, ports)  ### 'ports' are the two ports assigned to 2-port element.
        self.z = R_lambda(value)
        self.unit = 'ohm'


class JCT(Element, EnP):
    """Ideal n-port junction"""
    def __init__(self, name, value, ports):    
        Element.__init__(self, name, value = None)    
        EnP.__init__(self, ports)
        n = len(ports)
        for into in range(1, n+1):
            for outof in range(1, n+1):
                sij = 'S' + str(outof) + str(into)
                if into == outof:
                    rl = (2.0 - n) / n  ## rl: return loss
                    setattr(self, sij, rl)
                else:
                    il = 2.0 / n      ## il: insersion loss
                    setattr(self, sij, il)


class J3P(Element, EnP):
    """Ideal 3-port junction"""
    def __init__(self, name, value, ports):
        Element.__init__(self, name, value = None)
        EnP.__init__(self, ports)
        self.S11 = -1.0/3.0
        self.S22 = -1.0/3.0
        self.S33 = -1.0/3.0
        self.S12 = 2.0/3.0
        self.S13 = 2.0/3.0
        self.S21 = 2.0/3.0
        self.S23 = 2.0/3.0
        self.S31 = 2.0/3.0
        self.S32 = 2.0/3.0

class PIN(Element, EnP):
    """Input Port"""
    def __init__(self, name, value, ports):
        Element.__init__(self, name, value = 50.0)  ### value is port impedance.
        EnP.__init__(self, ports)
        self.S22 = (value - 50.0) / (value + 50.0)
        self.S12 = 1 - self.S22
        self.S11 = 0.0
        self.S21 = 1.0
        
class POUT(Element, EnP):
    """Output Port"""
    def __init__(self, name, value, ports):
        Element.__init__(self, name, value = 50.0)  ### value is port impedance.
        EnP.__init__(self, ports)
        self.S11 = (value - 50.0) / (value + 50.0)
        self.S21 = 1 - self.S11
        self.S22 = 0.0
        self.S12 = 1.0
        
_elmt_class_map_ = {'l': Ind, 'c': Cap, 'r': Res}


if __name__ == '__main__':
    
    c1 = Cap('c1', 5, (4, 5))
    print(c1)
    c1
    print("S11 in lambda: c1.S11")
    print(c1.S11)
    print("\n")
    print("S11 in complex: c1.S11(1)")
    print(c1.S11(1))
    print(c1.port[0])
    print(c1.port[1])
    print(c1.port[2])
    c1.port[1].set_pn(7)
    print(c1.port[1])
    print(c1.port[2])
