import numpy as np

def gray_code_permanent(A):

    n = len(A)
    N = 1 << n

    rowsum = np.zeros(n)
    permanent = 0

    gray_prev = 0

    for k in range(1, N):

        gray = k ^ (k >> 1)
        diff = gray ^ gray_prev

        j = (diff & -diff).bit_length() - 1

        if gray & diff:
            rowsum += A[:, j]
        else:
            rowsum -= A[:, j]

        prod = np.prod(rowsum)

        bits = bin(gray).count("1")

        if (n - bits) % 2 == 0:
            permanent += prod
        else:
            permanent -= prod

        gray_prev = gray

    return permanent