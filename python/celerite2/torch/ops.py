# -*- coding: utf-8 -*-

__all__ = [
    "factor",
    "solve",
    "norm",
    "dot_tril",
    "matmul",
    "conditional_mean",
    "searchsorted",
]
from functools import wraps

import numpy as np
import torch
from torch.autograd import Function

from celerite2 import backprop, driver


def wrap_forward(func):
    @wraps(func)
    def wrapped(ctx, *inputs):
        in_tensors = tuple(x.detach() for x in inputs)
        in_arrays = tuple(x.numpy() for x in in_tensors)
        out_arrays = func(*in_arrays)
        out_tensors = tuple(
            torch.as_tensor(x, dtype=torch.float64) for x in out_arrays
        )
        ctx.save_for_backward(*in_tensors, *out_tensors)
        return out_tensors

    return wrapped


def wrap_backward(func):
    @wraps(func)
    def wrapped(ctx, *grads):
        grad_tensors = tuple(x.detach() for x in grads)
        grad_arrays = tuple(x.numpy() for x in grad_tensors)
        saved_arrays = tuple(x.detach().numpy() for x in ctx.saved_tensors)
        out_arrays = func(*saved_arrays, *grad_arrays)
        out_tensors = tuple(
            torch.as_tensor(x, dtype=torch.float64) for x in out_arrays
        )
        return out_tensors

    return wrapped


class Factor(Function):
    @staticmethod
    def forward(ctx, a, U, V, P):
        @wrap_forward
        def apply(a, U, V, P):
            N, J = U.shape
            d = np.empty_like(a)
            W = np.empty_like(V)
            S = np.empty((N, J ** 2), dtype=np.float64)
            return backprop.factor_fwd(a, U, V, P, d, W, S)

        return apply(ctx, a, U, V, P)[:2]

    @staticmethod
    def backward(ctx, bd, bW):
        @wrap_backward
        def apply(a, U, V, P, d, W, S, bd, bW):
            ba = np.empty_like(a)
            bU = np.empty_like(U)
            bV = np.empty_like(V)
            bP = np.empty_like(P)
            return backprop.factor_rev(
                a, U, V, P, d, W, S, bd, bW, ba, bU, bV, bP
            )

        return apply(ctx, bd, bW)


class Solve(Function):
    @staticmethod
    def forward(ctx, U, P, d, W, Y):
        @wrap_forward
        def apply(U, P, d, W, Y):
            N, J = U.shape
            if Y.ndim == 1:
                nrhs = 1
            else:
                nrhs = Y.shape[1]
            X = np.empty_like(Y)
            Z = np.empty_like(X)
            F = np.empty((N, J * nrhs), dtype=np.float64)
            G = np.empty((N, J * nrhs), dtype=np.float64)
            return backprop.solve_fwd(U, P, d, W, Y, X, Z, F, G)

        return apply(ctx, U, P, d, W, Y)[0]

    @staticmethod
    def backward(ctx, bX):
        @wrap_backward
        def apply(U, P, d, W, Y, X, Z, F, G, bX):
            bU = np.empty_like(U)
            bP = np.empty_like(P)
            bd = np.empty_like(d)
            bW = np.empty_like(W)
            bY = np.empty_like(Y)
            return backprop.solve_rev(
                U, P, d, W, Y, X, Z, F, G, bX, bU, bP, bd, bW, bY
            )

        return apply(ctx, bX)


class Norm(Function):
    @staticmethod
    def forward(ctx, U, P, d, W, Y):
        @wrap_forward
        def apply(U, P, d, W, Y):
            N, J = U.shape
            X = np.empty((), dtype=np.float64)
            Z = np.empty_like(Y)
            F = np.empty((N, J), dtype=np.float64)
            return backprop.norm_fwd(U, P, d, W, Y, X, Z, F)

        return apply(ctx, U, P, d, W, Y)[0]

    @staticmethod
    def backward(ctx, bX):
        @wrap_backward
        def apply(U, P, d, W, Y, X, Z, F, bX):
            bU = np.empty_like(U)
            bP = np.empty_like(P)
            bd = np.empty_like(d)
            bW = np.empty_like(W)
            bY = np.empty_like(Y)
            return backprop.norm_rev(
                U, P, d, W, Y, X, Z, F, bX, bU, bP, bd, bW, bY
            )

        return apply(ctx, bX)


class DotTril(Function):
    @staticmethod
    def forward(ctx, U, P, d, W, Y):
        @wrap_forward
        def apply(U, P, d, W, Y):
            N, J = U.shape
            if Y.ndim == 1:
                nrhs = 1
            else:
                nrhs = Y.shape[1]
            X = np.empty_like(Y)
            F = np.empty((N, J * nrhs), dtype=np.float64)
            return backprop.dot_tril_fwd(U, P, d, W, Y, X, F)

        return apply(ctx, U, P, d, W, Y)[0]

    @staticmethod
    def backward(ctx, bX):
        @wrap_backward
        def apply(U, P, d, W, Y, X, F, bX):
            bU = np.empty_like(U)
            bP = np.empty_like(P)
            bd = np.empty_like(d)
            bW = np.empty_like(W)
            bY = np.empty_like(Y)
            return backprop.dot_tril_rev(
                U, P, d, W, Y, X, F, bX, bU, bP, bd, bW, bY
            )

        return apply(ctx, bX)


class Matmul(Function):
    @staticmethod
    def forward(ctx, a, U, V, P, Y):
        @wrap_forward
        def apply(a, U, V, P, Y):
            N, J = U.shape
            if Y.ndim == 1:
                nrhs = 1
            else:
                nrhs = Y.shape[1]
            X = np.empty_like(Y)
            Z = np.empty_like(X)
            F = np.empty((N, J * nrhs), dtype=np.float64)
            G = np.empty((N, J * nrhs), dtype=np.float64)
            return backprop.matmul_fwd(a, U, V, P, Y, X, Z, F, G)

        return apply(ctx, a, U, V, P, Y)[0]

    @staticmethod
    def backward(ctx, bX):
        @wrap_backward
        def apply(a, U, V, P, Y, X, Z, F, G, bX):
            ba = np.empty_like(a)
            bU = np.empty_like(U)
            bV = np.empty_like(V)
            bP = np.empty_like(P)
            bY = np.empty_like(Y)
            return backprop.matmul_rev(
                a, U, V, P, Y, X, Z, F, G, bX, ba, bU, bV, bP, bY
            )

        return apply(ctx, bX)


class ConditionalMean(Function):
    @staticmethod
    def forward(ctx, U, V, P, alpha, U_star, V_star, inds):
        inds_ = inds.detach().numpy()
        mu_ = np.empty(inds_.shape, dtype=np.float64)
        mu_ = driver.conditional_mean(
            U.detach().numpy(),
            V.detach().numpy(),
            P.detach().numpy(),
            alpha.detach().numpy(),
            U_star.detach().numpy(),
            V_star.detach().numpy(),
            inds_,
            mu_,
        )
        return torch.as_tensor(mu_, dtype=torch.double)


class Searchsorted(Function):
    @staticmethod
    def forward(ctx, x, t):
        ctx.save_for_backward(x, t)
        x_ = x.detach().numpy()
        t_ = t.detach().numpy()
        inds = np.searchsorted(x_, t_)
        return torch.as_tensor(inds, dtype=torch.int64)

    @staticmethod
    def backward(ctx, grad):
        x, t = ctx.saved_tensors
        return torch.zeros_like(x), torch.zeros_like(t)


def factor(*args):
    return Factor.apply(*args)


def solve(*args):
    return Solve.apply(*args)


def norm(*args):
    return Norm.apply(*args)


def dot_tril(*args):
    return DotTril.apply(*args)


def matmul(*args):
    return Matmul.apply(*args)


def conditional_mean(*args):
    return ConditionalMean.apply(*args)


def searchsorted(*args):
    return Searchsorted.apply(*args)
