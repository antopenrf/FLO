import argparse
import time
from cmath import phase
from math import pi

import sim


def _now():
    try:
        return time.perf_counter()
    except AttributeError:
        return time.time()


def _median(values):
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _phase_deg(value):
    return phase(value) / pi * 180.0


def _phase_diff_deg(a_deg, b_deg):
    diff = a_deg - b_deg
    while diff > 180.0:
        diff -= 360.0
    while diff < -180.0:
        diff += 360.0
    return abs(diff)


def _summarize_iteration_stats(result):
    stats = result['forward_stats'] + result['reverse_stats']
    iter_total = sum([s['iters_used'] for s in stats])
    converged_count = sum([1 for s in stats if s['converged']])
    stagnated_count = sum([1 for s in stats if s.get('stagnated')])
    quiescent_count = sum([1 for s in stats if s.get('mode_used') == 'quiescent'])
    fallback_count = sum([1 for s in stats if s.get('mode_used') == 'fallback_baseline'])
    final_deltas = [s['final_max_delta_en'] for s in stats if s['final_max_delta_en'] is not None]
    max_delta = max(final_deltas) if final_deltas else None
    check_total = sum([s.get('check_count', 0) for s in stats])
    graph_meta = None
    if len(stats) > 0:
        sample = stats[0]
        if 'orig_nodes' in sample:
            graph_meta = {
                'orig_nodes': sample['orig_nodes'],
                'orig_edges': sample['orig_edges'],
                'reduced_nodes': sample['reduced_nodes'],
                'reduced_edges': sample['reduced_edges'],
                'scc_count': sample['scc_count'],
                'cyclic_scc_count': sample['cyclic_scc_count'],
                'cyclic_nodes': sample['cyclic_nodes']
            }
    return iter_total, converged_count, len(stats), max_delta, check_total, stagnated_count, quiescent_count, fallback_count, graph_meta


def run_case(sim_file, converge, tol, min_iter, patience, max_iter, repeats, warmup,
             check_every, stagnation_checks, stagnation_ratio, max_checks,
             auto_disable_convergence, pilot_points, min_converged_ratio, use_fastflow, use_numba):
    durations = []
    iter_totals = []
    converged_ratios = []
    max_deltas = []
    check_totals = []
    stagnated_ratios = []
    quiescent_ratios = []
    fallback_ratios = []
    graph_meta = None
    last_result = None

    for _ in range(warmup):
        sim.run(
            inputfile=sim_file,
            converge=converge,
            tol=tol,
            min_iter=min_iter,
            patience=patience,
            max_iter=max_iter,
            check_every=check_every,
            stagnation_checks=stagnation_checks,
            stagnation_ratio=stagnation_ratio,
            max_checks=max_checks,
            auto_disable_convergence=auto_disable_convergence,
            pilot_points=pilot_points,
            min_converged_ratio=min_converged_ratio,
            use_fastflow=use_fastflow,
            use_numba=use_numba,
            write_outputs=False,
            print_network=False
        )

    for _ in range(repeats):
        t0 = _now()
        result = sim.run(
            inputfile=sim_file,
            converge=converge,
            tol=tol,
            min_iter=min_iter,
            patience=patience,
            max_iter=max_iter,
            check_every=check_every,
            stagnation_checks=stagnation_checks,
            stagnation_ratio=stagnation_ratio,
            max_checks=max_checks,
            auto_disable_convergence=auto_disable_convergence,
            pilot_points=pilot_points,
            min_converged_ratio=min_converged_ratio,
            use_fastflow=use_fastflow,
            use_numba=use_numba,
            write_outputs=False,
            print_network=False
        )
        t1 = _now()
        durations.append(t1 - t0)

        iter_total, converged_count, nstats, max_delta, check_total, stagnated_count, quiescent_count, fallback_count, meta = _summarize_iteration_stats(result)
        iter_totals.append(iter_total)
        check_totals.append(check_total)
        if nstats > 0:
            converged_ratios.append(float(converged_count) / float(nstats))
            stagnated_ratios.append(float(stagnated_count) / float(nstats))
            quiescent_ratios.append(float(quiescent_count) / float(nstats))
            fallback_ratios.append(float(fallback_count) / float(nstats))
        else:
            converged_ratios.append(0.0)
            stagnated_ratios.append(0.0)
            quiescent_ratios.append(0.0)
            fallback_ratios.append(0.0)
        if max_delta is not None:
            max_deltas.append(max_delta)
        if graph_meta is None and meta is not None:
            graph_meta = meta
        last_result = result

    return {
        'median_time_s': _median(durations),
        'median_iters': int(_median(iter_totals)),
        'median_checks': int(_median(check_totals)),
        'median_converged_ratio': _median(converged_ratios),
        'median_stagnated_ratio': _median(stagnated_ratios),
        'median_quiescent_ratio': _median(quiescent_ratios),
        'median_fallback_ratio': _median(fallback_ratios),
        'max_final_delta_en': max(max_deltas) if max_deltas else None,
        'graph_meta': graph_meta,
        'result': last_result
    }


def compare_results(baseline_points, converged_points, phase_floor=1e-9):
    max_mag_delta = 0.0
    max_phase_delta = 0.0
    keys = ('S11', 'S21', 'S12', 'S22')
    for idx in range(len(baseline_points)):
        b_point = baseline_points[idx]
        c_point = converged_points[idx]
        for key in keys:
            b_val = b_point[key]
            c_val = c_point[key]
            mag_delta = abs(abs(c_val) - abs(b_val))
            if mag_delta > max_mag_delta:
                max_mag_delta = mag_delta
            if abs(c_val) >= phase_floor and abs(b_val) >= phase_floor:
                phase_delta = _phase_diff_deg(_phase_deg(c_val), _phase_deg(b_val))
                if phase_delta > max_phase_delta:
                    max_phase_delta = phase_delta
    return max_mag_delta, max_phase_delta


def benchmark_one_case(sim_file, args):
    baseline = run_case(
        sim_file=sim_file,
        converge=False,
        tol=args.tol,
        min_iter=args.min_iter,
        patience=args.patience,
        max_iter=args.max_iter,
        repeats=args.repeats,
        warmup=args.warmup,
        check_every=args.check_every,
        stagnation_checks=args.stagnation_checks,
        stagnation_ratio=args.stagnation_ratio,
        max_checks=args.max_checks,
        auto_disable_convergence=args.auto_disable_convergence,
        pilot_points=args.pilot_points,
        min_converged_ratio=args.min_converged_ratio,
        use_fastflow=args.use_fastflow,
        use_numba=args.use_numba
    )

    converged = None
    if args.mode in ('both', 'converged'):
        converged = run_case(
            sim_file=sim_file,
            converge=True,
            tol=args.tol,
            min_iter=args.min_iter,
            patience=args.patience,
            max_iter=args.max_iter,
            repeats=args.repeats,
            warmup=args.warmup,
            check_every=args.check_every,
            stagnation_checks=args.stagnation_checks,
            stagnation_ratio=args.stagnation_ratio,
            max_checks=args.max_checks,
            auto_disable_convergence=args.auto_disable_convergence,
            pilot_points=args.pilot_points,
            min_converged_ratio=args.min_converged_ratio,
            use_fastflow=args.use_fastflow,
            use_numba=args.use_numba
        )

    return baseline, converged


def main():
    parser = argparse.ArgumentParser(description='Benchmark FLO baseline vs convergence-enabled solver.')
    parser.add_argument('--mode', choices=['baseline', 'converged', 'both'], default='both')
    parser.add_argument('--tol', type=float, default=1e-6)
    parser.add_argument('--min-iter', type=int, default=5)
    parser.add_argument('--patience', type=int, default=3)
    parser.add_argument('--max-iter', type=int, default=None)
    parser.add_argument('--check-every', type=int, default=8)
    parser.add_argument('--stagnation-checks', type=int, default=4)
    parser.add_argument('--stagnation-ratio', type=float, default=0.995)
    parser.add_argument('--max-checks', type=int, default=64)
    parser.add_argument('--phase-floor', type=float, default=1e-9)
    parser.add_argument('--auto-disable-convergence', type=int, choices=[0, 1], default=1)
    parser.add_argument('--pilot-points', type=int, default=40)
    parser.add_argument('--min-converged-ratio', type=float, default=0.2)
    parser.add_argument('--use-fastflow', type=int, choices=[0, 1], default=0)
    parser.add_argument('--use-numba', type=int, choices=[0, 1], default=0)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--warmup', type=int, default=1)
    parser.add_argument(
        '--cases',
        nargs='*',
        default=['sim_files/lpf.sim', 'sim_files/bpf.sim', 'sim_files/stress_ladder.sim']
    )
    args = parser.parse_args()

    args.auto_disable_convergence = bool(args.auto_disable_convergence)
    args.use_fastflow = bool(args.use_fastflow)
    args.use_numba = bool(args.use_numba)

    print('mode={0} tol={1} min_iter={2} patience={3} max_iter={4} check_every={5} stagnation_checks={6} stagnation_ratio={7} max_checks={8} auto_disable={9} pilot_points={10} min_converged_ratio={11} use_fastflow={12} use_numba={13} phase_floor={14} repeats={15} warmup={16}'.format(
        args.mode, args.tol, args.min_iter, args.patience, args.max_iter, args.check_every,
        args.stagnation_checks, args.stagnation_ratio, args.max_checks,
        int(args.auto_disable_convergence), args.pilot_points, args.min_converged_ratio,
        int(args.use_fastflow), int(args.use_numba), args.phase_floor, args.repeats, args.warmup
    ))
    print('')

    for sim_file in args.cases:
        print('Case: {0}'.format(sim_file))
        baseline, converged = benchmark_one_case(sim_file, args)

        if args.mode == 'baseline':
            print('  baseline_time_s={0:.6f} baseline_median_iters={1}'.format(
                baseline['median_time_s'], baseline['median_iters']
            ))
            if baseline['graph_meta'] is not None:
                gm = baseline['graph_meta']
                print('  graph_nodes={0}->{1} graph_edges={2}->{3} scc={4} cyclic_scc={5} cyclic_nodes={6}'.format(
                    gm['orig_nodes'], gm['reduced_nodes'], gm['orig_edges'], gm['reduced_edges'],
                    gm['scc_count'], gm['cyclic_scc_count'], gm['cyclic_nodes']
                ))
            print('')
            continue

        if args.mode == 'converged':
            print('  converged_time_s={0:.6f} converged_median_iters={1} converged_ratio={2:.2%} checks={3} fallback_ratio={4:.2%}'.format(
                converged['median_time_s'], converged['median_iters'], converged['median_converged_ratio'],
                converged['median_checks'], converged['median_fallback_ratio']
            ))
            if converged['max_final_delta_en'] is not None:
                print('  converged_max_final_delta_en={0:.3e}'.format(converged['max_final_delta_en']))
            print('')
            continue

        speedup = baseline['median_time_s'] / converged['median_time_s']
        max_mag_delta, max_phase_delta = compare_results(
            baseline['result']['points'],
            converged['result']['points'],
            phase_floor=args.phase_floor
        )
        print('  baseline_time_s={0:.6f} baseline_median_iters={1}'.format(
            baseline['median_time_s'], baseline['median_iters']
        ))
        if baseline['graph_meta'] is not None:
            gm = baseline['graph_meta']
            print('  graph_nodes={0}->{1} graph_edges={2}->{3} scc={4} cyclic_scc={5} cyclic_nodes={6}'.format(
                gm['orig_nodes'], gm['reduced_nodes'], gm['orig_edges'], gm['reduced_edges'],
                gm['scc_count'], gm['cyclic_scc_count'], gm['cyclic_nodes']
            ))
        print('  converged_time_s={0:.6f} converged_median_iters={1} converged_ratio={2:.2%} checks={3} fallback_ratio={4:.2%}'.format(
            converged['median_time_s'], converged['median_iters'], converged['median_converged_ratio'],
            converged['median_checks'], converged['median_fallback_ratio']
        ))
        if converged['max_final_delta_en'] is not None:
            print('  converged_max_final_delta_en={0:.3e}'.format(converged['max_final_delta_en']))
        print('  speedup={0:.3f}x max_mag_delta={1:.3e} max_phase_delta_deg={2:.6f}'.format(
            speedup, max_mag_delta, max_phase_delta
        ))
        print('')


if __name__ == '__main__':
    main()
