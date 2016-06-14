## netlist.py

class Netlist(object):

    def __init__(self, inputfile):
        f = open(inputfile, 'r')
        alllines = f.readlines()

        self.netlist=[]  ## netlist is the initial extraction from the inputfile
        self.network={}  ## network representation in dictionary: {1:{'cnct':..;'elmt':..;'valu':..;}
        self.nodes=[]    ## list of (char) nodes, no duplication, thus the number of total nodes
        self.ports=[]    ## list of (int) test ports in the sequence of port1,2,3,..
        self.simpara={}  ## the simulation parameters
        self.ttlelmt = 0 ## total number of elements
        self.ttlnode = 0 ## total number of nodes
        self.ttlport = 0 ## total number of ports
        self._existing_gnd = False ## flag to check if there is node '0' in the schematic
        f.close()

        ## "netlist" extraction - each item in netlist, containing break-ups for each element
        for each in alllines:
            temp = each[:each.find('#')].split()  # Any comments or lines after '#' will be removed.
            if temp != []:
                self.netlist.append(temp)

        ## "netlist" error check
        self._NetlistCheck()  # placeholder, not completed for _NetlistCheck() yet

        ## A-"network" and B-"simpara" extractions
        noe=0  ## nth-element
        for each in self.netlist:
            if each[0][0] != '.':     ## part A - extraction of network
            ## The lines starting with "." for simulation setup are ingored in self.netlist.
                n = 0
                ## n is used to count the number of nodes.
                ## the counting is done via counting numerical digit
                for item in each[1:]: ##
                    if item.isdigit(): # Use isdigit() to count connected node (n) for each element.
                        n += 1
                    else:
                        break
                ## noe is the noe-th element
                noe += 1
                self.network[noe]={}

                self.network[noe]['cnct']=[int(k) for k in each[1:n+1]]         # cnct: element node connection
                self.network[noe]['elmt']=each[n+1].lower()   # elmt: element type, R, L, C and so on
                self.network[noe]['valu']=each[n+2]           # valu: element values
                self.network[noe]['labl']=each[0]             # labl: element lable

            elif each[0][0] == '.':  ## part B - extraction of simpara
                temptag = each[0][1:]
                if temptag.lower()!='end':
                    self.simpara[temptag] = each[1:]
            else:
                print("warning - netlist not recognized")

        ## totle elements - obtained by taking the last noe from the previous counting
        self.ttlelmt = noe
        ## total ports - obtained by len the first list of the self.simpara
        ## the first element of self.simpara always the sim type
        self.ttlport = len(self.simpara['Spara'])

        ## All nodes, such as 1,2,3....g, are  extracted from self.network['cnct']
        ## ,and then the duplicated ones are removed, only the distinct ones are kept.
        for each in self.network.values():
            for item in each['cnct']:
                duplicate = True
                ## checking if any explicit grounding port '0'
                if item == '0':
                    self._existing_gnd = True
                ## appending nodes if nodes list is empty
                if self.nodes==[]:
                    self.nodes.append(item)
                else:
                    duplicate = False
                ## appending nodes if item is not a duplicate
                for n in self.nodes:
                    if item==n:
                        duplicate = True
                        break
                if not duplicate:
                    self.nodes.append(item)

        self.ttlnode = len(self.nodes)


    def _NetlistCheck(self):
        pass


    def PrintNetlist(self):
        for each in self.netlist:
            print(each)
        print('\n')

    def PrintNetwork(self):
        if self._existing_gnd:
            print('\nThere are %d nodes, and ground node is explicitly included.'% self.ttlnode)
        else:
            print('\nThere are %d nodes, and ground node is not explicitly included.'% self.ttlnode)
        
        nodes = ""
        for each in self.nodes:
            nodes = nodes + " " + str(each)
        print("> node list: " + nodes + "\n")
        print('The netlist is composed of %d elements with %d test ports.'% (self.ttlelmt,self.ttlport))
        for each in self.network:
            component = self.network[each]
            valu = component['valu']
            ports = component['cnct']
            print('> element ' + str(each) + ': ' + component['elmt'] + ', value ' + valu + ', connects from p' + str(ports[0]) + ' to p' + str(ports[1]))


