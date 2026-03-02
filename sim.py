from math import log10
from decimal import *
import os
#getcontext().prec = 200
from cmath import phase
from cmath import pi
from node import Node
from schematic import *
import element
PIN = element.PIN
POUT = element.POUT
JCT = element.JCT
_elmt_class_map_ = element._elmt_class_map_
try:
    import fastflow
except ImportError:
    fastflow = None
try:
    import fastflow_numba
except ImportError:
    fastflow_numba = None
FASTFLOW_EXPERIMENTAL = os.environ.get('FLO_EXPERIMENTAL_FASTFLOW') == '1'


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
    for k, v in list(shunting_nodes.items()):
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


def _tarjan_scc(node_count, edges_by_from):
    index = 0
    stack = []
    onstack = [False] * node_count
    indices = [-1] * node_count
    lowlink = [0] * node_count
    scc_id = [-1] * node_count
    sccs = []

    def strongconnect(v):
        # Python 2 compatible closure state.
        pass

    state = {'index': index}

    def visit(v):
        indices[v] = state['index']
        lowlink[v] = state['index']
        state['index'] += 1
        stack.append(v)
        onstack[v] = True

        for w in edges_by_from[v]:
            if indices[w] == -1:
                visit(w)
                if lowlink[w] < lowlink[v]:
                    lowlink[v] = lowlink[w]
            elif onstack[w]:
                if indices[w] < lowlink[v]:
                    lowlink[v] = indices[w]

        if lowlink[v] == indices[v]:
            comp = []
            while True:
                w = stack.pop()
                onstack[w] = False
                scc_id[w] = len(sccs)
                comp.append(w)
                if w == v:
                    break
            sccs.append(comp)

    for v in range(node_count):
        if indices[v] == -1:
            visit(v)
    return scc_id, sccs


def _forward_reachable(start_idx, edges_by_from):
    seen = set([start_idx])
    stack = [start_idx]
    while stack:
        node = stack.pop()
        for nxt in edges_by_from[node]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def _reverse_reachable(target_idxs, rev_edges_by_to):
    seen = set(target_idxs)
    stack = list(target_idxs)
    while stack:
        node = stack.pop()
        for prv in rev_edges_by_to[node]:
            if prv not in seen:
                seen.add(prv)
                stack.append(prv)
    return seen


def _with_graph_meta(stats, model):
    stats['orig_nodes'] = model['orig_nodes']
    stats['orig_edges'] = model['orig_edges']
    stats['reduced_nodes'] = model['reduced_nodes']
    stats['reduced_edges'] = model['reduced_edges']
    stats['scc_count'] = model['scc_count']
    stats['cyclic_scc_count'] = model['cyclic_scc_count']
    stats['cyclic_nodes'] = model['cyclic_nodes']
    return stats


def build_static_model(circuit_pipe, input_port, output_ports):
    """Build reduced static graph topology and per-edge descriptors once per circuit."""
    descriptors = []
    node_set = set()

    for elmt in circuit_pipe:
        elmt.makeFlow()
        for n in elmt.node_nos:
            node_set.add(n)

    for elmt in circuit_pipe:
        name = elmt.name[0]
        for k, v in elmt._flow_map.items():
            from_name = k[0]
            to_name = k[1]
            if name in ('P', 'J'):
                descriptors.append((from_name, to_name, 'const', elmt.__dict__['S' + v], None))
            else:
                descriptors.append((from_name, to_name, 'dynamic', elmt, v))

            gnd_n = int(k[0])
            gnd_p = int(k[1])
            if gnd_n > -1000 and gnd_n < -900 and gnd_p > 900 and gnd_p < 1000 and abs(gnd_n) == abs(gnd_p):
                descriptors.append((to_name, from_name, 'const', -1.0, None))

    full_nodes = sorted(list(node_set))
    full_index = {}
    for i, name in enumerate(full_nodes):
        full_index[name] = i

    edges_by_from_full = [[] for _ in range(len(full_nodes))]
    rev_edges_by_to_full = [[] for _ in range(len(full_nodes))]
    for item in descriptors:
        from_idx = full_index[item[0]]
        to_idx = full_index[item[1]]
        edges_by_from_full[from_idx].append(to_idx)
        rev_edges_by_to_full[to_idx].append(from_idx)

    src_name = '+' + str(input_port)
    out_names = ['+' + str(each) for each in output_ports]
    pin_neg_name = '-' + str(input_port)
    target_names = [pin_neg_name] + out_names

    src_idx_full = full_index[src_name]
    target_idxs_full = [full_index[name] for name in target_names]
    fwd = _forward_reachable(src_idx_full, edges_by_from_full)
    bwd = _reverse_reachable(target_idxs_full, rev_edges_by_to_full)
    keep_full = fwd.intersection(bwd)
    keep_full.add(src_idx_full)
    for each in target_idxs_full:
        keep_full.add(each)

    kept_nodes = [full_nodes[i] for i in sorted(list(keep_full))]
    node_index = {}
    for i, name in enumerate(kept_nodes):
        node_index[name] = i

    kept_desc = []
    for item in descriptors:
        if item[0] in node_index and item[1] in node_index:
            kept_desc.append(item)

    edge_desc_by_from = [[] for _ in range(len(kept_nodes))]
    edges_by_from_reduced = [[] for _ in range(len(kept_nodes))]
    has_self_loop = [False] * len(kept_nodes)
    for item in kept_desc:
        from_idx = node_index[item[0]]
        to_idx = node_index[item[1]]
        edge_desc_by_from[from_idx].append((to_idx, item[2], item[3], item[4]))
        edges_by_from_reduced[from_idx].append(to_idx)
        if from_idx == to_idx:
            has_self_loop[from_idx] = True

    scc_id, sccs = _tarjan_scc(len(kept_nodes), edges_by_from_reduced)
    cyclic_scc_count = 0
    cyclic_nodes = 0
    for comp in sccs:
        comp_is_cyclic = len(comp) > 1
        if not comp_is_cyclic and has_self_loop[comp[0]]:
            comp_is_cyclic = True
        if comp_is_cyclic:
            cyclic_scc_count += 1
            cyclic_nodes += len(comp)

    model = {
        'nodes': kept_nodes,
        'node_index': node_index,
        'edge_desc_by_from': edge_desc_by_from,
        'source_idx': node_index[src_name],
        'pin_neg_idx': node_index[pin_neg_name],
        'output_idxs': [node_index[name] for name in out_names],
        'orig_nodes': len(full_nodes),
        'orig_edges': len(descriptors),
        'reduced_nodes': len(kept_nodes),
        'reduced_edges': len(kept_desc),
        'scc_count': len(sccs),
        'cyclic_scc_count': cyclic_scc_count,
        'cyclic_nodes': cyclic_nodes,
    }
    return model


def sim_Sij_static(model, frequency, noiter = 40, converge = False, tol = 1e-6,
                   min_iter = 5, patience = 3, max_iter = None, return_stats = False,
                   check_every = 8, stagnation_checks = 4, stagnation_ratio = 0.995,
                   max_checks = 64, use_fastflow = False, use_numba = False):
    """Simulate using precomputed reduced topology and per-frequency edge weights."""
    n_nodes = len(model['nodes'])
    edge_offsets = [0]
    edge_to = []
    edge_w = []
    out_edges = [[] for _ in range(n_nodes)]
    for from_idx in range(n_nodes):
        for item in model['edge_desc_by_from'][from_idx]:
            to_idx = item[0]
            etype = item[1]
            if etype == 'const':
                weight = item[2]
            else:
                weight = item[2]._S(item[3], frequency)
            out_edges[from_idx].append((to_idx, weight))
            edge_to.append(to_idx)
            edge_w.append(weight)
        edge_offsets.append(len(edge_to))

    source_idx = model['source_idx']
    pin_neg_idx = model['pin_neg_idx']
    output_idxs = model['output_idxs']
    iter_limit = noiter if max_iter is None else max_iter

    if use_numba and fastflow_numba is not None and getattr(fastflow_numba, 'AVAILABLE', False):
        b1, insersions, stats = fastflow_numba.propagate_csr(
            edge_offsets, edge_to, edge_w,
            int(source_idx), int(pin_neg_idx), output_idxs,
            int(iter_limit), bool(converge), float(tol),
            int(min_iter), int(patience), int(check_every),
            int(stagnation_checks), float(stagnation_ratio), max_checks
        )
        if return_stats:
            return b1, insersions, _with_graph_meta(stats, model)
        return b1, insersions

    if use_fastflow and fastflow is not None and FASTFLOW_EXPERIMENTAL:
        c_max_checks = -1 if max_checks is None else int(max_checks)
        b1, insersions, stats = fastflow.propagate_csr(
            edge_offsets, edge_to, edge_w,
            int(source_idx), int(pin_neg_idx), output_idxs,
            int(iter_limit), int(bool(converge)), float(tol),
            int(min_iter), int(patience), int(check_every),
            int(stagnation_checks), float(stagnation_ratio), int(c_max_checks)
        )
        if return_stats:
            return b1, insersions, _with_graph_meta(stats, model)
        return b1, insersions

    en = [0.0] * n_nodes
    sf = [0.0] * n_nodes
    tick = [False] * n_nodes

    en[source_idx] = 1.0
    for edge in out_edges[source_idx]:
        to_idx = edge[0]
        val = 1.0 * edge[1]
        sf[to_idx] = sf[to_idx] + val
        en[to_idx] = en[to_idx] + val
        tick[to_idx] = True

    stable_count = 0
    converged = False
    iters_used = 0
    final_max_delta_en = None
    check_count = 0
    stagnated = False
    mode_used = 'baseline'
    convergence_active = bool(converge)
    prev_check_delta = None
    stagnation_count = 0
    last_checked_en = [0.0] * n_nodes
    if convergence_active:
        mode_used = 'convergence'
        if check_every < 1:
            check_every = 1
        for i in range(n_nodes):
            last_checked_en[i] = en[i]

    for each in range(iter_limit):
        ticks = []
        for i in range(n_nodes):
            if tick[i]:
                ticks.append(i)

        if len(ticks) == 0:
            mode_used = 'quiescent'
            break

        for i in ticks:
            incoming = sf[i]
            for edge in out_edges[i]:
                to_idx = edge[0]
                val = incoming * edge[1]
                sf[to_idx] = sf[to_idx] + val
                en[to_idx] = en[to_idx] + val
                tick[to_idx] = True
            tick[i] = False

        for i in ticks:
            sf[i] = 0.0

        iters_used = each + 1
        if convergence_active and iters_used >= min_iter and iters_used % check_every == 0:
            check_count += 1
            max_delta_en = 0.0
            for i in range(n_nodes):
                delta_en = abs(en[i] - last_checked_en[i])
                if delta_en > max_delta_en:
                    max_delta_en = delta_en
                last_checked_en[i] = en[i]
            final_max_delta_en = max_delta_en

            if max_delta_en < tol:
                stable_count += 1
            else:
                stable_count = 0
            if stable_count >= patience:
                converged = True
                mode_used = 'converged'
                break

            if prev_check_delta is not None:
                if max_delta_en >= prev_check_delta * stagnation_ratio:
                    stagnation_count += 1
                else:
                    stagnation_count = 0
            prev_check_delta = max_delta_en
            if stagnation_count >= stagnation_checks:
                stagnated = True
                convergence_active = False
                mode_used = 'fallback_baseline'
            if convergence_active and max_checks is not None and check_count >= max_checks:
                convergence_active = False
                mode_used = 'fallback_baseline'

    b1 = en[pin_neg_idx]
    insersions = [en[idx] for idx in output_idxs]

    if return_stats:
        if mode_used == 'convergence' and not converged:
            mode_used = 'max_iter'
        stats = {
            'iters_used': iters_used,
            'converged': converged,
            'final_max_delta_en': final_max_delta_en,
            'check_count': check_count,
            'stagnated': stagnated,
            'mode_used': mode_used
        }
        return b1, insersions, _with_graph_meta(stats, model)
    return b1, insersions


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


def sim_Sij(graph, input_port, output_ports, noiter = 40, gammaS = 0.0, gammaL = 0.0,
            converge = False, tol = 1e-6, min_iter = 5, patience = 3,
            max_iter = None, return_stats = False, check_every = 8,
            stagnation_checks = 4, stagnation_ratio = 0.995,
            max_checks = 64):
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
    iter_limit = noiter if max_iter is None else max_iter
    stable_count = 0
    converged = False
    iters_used = 0
    final_max_delta_en = None
    check_count = 0
    stagnated = False
    mode_used = 'baseline'
    convergence_active = bool(converge)
    prev_check_delta = None
    stagnation_count = 0
    last_checked_en = {}
    if convergence_active:
        mode_used = 'convergence'
        if check_every < 1:
            check_every = 1
        for node_name, node_obj in this_graph.items():
            last_checked_en[node_name] = node_obj.en
    ticks = []
    for each in range(iter_limit):  ## noiter: number of iteration
        for node_name, node_obj in this_graph.items():
            if node_obj._tick:
                ticks.append(node_obj)

        if len(ticks) == 0:
            mode_used = 'quiescent'
            break

        for each_tick in ticks:
            each_tick.sequence = each + 1
            each_tick.tack()
                
        for each_tick in ticks:
            each_tick.sf = 0.0##Decimal(0)
        ticks = []

        iters_used = each + 1
        if convergence_active and iters_used >= min_iter and iters_used % check_every == 0:
            check_count += 1
            max_delta_en = 0.0
            for node_name, node_obj in this_graph.items():
                delta_en = abs(node_obj.en - last_checked_en[node_name])
                if delta_en > max_delta_en:
                    max_delta_en = delta_en
                last_checked_en[node_name] = node_obj.en
            final_max_delta_en = max_delta_en

            if max_delta_en < tol:
                stable_count += 1
            else:
                stable_count = 0
            if stable_count >= patience:
                converged = True
                mode_used = 'converged'
                break

            if prev_check_delta is not None:
                if max_delta_en >= prev_check_delta * stagnation_ratio:
                    stagnation_count += 1
                else:
                    stagnation_count = 0
            prev_check_delta = max_delta_en
            if stagnation_count >= stagnation_checks:
                stagnated = True
                convergence_active = False
                mode_used = 'fallback_baseline'
            if convergence_active and max_checks is not None and check_count >= max_checks:
                convergence_active = False
                mode_used = 'fallback_baseline'

    a1 = pin.en
    b1 = pin_neg.en
    insersions = [each.en for each in pouts]
    
    ##5. reset nodes
    for node_name, node_obj in this_graph.items():
        node_obj.reset()
#    print(a1, b1, insersions)
    if return_stats:
        if mode_used == 'convergence' and not converged:
            mode_used = 'max_iter'
        stats = {
            'iters_used': iters_used,
            'converged': converged,
            'final_max_delta_en': final_max_delta_en,
            'check_count': check_count,
            'stagnated': stagnated,
            'mode_used': mode_used
        }
        return b1, insersions, stats
    return b1, insersions


def run(inputfile = './sim_files/lpf.sim', converge = False, tol = 1e-6,
        min_iter = 5, patience = 3, max_iter = None, write_outputs = True,
        print_network = True, check_every = 8, stagnation_checks = 4,
        stagnation_ratio = 0.995, max_checks = 64,
        auto_disable_convergence = True, pilot_points = 40,
        min_converged_ratio = 0.2, use_fastflow = False, use_numba = False):
    a_netlist = netlist.Netlist(inputfile)
    if print_network:
        a_netlist.PrintNetwork()
    test_ports = extract_ports(a_netlist.simpara)
    f_list = extract_freq(a_netlist.simpara)

    ## forwarding simulation
    a_circuit = circuit_generator(a_netlist.network, in_port = test_ports[0], out_ports = test_ports[1:])
    circuit_reflow(a_circuit, in_port = 801)
    circuit_junctioning(a_circuit)
    a_ensemble = ensemble_generator(a_circuit)
    a_model = build_static_model(a_circuit, input_port = 801, output_ports = [802,])
    
    Spara = []
    for_plotting = []
    points = []
    forward_stats = []
    reverse_stats = []
    forward_converge = bool(converge)
    forward_pilot_total = 0
    forward_pilot_converged = 0
    for freq in f_list:
        refl, ford, stats = sim_Sij_static(
            a_model,
            frequency = freq,
            noiter = 250 * len(a_ensemble),
            converge = forward_converge,
            tol = tol,
            min_iter = min_iter,
            patience = patience,
            max_iter = max_iter,
            check_every = check_every,
            stagnation_checks = stagnation_checks,
            stagnation_ratio = stagnation_ratio,
            max_checks = max_checks,
            use_fastflow = use_fastflow,
            use_numba = use_numba,
            return_stats = True
        )
        forward_stats.append(stats)
        if forward_converge:
            forward_pilot_total += 1
            if stats['converged']:
                forward_pilot_converged += 1
            if auto_disable_convergence and forward_pilot_total >= pilot_points:
                converged_ratio = float(forward_pilot_converged) / float(forward_pilot_total)
                if converged_ratio < min_converged_ratio:
                    forward_converge = False
        freq_txt = "{:.9f}".format(freq) + "\t"
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
        Spara.append(freq_txt + S11 + S21)
        for_plotting.append(freq_txt + S11_dB + S21_dB)
        points.append({
            'freq': float(freq),
            'S11': refl,
            'S21': ford[0]
        })

    ## reversing simulation
    b_circuit = circuit_generator(a_netlist.network, in_port = test_ports[0], out_ports = test_ports[1:])
    circuit_reflow(b_circuit, in_port = 802)        
    circuit_junctioning(b_circuit)
    b_ensemble = ensemble_generator(b_circuit)
    b_model = build_static_model(b_circuit, input_port = 802, output_ports = [801,])
    n = 0
    reverse_converge = bool(converge)
    reverse_pilot_total = 0
    reverse_pilot_converged = 0
    for freq in f_list:
        refl, revs, stats = sim_Sij_static(
            b_model,
            frequency = freq,
            noiter = 250 * len(b_ensemble),
            converge = reverse_converge,
            tol = tol,
            min_iter = min_iter,
            patience = patience,
            max_iter = max_iter,
            check_every = check_every,
            stagnation_checks = stagnation_checks,
            stagnation_ratio = stagnation_ratio,
            max_checks = max_checks,
            use_fastflow = use_fastflow,
            use_numba = use_numba,
            return_stats = True
        )
        reverse_stats.append(stats)
        if reverse_converge:
            reverse_pilot_total += 1
            if stats['converged']:
                reverse_pilot_converged += 1
            if auto_disable_convergence and reverse_pilot_total >= pilot_points:
                converged_ratio = float(reverse_pilot_converged) / float(reverse_pilot_total)
                if converged_ratio < min_converged_ratio:
                    reverse_converge = False
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
        for_plotting[n] += S12_and_S22_dB
        points[n]['S12'] = revs[0]
        points[n]['S22'] = refl
        n += 1

    output_s2p = inputfile[:inputfile[1:].find(".") + 1] + ".s" + str(len(test_ports)) + "p"
    output_plt = inputfile[:inputfile[1:].find(".") + 1] + ".plt"
    if write_outputs:
        fp = open(output_s2p, 'w')
        fp.write("# GHZ S MA R 50\n")
        for each in Spara:
            fp.write(each+ "\n")
        fp.close()

        fp = open(output_plt, 'w')
        for each in for_plotting:
            fp.write(each + "\n")
        fp.close()
        print("Simulation done! " + output_plt + " generated.")

    result = {
        'inputfile': inputfile,
        'points': points,
        'spara_lines': Spara,
        'plot_lines': for_plotting,
        'output_s2p': output_s2p,
        'output_plt': output_plt,
        'forward_stats': forward_stats,
        'reverse_stats': reverse_stats
    }
    return result


if __name__ == '__main__':
    import sys
    from os import listdir
    from os.path import isfile, join
    onlyfiles = [f for f in listdir("./sim_files/") if isfile(join("./sim_files/", f))]
    print("\n")

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
