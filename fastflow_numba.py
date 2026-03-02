from __future__ import print_function

import numpy as np

AVAILABLE = False

try:
    from numba import njit
    AVAILABLE = True
except Exception:
    njit = None


if AVAILABLE:
    @njit(cache=True)
    def _propagate_loop(edge_offsets, edge_to, edge_w, source_idx, iter_limit,
                        converge, tol, min_iter, patience, check_every,
                        stagnation_checks, stagnation_ratio, max_checks):
        n_nodes = edge_offsets.shape[0] - 1
        en = np.zeros(n_nodes, dtype=np.complex128)
        sf = np.zeros(n_nodes, dtype=np.complex128)
        tick = np.zeros(n_nodes, dtype=np.uint8)
        ticks = np.empty(n_nodes, dtype=np.int64)
        last_checked_en = np.zeros(n_nodes, dtype=np.complex128)

        en[source_idx] = 1.0
        for e in range(edge_offsets[source_idx], edge_offsets[source_idx + 1]):
            to_idx = edge_to[e]
            val = edge_w[e]
            sf[to_idx] += val
            en[to_idx] += val
            tick[to_idx] = 1

        if check_every < 1:
            check_every = 1

        stable_count = 0
        converged_flag = 0
        iters_used = 0
        check_count = 0
        stagnated = 0
        convergence_active = converge
        final_max_delta_en = 0.0
        has_final_delta = 0
        prev_check_delta = 0.0
        has_prev_check_delta = 0
        stagnation_count = 0
        mode_code = 0  # baseline
        if convergence_active == 1:
            mode_code = 1  # convergence
            for i in range(n_nodes):
                last_checked_en[i] = en[i]

        for each in range(iter_limit):
            tick_count = 0
            for i in range(n_nodes):
                if tick[i] == 1:
                    ticks[tick_count] = i
                    tick_count += 1

            if tick_count == 0:
                mode_code = 2  # quiescent
                break

            for t in range(tick_count):
                node = ticks[t]
                incoming = sf[node]
                for e in range(edge_offsets[node], edge_offsets[node + 1]):
                    to_idx = edge_to[e]
                    val = incoming * edge_w[e]
                    sf[to_idx] += val
                    en[to_idx] += val
                    tick[to_idx] = 1
                tick[node] = 0

            for t in range(tick_count):
                sf[ticks[t]] = 0.0

            iters_used = each + 1
            if convergence_active == 1 and iters_used >= min_iter and (iters_used % check_every) == 0:
                check_count += 1
                max_delta_en = 0.0
                for i in range(n_nodes):
                    delta = abs(en[i] - last_checked_en[i])
                    if delta > max_delta_en:
                        max_delta_en = delta
                    last_checked_en[i] = en[i]
                final_max_delta_en = max_delta_en
                has_final_delta = 1

                if max_delta_en < tol:
                    stable_count += 1
                else:
                    stable_count = 0
                if stable_count >= patience:
                    converged_flag = 1
                    mode_code = 3  # converged
                    break

                if has_prev_check_delta == 1:
                    if max_delta_en >= prev_check_delta * stagnation_ratio:
                        stagnation_count += 1
                    else:
                        stagnation_count = 0
                prev_check_delta = max_delta_en
                has_prev_check_delta = 1

                if stagnation_count >= stagnation_checks:
                    stagnated = 1
                    convergence_active = 0
                    mode_code = 4  # fallback_baseline
                if convergence_active == 1 and max_checks >= 0 and check_count >= max_checks:
                    convergence_active = 0
                    mode_code = 4

        if mode_code == 1 and converged_flag == 0:
            mode_code = 5  # max_iter

        return en, iters_used, converged_flag, has_final_delta, final_max_delta_en, check_count, stagnated, mode_code


def propagate_csr(edge_offsets, edge_to, edge_w, source_idx, pin_neg_idx, output_idxs,
                  iter_limit, converge, tol, min_iter, patience, check_every,
                  stagnation_checks, stagnation_ratio, max_checks):
    if not AVAILABLE:
        raise RuntimeError("numba backend unavailable")

    edge_offsets_np = np.asarray(edge_offsets, dtype=np.int64)
    edge_to_np = np.asarray(edge_to, dtype=np.int64)
    edge_w_np = np.asarray(edge_w, dtype=np.complex128)
    max_checks_i = -1 if max_checks is None else int(max_checks)

    en, iters_used, converged_flag, has_final_delta, final_max_delta_en, check_count, stagnated, mode_code = _propagate_loop(
        edge_offsets_np, edge_to_np, edge_w_np, int(source_idx), int(iter_limit),
        1 if converge else 0, float(tol), int(min_iter), int(patience), int(check_every),
        int(stagnation_checks), float(stagnation_ratio), int(max_checks_i)
    )

    mode_map = {
        0: 'baseline',
        1: 'convergence',
        2: 'quiescent',
        3: 'converged',
        4: 'fallback_baseline',
        5: 'max_iter'
    }
    stats = {
        'iters_used': int(iters_used),
        'converged': bool(converged_flag),
        'final_max_delta_en': float(final_max_delta_en) if has_final_delta else None,
        'check_count': int(check_count),
        'stagnated': bool(stagnated),
        'mode_used': mode_map.get(int(mode_code), 'baseline')
    }
    b1 = complex(en[int(pin_neg_idx)])
    insersions = [complex(en[int(idx)]) for idx in output_idxs]
    return b1, insersions, stats
