from math import log10
from decimal import *
#getcontext().prec = 200
from node import Node
from schematic import *
import element
PIN = element.PIN
POUT = element.POUT
JCT = element.JCT
_elmt_class_map_ = element._elmt_class_map_


### 
#  circuit_generator --> circuit_reflow --> ensemble_generator --> graphs_of_all_freqs(graph_generator)
#
#  circuit_generator - making circuit that is composed of elements
#     input:  network_dict, which can be network dict from netlist module.
#     output: circuit pipe, which is a list of elements (from element module)
#
#  circuit_reflow - reflowing the circuit based on the given test ports
#     input: circuit pipe from circuit_generator
#     output:  the same circuit pipe but after being reflowed
#
#  circuit_junctioning - adding idea T-junction and normalizing port numbers to the give circuit from circuit_flow
#     input: circuit pipe from circuit_reflow
#     output: the same circuit pipe after being junctioned
#
#  ensemble_generator - making emsemble of nodes
#     input:  circuit pipe from above
#     output: nodes (ensemble), which is a dict of all the requried nodes
#
#  graph_geneartor - connecting the nodes obtained from 'ensemble generator'
#     input:  nodes from above
#     output: same nodes but being wired with assigned coefficients
###

def circuit_generator(network_dict, in_port, out_ports):
    """Input network dictionary from netlist class to generate circuit with element objects instantiated."""
    circuit_pipe = []
    for k, v in network_dict.items():
        element_class = _elmt_class_map_[v['elmt'].lower()]
        label = v['labl']
        value = float(v['valu'])
        ports = v['cnct']
        element = element_class(label, value, ports)
        circuit_pipe.append(element)

    ## append input port
    circuit_pipe.append(PIN('PIN' + str(in_port), 50.0, [801, in_port]))
    ## append output ports
    nofout = 2
    for each in out_ports:
        circuit_pipe.append(POUT('POUT' + str(nofout), 50.0, [each, 800 + nofout]))
        nofout += 1

    return circuit_pipe


def circuit_reflow(circuit_pipe, in_port):
    the_same_pipe = list(circuit_pipe)
    ## the reason to duplicate the same 'circuit pipe' is to run through and modify its elements, while
    ## keeping the original pipe
    leading_ports = [in_port, ]
    while leading_ports != []:
        leading = leading_ports.pop()
        found_tailing = True
        the_1st_tail = None
        while found_tailing:
            nol = 0  ## number of leading ports
            to_remove = []
            for each_circuit in the_same_pipe:
                p = each_circuit.ports
                if 0 in p:
                    if p[0] == 0 and len(p) == 2:
                        each_circuit.reFlow()
                        to_remove.append(each_circuit)
                    elif p[0] == 0 and len(p) > 2:
                        each_circuit.reFlow()
                    elif p[1] == 0 and len(p) == 2:
                        to_remove.append(each_circuit)
            for each in to_remove:
                the_same_pipe.remove(each)
                
            to_remove = []
            for each_circuit in the_same_pipe:
                if leading in each_circuit.ports:
                    nol += 1
                    to_remove.append(each_circuit)
                    if leading != each_circuit.ports[0]:
                        tailing_port = each_circuit.ports[0]
                        each_circuit.reFlow(leading)
                        ## rerun the flow if the leading port is not at the leading position
                    else:
                        tailing_port = each_circuit.ports[1]
                    if nol == 1:
                        the_1st_tail = tailing_port
                    else:
                    ## nol > 1: means there are shunting nodes, which are put into the list of 'leading ports'
                        leading_ports.append(tailing_port)
            if nol == 0:   ## end of the trail
                found_tailing = False
            leading = the_1st_tail
            for each in to_remove:
                the_same_pipe.remove(each)


def circuit_junctioning(circuit_pipe):
    """Adding ideal shunting junction and normalizing port number accoring to ports.definition."""
    ## Sequence the numbering of the grounding ports.
    g = 1
    for elmt in circuit_pipe:
        k = 1
        for n in elmt.ports[1:]:
            if n == 0:
                elmt.ports[k] = 900 + g
                g += 1
                break
            else:
                k += 1

    ## Fitch shunting ports
    shunting_nodes = {}
    nog = 0 ## number of grounding ports
    for elmt in circuit_pipe:
        for n in elmt.ports[1:]:
            if n != 0:
                shunting_nodes[n] = []
            else:
                nog += 1
    for n in shunting_nodes:
        for each in circuit_pipe:
            if each.ports[0] == n:
                shunting_nodes[n].append(each.ports[-1])
    for k, v in shunting_nodes.items():
        if len(v) < 2:
            del shunting_nodes[k]
                
    ## Match the leading shunt port to the element port, then normalize port number to 'ports.defition'.
    for n in shunting_nodes:
        for elmt in circuit_pipe:
            k = 1
            for each in elmt.ports[1:]:
                if n == each:
                    elmt.ports[k] = n + 900000
                    elmt.updatePorts()
                    break
                else:
                    k += 1
                    
    ## Match the tailing shunt port to the element port, then normalize port number.
    for k, v in shunting_nodes.items():
        for n in v:
            for elmt in circuit_pipe:
                p = [ elmt.ports[0], elmt.ports[-1] % 900000]
                if [k, n] == p:
                    elmt.ports[0] = p[0]*1000 + p[1]
                    elmt.updatePorts()
                    break
    ## Add ideal T junctions
    for k, v in shunting_nodes.items():
        n = len(v) + 1
        ports = [ 900000 + k, ]
        name = str(k)
        for n in v:
            ports.append(k*1000 + n)
            name += str(n)
        circuit_pipe.append(JCT('JCT' + name, None, ports))

    
def ensemble_generator(circuit_pipe):
    """Generate the dictionary of the ensemble of nodes."""
    ensemble_nodes = {}
    for elmt in circuit_pipe:
        for each in elmt.node_nos:
            node_name = each
            ensemble_nodes[node_name] = Node(node_name)
    return ensemble_nodes


def graph_generator(circuit_pipe, ensemble_nodes, frequency):
    """Making graph connections."""
    for elmt in circuit_pipe:
        elmt.makeFlow()
    connections = {}
    for elmt in circuit_pipe:                ## 3 --- Connect all the nodes.
        name = elmt.name[0]
        for k, v in elmt._flow_map.items():
            if name in ('P', 'J'):
                Spara = elmt.__dict__['S' + v]
            else:
                Spara = elmt._S(v, frequency)

            from_port = k[0]
            to_port = k[1]
            ports_tuple = (k[0], k[1])
            connections[ports_tuple] = Spara
            ensemble_nodes[from_port].connect(ensemble_nodes[to_port], connections[ports_tuple])
            ## Shorting ground with -1 reflection coef.
            gnd_n = int(k[0])
            gnd_p = int(k[1])
            if gnd_n > -1000 and gnd_n < -900 and gnd_p > 900 and gnd_p < 1000 and abs(gnd_n) == abs(gnd_p):
                ensemble_nodes[k[1]].connect(ensemble_nodes[k[0]], -1.0)
    return ensemble_nodes


def graphs_of_all_freqs(a_circuit, a_ensemble, f_list, test_ports = None):
    graphs = {}
    for each in f_list:
        graphs[each] = graph_generator(a_circuit, a_ensemble, each)
    return graphs


def extract_freq(simpara):
    f = simpara['Freq']
    f_list = []
    if len(f) !=3:
        print("Frequency inputs are incorrect!")
        exit()
    else:
        start = Decimal(f[0][:-1]).quantize(Decimal('1.000000000'))
        ## Currently, only deal with frequencies given in G (GHz)
        stop = Decimal(f[1][:-1]).quantize(Decimal('1.000000000'))
        step = Decimal(f[2][:-1]).quantize(Decimal('1.000000000'))
        f_list.append(start)
        for each in range(int((stop-start)/step)):
            f_list.append(f_list[-1] + step)
        if f_list[-1] < stop:
            f_list.append(stop)
    return f_list#[float(each) for each in f_list]


def extract_ports(simpara):
    p = simpara['Spara']
    return [int(each) for each in p]


def sim_Sij(graph, input_port, output_ports, noiter = 40, gammaS = 0.0, gammaL = 0.0):
    """Simulate S21/S11 (Sij assigned as 'S21') or S12/S22 (Sij assigned as 'S12')."""
    this_graph = graph
    pin = this_graph['+' + str(input_port)]
    pouts = [this_graph['+' + str(each)] for each in output_ports]
    pin_neg = this_graph['-' + str(input_port)]

    for node_name, node_obj in this_graph.items():
    ##2. for each graph (per frequency), initialize the flows (newflow)
        node_obj.newflow()

    ##3. kick in the input
    pin.en = 1.0
    pin._flow.send(1.0)
    pin.sf = 0.0

    ##4. flowing through the graph by tick-tacking
    ticks = []
    for each in range(noiter):  ## noiter: number of iteration
        for node_name, node_obj in this_graph.items():
            if node_obj._tick:
                ticks.append(node_obj)

        for each_tick in ticks:
            each_tick.sequence = each + 1
            each_tick.tack()
                
        for each_tick in ticks:
            each_tick.sf = 0.0##Decimal(0)
        ticks = []

    a1 = pin.en
    b1 = pin_neg.en
    insersions = [each.en for each in pouts]
    
    ##5. reset nodes
    for node_name, node_obj in this_graph.items():
        node_obj.reset()
#    print(a1, b1, insersions)
    return b1, insersions
        


if __name__ == '__main__':
    import sys
    from os import listdir
    from os.path import isfile, join
    from cmath import phase
    from cmath import pi
    onlyfiles = [f for f in listdir("./sim_files/") if isfile(join("./sim_files/", f))]
    print("\n")
    def run(inputfile = './sim_files/lpf.sim'):
        a_netlist = netlist.Netlist(inputfile)
        a_netlist.PrintNetwork()
        test_ports = extract_ports(a_netlist.simpara)
        f_list = extract_freq(a_netlist.simpara)

        ## forwarding simulation
        a_circuit = circuit_generator(a_netlist.network, in_port = test_ports[0], out_ports = test_ports[1:])
        circuit_reflow(a_circuit, in_port = 801)
        circuit_junctioning(a_circuit)
        a_ensemble = ensemble_generator(a_circuit)
        
        Spara = []
        for_plotting = []
        for freq in f_list:
            graph = graph_generator(a_circuit, a_ensemble, freq)
            refl, ford = sim_Sij(graph, input_port = 801, output_ports = [802,], noiter = 250*len(a_ensemble))
            freq = "{:.9f}".format(freq) + "\t"
            S11 = "{:.10f}".format(abs(refl)) + "\t" + "{:.8f}".format(phase(refl)/pi*180) + "\t"
            if abs(refl) == 0:
                S11_dB = "-100.00"
            else:
                S11_dB = "{:.2f}".format(20*log10(abs(refl))) + "\t"
            S21 = "{:.10f}".format(abs(ford[0])) + "\t" + "{:.8f}".format(phase(ford[0])/pi*180) + "\t"
            if abs(ford[0]) == 0:
                S21_dB = "-100.00"
            else:
                S21_dB = "{:.2f}".format(20*log10(abs(ford[0]))) + "\t"
            Spara.append(freq + S11 + S21)
            for_plotting.append(freq + S11_dB + S21_dB)


        ## reversing simulation
        b_circuit = circuit_generator(a_netlist.network, in_port = test_ports[0], out_ports = test_ports[1:])
        circuit_reflow(b_circuit, in_port = 802)        
        circuit_junctioning(b_circuit)
        b_ensemble = ensemble_generator(b_circuit)
        n = 0
        for freq in f_list:
            graph = graph_generator(b_circuit, b_ensemble, freq)
            refl, revs = sim_Sij(graph, input_port = 802, output_ports = [801,], noiter = 250*len(b_ensemble))
            S12 = "{:.10f}".format(abs(revs[0])) + "\t" + "{:.8f}".format(phase(revs[0])/pi*180) + "\t"
            if abs(revs[0]) == 0:
                S12_dB = "-100.00"
            else:
                S12_dB = "{:.2f}".format(20*log10(abs(revs[0]))) + "\t"
            S22 = "{:.10f}".format(abs(refl)) + "\t" + "{:.8f}".format(phase(refl)/pi*180)

            if abs(refl) == 0:
                S22_dB = "-100.00"
            else:
                S22_dB = "{:.2f}".format(20*log10(abs(refl)))
            S12_and_S22 = S12 + S22
            S12_and_S22_dB = S12_dB + S22_dB
            Spara[n] += S12_and_S22
            for_plotting[n] += S12_dB + S22_dB
            n += 1

        outputfile = inputfile[:inputfile[1:].find(".") + 1] + ".s" + str(len(test_ports)) + "p"
        fp = open(outputfile, 'w')
        fp.write("# GHZ S MA R 50\n")
        for each in Spara:
            fp.write(each+ "\n")
        fp.close()

        outputfile = inputfile[:inputfile[1:].find(".") + 1] + ".plt"
        fp = open(outputfile, 'w')
        for each in for_plotting:
            fp.write(each + "\n")
        fp.close()
        print("Simulation done! " + outputfile + " generated.")             

    if len(sys.argv) == 2:
        filename = sys.argv[1]
        if filename in onlyfiles:
            print("\nRunning simulation file: {0}\n".format(filename))
            run("./sim_files/" + filename)
        else:
            print('Input file ' + "'" + filename + "'" + ' does not exist!\n')
        
    elif len(sys.argv) == 1:
        print("\nNo input file given.  Running demo mode on a low pass filter.\n")
        run()

    else:
        print("\nInput syntax error!")
        print("\nRunning simulation file:")
        print("  >python sim.py netlist.txt\n")
        print("\nRunning demo mode:")
        print("  >python sim.py ## no input file\n")
