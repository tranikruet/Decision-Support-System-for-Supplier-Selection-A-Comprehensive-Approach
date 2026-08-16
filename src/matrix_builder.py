import numpy as np


def build_smp_matrix(criteria, weights, interdependencies):
    
    n = len(criteria)
    # Start with interdependencies (off-diagonal elements)
    SMP = np.array(interdependencies, dtype=float, copy=True)
    
    # Place supplier performance scores on diagonal (Fi values)
    for i in range(n):
        if criteria[i] in weights:
            SMP[i][i] = weights[criteria[i]]
        else:
            SMP[i][i] = 0.0
    
    return SMP


def build_matrix(scores, dependency_matrix):
    
    n = len(scores)
    M = np.array(dependency_matrix, dtype=float)
    
    # Place scores on the diagonal (self-weights)
    for i in range(n):
        M[i][i] = scores[i]
    
    return M


def build_gtma_matrix(criteria, weights, digraph_adjacency):
    
    n = len(criteria)
    A = np.array(digraph_adjacency, dtype=float)
    
    # Place weights on diagonal
    for i in range(n):
        if criteria[i] in weights:
            A[i][i] = weights[criteria[i]]
    
    return A
