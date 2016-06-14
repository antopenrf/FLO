
#! /usr/bin/python

# Note1: This is the most inner module for connecting the 'dots'.
# One node (dot) represents either incoming (a) or outgoing (b) normalized waves.
# e.g: One 2-port network should consist of four nodes, two a's and two b's.

# Note2: The algorithm applied here is simply using signal flow chart.
# Each node is tick-ed to follow to all the joined nodes, which then are then
# tack-ed to be ready for ticking again.
# This 'tick-tack' algorithm is different from conventional ABCD matrix method.

from decimal import *
getcontext().prec = 200

__version__ = "1.0"  ## Initial version started from year 2015.
        
class Node(object):

    def __init__(self, nodename):
        self.nodename = nodename
        self.en = 0.0#Decimal(0.0)  ## voltage (en) initialized as 0.0
        self.sf = 0.0#Decimal(0.0)  ## signal flows
#        self.branching_coef = 1.0
        self.shunting_node = False
        self.outnodes = {}
        self.sequence = 0
        self.from_node = "IC"   ## 'IC' stands for initial condition.
#        self._delta = 0.0
        self._tick = False
        self._flow = None

    def __repr__(self):
        alloutnodes = ''
        shunting = ''
        for each in self.outnodes.keys():
            alloutnodes += ' ' + each.nodename + ' with coef = ' + str(self.outnodes[each]) + '.'
        if alloutnodes == '':
            alloutnodes = 'None'
        if self.shunting_node:
            shunting = ', and is a shunting node.'
        return 'Node ' + self.nodename + ' connected to nodes: ' + alloutnodes + shunting

    def __str__(self):
        return 'node ' + self.nodename

    def reset(self):
        self.en = 0.0#Decimal(0.0)
        self.sf = 0.0#Decimal(0.0)
        self._tick = False
        
    def connect(self, node, coef = 0.0):#Decimal(0)):
        self.outnodes[node] = coef
        
    def newflow(self):
        try:
            self._flow.close()
        except:
            pass            
        def flow():
            count = 1
            while True:
                incoming = yield
                ####self.en = incoming
                self.sf = incoming
#                print('\tCount ' + str(count) + ' Sequence ' + str(self.sequence) + ': at ' + self.nodename + ' (coming from ' + self.from_node + ') en= ' + str(self.en) + ' and sf= ' + str(self.sf))
                for node in self.outnodes:

                    node.from_node = self.nodename
                    node.sf = node.sf + self.sf*self.outnodes[node]
                    node.en = node.en + self.sf*self.outnodes[node]

#                    print('\tSending to: ' + node.nodename + ' with (sf)'+ str(node.sf))
                    node._tick = True
#                print("\n")
                count += 1 
  
        _newflow = flow()
        next(_newflow)
        self._flow = _newflow      

    def tack(self):
        if self._tick:
            self._flow.send(self.sf)
            #self.sf = Decimal(0)
            self._tick = False


    
if __name__ == '__main__':
    def test6():
        """Series two 50 ohms with five 50 ohms shunt in the middle."""
        P1 = Node('+1')
        N1 = Node('-1')
        P2 = Node('+2')
        N2 = Node('-2')
        P3 = Node('+3')
        N3 = Node('-3')
        P01 = Node('+01')
        N01 = Node('-01')
        P02 = Node('+02')
        N02 = Node('-02')
        P03 = Node('+03')
        N03 = Node('-03')
        P04 = Node('+04')
        N04 = Node('-04')
        P05 = Node('+05')
        N05 = Node('-05')

        branching = 2.0/13.0  
        P1.connect(N1, 1.0/3.0)
        P1.connect(P2, 2.0/3.0)
        N2.connect(P2, 1.0/3.0)
        N2.connect(N1, 2.0/3.0)
        N1.connect(P1, 0)
        P2.connect(N2, -4.0/13.0) ## shunting S11's
        
        P2.connect(P01, branching)
        P01.connect(N01, -1.0)
        N01.connect(P01, 1.0/3.0)
        N01.connect(N2, 2.0/3.0)

        P2.connect(P02, branching)
        P02.connect(N02, -1.0)
        N02.connect(P02, 1.0/3.0)
        N02.connect(N2, 2.0/3.0)

        P2.connect(P03, branching)
        P03.connect(N03, -1.0)
        N03.connect(P03, 1.0/3.0)
        N03.connect(N2, 2.0/3.0)

        P2.connect(P04, branching)
        P04.connect(N04, -1.0)
        N04.connect(P04, 1.0/3.0)
        N04.connect(N2, 2.0/3.0)

        P2.connect(P05, branching)
        P05.connect(N05, -1.0)
        N05.connect(P05, 1.0/3.0)
        N05.connect(N2, 2.0/3.0)

        P2.connect(P3, branching)
        P3.connect(N3, 0)
        N3.connect(P3, 1.0/3.0)
        N3.connect(N2, 2.0/3.0)
        return [P1, N1, P2, N2, P3, N3, P01, N01, P02, N02, P03, N03, P04, N04, P05, N05]

    def test5():
        """Series two 50 ohms with four 50 ohms shunt in the middle."""
        P1 = Node('+1')
        N1 = Node('-1')
        P2 = Node('+2')
        N2 = Node('-2')
        P3 = Node('+3')
        N3 = Node('-3')
        P01 = Node('+01')
        N01 = Node('-01')
        P02 = Node('+02')
        N02 = Node('-02')
        P03 = Node('+03')
        N03 = Node('-03')
        P04 = Node('+04')
        N04 = Node('-04')

        branching = 2.0/11.0  
        P1.connect(N1, 1.0/3.0)
        P1.connect(P2, 2.0/3.0)
        N2.connect(P2, 1.0/3.0)
        N2.connect(N1, 2.0/3.0)
        N1.connect(P1, 0)
        P2.connect(N2, -3.0/11.0) ## shunting S11's
        
        P2.connect(P01, branching)
        P01.connect(N01, -1.0)
        N01.connect(P01, 1.0/3.0)
        N01.connect(N2, 2.0/3.0)

        P2.connect(P02, branching)
        P02.connect(N02, -1.0)
        N02.connect(P02, 1.0/3.0)
        N02.connect(N2, 2.0/3.0)

        P2.connect(P03, branching)
        P03.connect(N03, -1.0)
        N03.connect(P03, 1.0/3.0)
        N03.connect(N2, 2.0/3.0)

        P2.connect(P04, branching)
        P04.connect(N04, -1.0)
        N04.connect(P04, 1.0/3.0)
        N04.connect(N2, 2.0/3.0)

        P2.connect(P3, branching)
        P3.connect(N3, 0)
        N3.connect(P3, 1.0/3.0)
        N3.connect(N2, 2.0/3.0)
        return [P1, N1, P2, N2, P3, N3, P01, N01, P02, N02, P03, N03, P04, N04]

    def test4():
        """Series two 50 ohms with three 50 ohms shunt in the middle."""
        P1 = Node('+1')
        N1 = Node('-1')
        P2 = Node('+2')
        N2 = Node('-2')
        P3 = Node('+3')
        N3 = Node('-3')
        P01 = Node('+01')
        N01 = Node('-01')
        P02 = Node('+02')
        N02 = Node('-02')
        P03 = Node('+03')
        N03 = Node('-03')

        branching = 2.0/9.0  
        P1.connect(N1, 1.0/3.0)
        P1.connect(P2, 2.0/3.0)
        N2.connect(P2, 1.0/3.0)
        N2.connect(N1, 2.0/3.0)
        N1.connect(P1, 0)
        P2.connect(N2, -2.0/9.0) ## shunting S11's
        
        P2.connect(P01, branching)
        P01.connect(N01, -1.0)
        N01.connect(P01, 1.0/3.0)
        N01.connect(N2, 2.0/3.0)

        P2.connect(P02, branching)
        P02.connect(N02, -1.0)
        N02.connect(P02, 1.0/3.0)
        N02.connect(N2, 2.0/3.0)

        P2.connect(P03, branching)
        P03.connect(N03, -1.0)
        N03.connect(P03, 1.0/3.0)
        N03.connect(N2, 2.0/3.0)

        P2.connect(P3, branching)
        P3.connect(N3, 0)
        N3.connect(P3, 1.0/3.0)
        N3.connect(N2, 2.0/3.0)
        return [P1, N1, P2, N2, P3, N3, P01, N01, P02, N02, P03, N03]

    def test3():
        """Series two 50 ohms with two 50 ohms shunt in the middle."""
        P1 = Node('+1')
        N1 = Node('-1')
        P2 = Node('+2')
        N2 = Node('-2')
        P3 = Node('+3')
        N3 = Node('-3')
        P01 = Node('+01')
        N01 = Node('-01')
        P02 = Node('+02')
        N02 = Node('-02')

        branching = 2.0/7  ###0.285714285714
        P1.connect(N1, 1.0/3.0)
        P1.connect(P2, 2.0/3.0)
        N2.connect(P2, 1.0/3.0)
        N2.connect(N1, 2.0/3.0)
        N1.connect(P1, 0)
        P2.connect(N2, -1.0/7)##-0.142857142857)  ## shunting S11's
        
        P2.connect(P01, branching)
        P01.connect(N01, -1.0)
        N01.connect(P01, 1.0/3.0)
        N01.connect(N2, 2.0/3.0)

        P2.connect(P02, branching)
        P02.connect(N02, -1.0)
        N02.connect(P02, 1.0/3.0)
        N02.connect(N2, 2.0/3.0)

        P2.connect(P3, branching)
        P3.connect(N3, 0)
        N3.connect(P3, 1.0/3.0)
        N3.connect(N2, 2.0/3.0)
        return [P1, N1, P2, N2, P3, N3, P01, N01, P02, N02]

    def test2():
        """Series two 50 ohms."""
        P1 = Node('+1')
        N1 = Node('-1')
        P2 = Node('+2')
        N2 = Node('-2')
        P3 = Node('+3')
        N3 = Node('-3')
        P1.connect(N1, 1.0/3.0)
        P1.connect(P2, 2.0/3.0)
        N2.connect(P2, 1.0/3.0)
        N2.connect(N1, 2.0/3.0)
        N1.connect(P1, 0)
        P2.connect(N2, 1.0/3.0)
        P2.connect(P3, 2.0/3.0)
        N3.connect(P3, 1.0/3.0)
        N3.connect(N2, 2.0/3.0)
        P3.connect(N3, 0)
        return [P1, N1, P2, N2, P3, N3]


        
    def test1():
        """Series two 50 ohms and shunt one 50 ohm in the middle."""
        P1 = Node('+1')
        N1 = Node('-1')
        P2 = Node('+2')
        N2 = Node('-2')
        P21 = Node('+21')
        P22 = Node('+22')
        N21 = Node('-21')
        N22 = Node('-22')
        P3 = Node('+3')
        N3 = Node('-3')
        P0 = Node('+0')
        N0 = Node('-0')
        branching = 0.4
        P1.connect(N1, 1.0/3.0)
        P1.connect(P2, 2.0/3.0)
        N2.connect(P2, 1.0/3.0)
        N2.connect(N1, 2.0/3.0)        
        N1.connect(P1, 0) ## Source
        
        P22.connect(N22, 1.0/3.0)  
        P22.connect(P3, 2.0/3.0)
        N3.connect(P3, 1.0/3.0)
        N3.connect(N22, 2.0/3.0)
        P3.connect(N3, 0) ## Load        
        
        P21.connect(N21, 1.0/3.0)
        P21.connect(P0, 2.0/3.0)
        N0.connect(P0, 1.0/3.0)
        N0.connect(N21, 2.0/3.0)
        P0.connect(N0, -1.0) ## ground reflection

        ### Here is the T-junction network.
        P2.connect(N2, -1.0/3.0)
        P2.connect(P21, 2.0/3.0)
        N21.connect(P21, -1.0/3.0)
        N21.connect(N2, 2.0/3.0)
       
        P2.connect(P22, 2.0/3.0)
        N22.connect(N2, 2.0/3.0)
        N22.connect(P21, 2.0/3.0)
        N21.connect(P22, 2.0/3.0)
        
        N22.connect(P22, -1.0/3.0)
        N21.connect(P21, -1.0/3.0)
        
        return [P1, N1, P2, N2, P3, N3, P0, N0, P21, P22, N21, N22]

    noiter = 100
    nodes_set = test1()   #### Here is to change the test case.
    for each in nodes_set:
        each.newflow()     

    P1 = nodes_set[0]
    N1 = nodes_set[1]
    P3 = nodes_set[4]
    P1.en = 1.0
    P1._flow.send(1)
    P1.sf = 0.0

    ticks = []

    for each in range(noiter):  ## noiter: number of iteration
        for each_node in nodes_set:
            if each_node._tick:
                ticks.append(each_node)
#        print('Begin iter ' + str(each + 1), ticks)                    
        for each_tick in ticks:
#            print('-at iter ' + str(each + 1) + ' with node ', each_tick)
            each_tick.sequence = each + 1
            each_tick.tack()

        for each_tick in ticks:
            each_tick.sf = 0.0##Decimal(0)
        ticks = []
    print('a1', P1.en)
    print('b1', N1.en)
    print('b2', P3.en)
