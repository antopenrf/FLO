pi = 3.141592653589793


def C_lambda(v):
    """Lib 2-port: Capacitor"""
    c = lambda f: -1.0j/2.0/pi/f/v*1000.0 if f !=0 else float(1e100)
    return c

def L_lambda(v):
    """Lib 2-port: Inductor"""
    l = lambda f: 1.0j*2.0*pi*f*v
    return l

def R_lambda(v):
    """Lib 2-port: Resistor"""
    r = lambda f: v##Decimal(v)
    return r



