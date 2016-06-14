"""Illustration of the concept of using 'port' module.
c1 = Cap('c1', 1)
c1.nosp = 2, nocp: number of schematic ports
c1.nond = 4, nond: number of matrix nodes
c1.s_ports = (1, 2)
c1.m_ports = (1, 2, -1, -2)

c2 = Cap('c2', 2)
c2.nosp = 2
c2.nomp = 4
c2.s_ports = (3, 4)        -- seq of ports for symbol
c2.m_ports = (3, 4, -3, -4)  -- seq of ports for matrix

c1.wire.c2(1, 3)

"""

class Port(object):

    def __init__(self, s_port_number):
        self.pn = s_port_number  ## pn: port number
        self.pt = 'linear'       ## pt: port type
        
    def __repr__(self):
        return "Port Number: {pn}".format(pn = str(self.pn))


    def set_pn(self, s_port_number):
        self.pn = s_port_number

