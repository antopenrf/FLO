#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

static PyObject* propagate_csr(PyObject* self, PyObject* args) {
    PyObject *edge_offsets_obj, *edge_to_obj, *edge_w_obj, *output_idxs_obj;
    int source_idx, pin_neg_idx;
    int iter_limit, converge, min_iter, patience, check_every, stagnation_checks, max_checks;
    double tol, stagnation_ratio;

    if (!PyArg_ParseTuple(
            args, "OOOiiOiidiiiidi",
            &edge_offsets_obj, &edge_to_obj, &edge_w_obj,
            &source_idx, &pin_neg_idx, &output_idxs_obj,
            &iter_limit, &converge, &tol, &min_iter, &patience, &check_every,
            &stagnation_checks, &stagnation_ratio, &max_checks)) {
        return NULL;
    }

    PyObject *edge_offsets_seq = PySequence_Fast(edge_offsets_obj, "edge_offsets must be a sequence");
    PyObject *edge_to_seq = PySequence_Fast(edge_to_obj, "edge_to must be a sequence");
    PyObject *edge_w_seq = PySequence_Fast(edge_w_obj, "edge_w must be a sequence");
    PyObject *output_idxs_seq = PySequence_Fast(output_idxs_obj, "output_idxs must be a sequence");
    if (!edge_offsets_seq || !edge_to_seq || !edge_w_seq || !output_idxs_seq) {
        Py_XDECREF(edge_offsets_seq);
        Py_XDECREF(edge_to_seq);
        Py_XDECREF(edge_w_seq);
        Py_XDECREF(output_idxs_seq);
        return NULL;
    }

    Py_ssize_t offsets_len = PySequence_Fast_GET_SIZE(edge_offsets_seq);
    Py_ssize_t edge_count = PySequence_Fast_GET_SIZE(edge_to_seq);
    Py_ssize_t edge_w_len = PySequence_Fast_GET_SIZE(edge_w_seq);
    Py_ssize_t out_count = PySequence_Fast_GET_SIZE(output_idxs_seq);
    if (offsets_len < 1 || edge_count != edge_w_len) {
        PyErr_SetString(PyExc_ValueError, "invalid CSR sizes");
        goto fail;
    }

    int n_nodes = (int)(offsets_len - 1);
    int *edge_offsets = (int*)malloc(sizeof(int) * (size_t)offsets_len);
    int *edge_to = (int*)malloc(sizeof(int) * (size_t)edge_count);
    double *edge_w = (double*)malloc(sizeof(double) * (size_t)edge_count);
    int *output_idxs = (int*)malloc(sizeof(int) * (size_t)out_count);
    double *en = (double*)calloc((size_t)n_nodes, sizeof(double));
    double *sf = (double*)calloc((size_t)n_nodes, sizeof(double));
    unsigned char *tick = (unsigned char*)calloc((size_t)n_nodes, sizeof(unsigned char));
    int *ticks = (int*)malloc(sizeof(int) * (size_t)n_nodes);
    double *last_checked_en = (double*)calloc((size_t)n_nodes, sizeof(double));
    if (!edge_offsets || !edge_to || !edge_w || !output_idxs || !en || !sf || !tick || !ticks || !last_checked_en) {
        PyErr_SetString(PyExc_MemoryError, "allocation failed");
        goto fail_alloc;
    }

    Py_ssize_t i;
    for (i = 0; i < offsets_len; ++i) {
        edge_offsets[i] = (int)PyInt_AsLong(PySequence_Fast_GET_ITEM(edge_offsets_seq, i));
    }
    for (i = 0; i < edge_count; ++i) {
        edge_to[i] = (int)PyInt_AsLong(PySequence_Fast_GET_ITEM(edge_to_seq, i));
        edge_w[i] = PyFloat_AsDouble(PySequence_Fast_GET_ITEM(edge_w_seq, i));
    }
    for (i = 0; i < out_count; ++i) {
        output_idxs[i] = (int)PyInt_AsLong(PySequence_Fast_GET_ITEM(output_idxs_seq, i));
    }

    if (check_every < 1) {
        check_every = 1;
    }

    en[source_idx] = 1.0;
    for (i = edge_offsets[source_idx]; i < edge_offsets[source_idx + 1]; ++i) {
        int to_idx = edge_to[i];
        double val = edge_w[i];
        sf[to_idx] += val;
        en[to_idx] += val;
        tick[to_idx] = 1;
    }

    int stable_count = 0;
    int converged_flag = 0;
    int iters_used = 0;
    int check_count = 0;
    int stagnated = 0;
    int convergence_active = converge ? 1 : 0;
    double final_max_delta_en = 0.0;
    int has_final_delta = 0;
    double prev_check_delta = 0.0;
    int has_prev_check_delta = 0;
    int stagnation_count = 0;
    const char *mode_used = "baseline";
    if (convergence_active) {
        mode_used = "convergence";
        for (i = 0; i < n_nodes; ++i) {
            last_checked_en[i] = en[i];
        }
    }

    int each;
    for (each = 0; each < iter_limit; ++each) {
        int tick_count = 0;
        int n;
        for (n = 0; n < n_nodes; ++n) {
            if (tick[n]) {
                ticks[tick_count++] = n;
            }
        }
        if (tick_count == 0) {
            mode_used = "quiescent";
            break;
        }

        int t;
        for (t = 0; t < tick_count; ++t) {
            int node = ticks[t];
            double incoming = sf[node];
            int e;
            for (e = edge_offsets[node]; e < edge_offsets[node + 1]; ++e) {
                int to_idx = edge_to[e];
                double val = incoming * edge_w[e];
                sf[to_idx] += val;
                en[to_idx] += val;
                tick[to_idx] = 1;
            }
            tick[node] = 0;
        }
        for (t = 0; t < tick_count; ++t) {
            sf[ticks[t]] = 0.0;
        }

        iters_used = each + 1;
        if (convergence_active && iters_used >= min_iter && (iters_used % check_every) == 0) {
            check_count += 1;
            double max_delta_en = 0.0;
            for (n = 0; n < n_nodes; ++n) {
                double delta = fabs(en[n] - last_checked_en[n]);
                if (delta > max_delta_en) {
                    max_delta_en = delta;
                }
                last_checked_en[n] = en[n];
            }
            final_max_delta_en = max_delta_en;
            has_final_delta = 1;

            if (max_delta_en < tol) {
                stable_count += 1;
            } else {
                stable_count = 0;
            }
            if (stable_count >= patience) {
                converged_flag = 1;
                mode_used = "converged";
                break;
            }

            if (has_prev_check_delta) {
                if (max_delta_en >= prev_check_delta * stagnation_ratio) {
                    stagnation_count += 1;
                } else {
                    stagnation_count = 0;
                }
            }
            prev_check_delta = max_delta_en;
            has_prev_check_delta = 1;
            if (stagnation_count >= stagnation_checks) {
                stagnated = 1;
                convergence_active = 0;
                mode_used = "fallback_baseline";
            }
            if (convergence_active && max_checks >= 0 && check_count >= max_checks) {
                convergence_active = 0;
                mode_used = "fallback_baseline";
            }
        }
    }

    if (strcmp(mode_used, "convergence") == 0 && !converged_flag) {
        mode_used = "max_iter";
    }

    PyObject *insersions = PyList_New(out_count);
    if (!insersions) {
        goto fail_alloc;
    }
    for (i = 0; i < out_count; ++i) {
        PyObject *v = PyFloat_FromDouble(en[output_idxs[i]]);
        if (!v) {
            Py_DECREF(insersions);
            goto fail_alloc;
        }
        PyList_SET_ITEM(insersions, i, v);
    }

    PyObject *stats = PyDict_New();
    if (!stats) {
        Py_DECREF(insersions);
        goto fail_alloc;
    }
    PyDict_SetItemString(stats, "iters_used", PyInt_FromLong(iters_used));
    PyDict_SetItemString(stats, "converged", converged_flag ? Py_True : Py_False);
    Py_INCREF(converged_flag ? Py_True : Py_False);
    if (has_final_delta) {
        PyDict_SetItemString(stats, "final_max_delta_en", PyFloat_FromDouble(final_max_delta_en));
    } else {
        PyDict_SetItemString(stats, "final_max_delta_en", Py_None);
        Py_INCREF(Py_None);
    }
    PyDict_SetItemString(stats, "check_count", PyInt_FromLong(check_count));
    PyDict_SetItemString(stats, "stagnated", stagnated ? Py_True : Py_False);
    Py_INCREF(stagnated ? Py_True : Py_False);
    PyDict_SetItemString(stats, "mode_used", PyString_FromString(mode_used));

    PyObject *ret = Py_BuildValue("dOO", en[pin_neg_idx], insersions, stats);
    Py_DECREF(insersions);
    Py_DECREF(stats);

    free(edge_offsets);
    free(edge_to);
    free(edge_w);
    free(output_idxs);
    free(en);
    free(sf);
    free(tick);
    free(ticks);
    free(last_checked_en);
    Py_DECREF(edge_offsets_seq);
    Py_DECREF(edge_to_seq);
    Py_DECREF(edge_w_seq);
    Py_DECREF(output_idxs_seq);
    return ret;

fail_alloc:
    free(edge_offsets);
    free(edge_to);
    free(edge_w);
    free(output_idxs);
    free(en);
    free(sf);
    free(tick);
    free(ticks);
    free(last_checked_en);
fail:
    Py_XDECREF(edge_offsets_seq);
    Py_XDECREF(edge_to_seq);
    Py_XDECREF(edge_w_seq);
    Py_XDECREF(output_idxs_seq);
    return NULL;
}

static PyMethodDef FastFlowMethods[] = {
    {"propagate_csr", propagate_csr, METH_VARARGS, "Propagate wave graph on CSR arrays."},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC initfastflow(void) {
    Py_InitModule("fastflow", FastFlowMethods);
}
