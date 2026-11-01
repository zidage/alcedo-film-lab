"""Compiled, parallel kernels of the film preview (numba). Each kernel has the same meaning as a stage of film_preview.py.

check_fast_kernels.py compares them with the array implementation in film_preview.py, which stays as the reference.
Image data is float32 with shape (H, W, 3). Curves are on a uniform grid.

Rule 'large_blur_on_reduced_image': a Gaussian with sigma >= LARGE_SIGMA runs on a box-reduced image, with bilinear
enlargement. The image of the blur is smooth, so the cost does not grow with the image size. The check limits the error.
"""

from __future__ import annotations

import math

import numpy as np
from numba import njit, prange

LOG10 = 2.302585092994046
LARGE_SIGMA = 12.0
HALF_SIZE_SMALLEST_SIGMA = 4.0  # rule 'inhibitor_on_half_size': below this the reduction changes the result (P7 report, section 5.3)


@njit(fastmath=True)
def _acescc_encode(value):
    if value < 0.0:
        return (-16.0 + 9.72) / 17.52 + value
    if value < 0.000030517578125:
        return (math.log2(0.0000152587890625 + value * 0.5) + 9.72) / 17.52
    return (math.log2(value) + 9.72) / 17.52


@njit(fastmath=True)
def _acescc_decode(value):
    if value < (-16.0 + 9.72) / 17.52:
        return value - (-16.0 + 9.72) / 17.52
    if value <= (-15.0 + 9.72) / 17.52:
        return (2.0 ** (value * 17.52 - 9.72) - 0.0000152587890625) * 2.0
    return 2.0 ** (value * 17.52 - 9.72)


@njit(parallel=True, fastmath=True, cache=True)
def product_grade(ap1, exposure_ev, contrast, saturation):
    """The default Color Grade of Alcedo Studio on linear AP1: exposure, contrast, saturation, in that order, on ACEScc.
    Source: alcedo_studio/src/edit/runtime/opencl/shader/primary_grade.cl, oklab.cl. Saturation has no peak limit here;
    the product applies one only above a scale of 1.5."""
    h, w = ap1.shape[:2]
    out = np.empty_like(ap1)
    offset = exposure_ev / 17.52
    slope = 2.0 ** (contrast * 0.01)
    for i in prange(h):
        for j in range(w):
            c0 = _acescc_encode(float(ap1[i, j, 0])) + offset
            c1 = _acescc_encode(float(ap1[i, j, 1])) + offset
            c2 = _acescc_encode(float(ap1[i, j, 2])) + offset
            if contrast != 0.0:
                r, g, b = _acescc_decode(c0), _acescc_decode(c1), _acescc_decode(c2)
                l_ = np.cbrt(0.6341104672 * r + 0.3489495087 * g + 0.0169400240 * b)
                m_ = np.cbrt(0.2754060131 * r + 0.6327713632 * g + 0.0918226237 * b)
                s_ = np.cbrt(0.1056775254 * r + 0.1971481306 * g + 0.6971743440 * b)
                lab_l = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
                lab_a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
                lab_b = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
                shape = math.tanh(3.0 * math.log2(lab_l / 0.5646216) / 2.5) if lab_l > 0.0 else -1.0
                gain = 2.0 ** ((slope - 1.0) * 2.5 * shape / 3.0)
                chroma = math.sqrt(slope) * min(gain, 1.0)
                lab_l, lab_a, lab_b = lab_l * gain, lab_a * chroma, lab_b * chroma
                l_ = lab_l + 0.3963377774 * lab_a + 0.2158037573 * lab_b
                m_ = lab_l - 0.1055613458 * lab_a - 0.0638541728 * lab_b
                s_ = lab_l - 0.0894841775 * lab_a - 1.2914855480 * lab_b
                l3, m3, s3 = l_ * l_ * l_, m_ * m_ * m_, s_ * s_ * s_
                c0 = _acescc_encode(2.0693822907 * l3 - 1.1736821545 * m3 + 0.1042998638 * s3)
                c1 = _acescc_encode(-0.8917480677 * l3 + 2.1537429245 * m3 - 0.2619948569 * s3)
                c2 = _acescc_encode(-0.0615064732 * l3 - 0.4311325686 * m3 + 1.4926390418 * s3)
            luma = 0.272229 * c0 + 0.674082 * c1 + 0.053689 * c2
            out[i, j, 0] = _acescc_decode(luma + (c0 - luma) * saturation)
            out[i, j, 1] = _acescc_decode(luma + (c1 - luma) * saturation)
            out[i, j, 2] = _acescc_decode(luma + (c2 - luma) * saturation)
    return out


@njit(parallel=True, fastmath=True, cache=True)
def layer_exposure(ap1, flare, to_xyz, normals, room, white, inset, table, uv_max, gain):
    """Stage 2: rule 'spectral_locus_projection', then the u'v' table. Returns (Q, moved, Y not positive)."""
    h, w = ap1.shape[:2]
    out = np.empty((h, w, 3), dtype=np.float32)
    nodes = table.shape[0]
    scale_u = (nodes - 1) / uv_max[0]
    scale_v = (nodes - 1) / uv_max[1]
    facets = normals.shape[0]
    moved = np.zeros(h, dtype=np.int64)
    not_positive = np.zeros(h, dtype=np.int64)
    for i in prange(h):
        row_moved = 0
        row_not_positive = 0
        for j in range(w):
            r, g, b = ap1[i, j, 0] + flare, ap1[i, j, 1] + flare, ap1[i, j, 2] + flare
            x = to_xyz[0, 0] * r + to_xyz[0, 1] * g + to_xyz[0, 2] * b
            y = to_xyz[1, 0] * r + to_xyz[1, 1] * g + to_xyz[1, 2] * b
            z = to_xyz[2, 0] * r + to_xyz[2, 1] * g + to_xyz[2, 2] * b
            if y <= 0.0:
                out[i, j, 0] = out[i, j, 1] = out[i, j, 2] = 0.0
                row_not_positive += 1
                continue
            dx = x / y - white[0]
            dz = z / y - white[1]
            t = 1.0
            for k in range(facets):
                rate = dx * normals[k, 0] + dz * normals[k, 1]
                if rate > 0.0:
                    limit = room[k] * (1.0 - inset) / rate
                    if limit < t:
                        t = limit
            if t < 1.0:
                row_moved += 1
            x = (white[0] + t * dx) * y
            z = (white[1] + t * dz) * y
            d = x + 15.0 * y + 3.0 * z
            cu = min(max(4.0 * x / d * scale_u, 0.0), nodes - 1.000001)
            cv = min(max(9.0 * y / d * scale_v, 0.0), nodes - 1.000001)
            iu = int(cu)
            iv = int(cv)
            fu = cu - iu
            fv = cv - iv
            for k in range(3):
                value = ((1 - fu) * ((1 - fv) * table[iu, iv, k] + fv * table[iu, iv + 1, k])
                         + fu * ((1 - fv) * table[iu + 1, iv, k] + fv * table[iu + 1, iv + 1, k]))
                out[i, j, k] = gain[k] * y * value
        moved[i] = row_moved
        not_positive[i] = row_not_positive
    return out, moved.sum(), not_positive.sum()


@njit(parallel=True, fastmath=True, cache=True)
def negative_density(q, criterion, neutral, interlayer, curve_start, curves, lengths, step):
    """Stage 3: the interlayer gain, then the characteristic curves. Returns (Status M, values above the curve end)."""
    h, w = q.shape[:2]
    out = np.empty((h, w, 3), dtype=np.float32)
    above = np.zeros(h, dtype=np.int64)
    for i in prange(h):
        row_above = 0
        log_q = np.empty(3)
        for j in range(w):
            for k in range(3):
                log_q[k] = math.log10(max(float(q[i, j, k]), 1e-30))
            if interlayer != 0.0:
                d0, d1, d2 = log_q[0] - neutral[0], log_q[1] - neutral[1], log_q[2] - neutral[2]
                mean = (d0 + d1 + d2) / 3.0
                log_q[0] += interlayer * (d0 - mean)
                log_q[1] += interlayer * (d1 - mean)
                log_q[2] += interlayer * (d2 - mean)
            for k in range(3):
                t = (criterion[k] + log_q[k] - curve_start[k]) / step
                last = lengths[k] - 1
                if t <= 0.0:
                    out[i, j, k] = curves[k, 0]
                elif t >= last:
                    if t > last:
                        row_above += 1
                    out[i, j, k] = curves[k, last]
                else:
                    index = int(t)
                    out[i, j, k] = curves[k, index] + (t - index) * (curves[k, index + 1] - curves[k, index])
        above[i] = row_above
    return out, above.sum()


@njit(parallel=True, fastmath=True, cache=True)
def inhibited_step(q, inhibitor, criterion, k, start, free, lengths, step):
    """One step of rule 'development_inhibition': a_i = F_i(log H_i - sum_j K_ij I_j)."""
    h, w = q.shape[:2]
    out = np.empty((h, w, 3), dtype=np.float32)
    for i in prange(h):
        for j in range(w):
            for m in range(3):
                reduced = (criterion[m] + math.log10(max(float(q[i, j, m]), 1e-30))
                           - k[m, 0] * inhibitor[i, j, 0] - k[m, 1] * inhibitor[i, j, 1] - k[m, 2] * inhibitor[i, j, 2])
                t = (reduced - start[m]) / step
                last = lengths[m] - 1
                if t <= 0.0:
                    out[i, j, m] = free[m, 0]
                elif t >= last:
                    out[i, j, m] = free[m, last]
                else:
                    index = int(t)
                    out[i, j, m] = free[m, index] + (t - index) * (free[m, index + 1] - free[m, index])
    return out


def _kernel(sigma: float) -> np.ndarray:
    radius = int(4.0 * sigma + 0.5)
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    weights = np.exp(-0.5 * (x / sigma) ** 2)
    return (weights / weights.sum()).astype(np.float32)


@njit(parallel=True, fastmath=True, cache=True)
def _blur_fir(image, kernel_y, kernel_x):
    """Separable blur with the boundary rule 'reflect' of scipy.ndimage."""
    h, w = image.shape[:2]
    radius_y = (len(kernel_y) - 1) // 2
    radius_x = (len(kernel_x) - 1) // 2
    out = np.empty_like(image)
    middle = np.empty_like(image)
    for i in prange(h):
        for j in range(w):
            r0 = r1 = r2 = 0.0
            for m in range(-radius_x, radius_x + 1):
                c = (j + m) % (2 * w)
                if c >= w:
                    c = 2 * w - 1 - c
                weight = kernel_x[m + radius_x]
                r0 += weight * image[i, c, 0]
                r1 += weight * image[i, c, 1]
                r2 += weight * image[i, c, 2]
            middle[i, j, 0], middle[i, j, 1], middle[i, j, 2] = r0, r1, r2
    for i in prange(h):
        out[i] = 0.0
        for m in range(-radius_y, radius_y + 1):
            c = (i + m) % (2 * h)
            if c >= h:
                c = 2 * h - 1 - c
            weight = kernel_y[m + radius_y]
            for j in range(w):
                out[i, j, 0] += weight * middle[c, j, 0]
                out[i, j, 1] += weight * middle[c, j, 1]
                out[i, j, 2] += weight * middle[c, j, 2]
    return out


@njit(parallel=True, fastmath=True, cache=True)
def _reduce(image, rows, columns):
    """Box mean. The cells cover the image exactly, so the reflecting edge of the reduced image is the edge of the image."""
    h, w = image.shape[:2]
    out = np.zeros((rows, columns, 3), dtype=np.float32)
    for i in prange(rows):
        y0, y1 = (i * h + rows - 1) // rows, ((i + 1) * h + rows - 1) // rows
        for j in range(columns):
            x0, x1 = (j * w + columns - 1) // columns, ((j + 1) * w + columns - 1) // columns
            r0 = r1 = r2 = 0.0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    r0 += image[y, x, 0]
                    r1 += image[y, x, 1]
                    r2 += image[y, x, 2]
            count = (y1 - y0) * (x1 - x0)
            out[i, j, 0], out[i, j, 1], out[i, j, 2] = r0 / count, r1 / count, r2 / count
    return out


@njit(parallel=True, fastmath=True, cache=True)
def _enlarge(image, h, w):
    out = np.empty((h, w, 3), dtype=np.float32)
    rows, columns = image.shape[:2]
    for i in prange(h):
        y = min(max((i + 0.5) * rows / h - 0.5, 0.0), rows - 1.000001)
        y0 = int(y)
        fy = y - y0
        for j in range(w):
            x = min(max((j + 0.5) * columns / w - 0.5, 0.0), columns - 1.000001)
            x0 = int(x)
            fx = x - x0
            for k in range(3):
                out[i, j, k] = ((1 - fy) * ((1 - fx) * image[y0, x0, k] + fx * image[y0, x0 + 1, k])
                                + fy * ((1 - fx) * image[y0 + 1, x0, k] + fx * image[y0 + 1, x0 + 1, k]))
    return out


def gaussian_blur(image: np.ndarray, sigma: float) -> np.ndarray:
    if sigma < LARGE_SIGMA:
        kernel = _kernel(sigma)
        return _blur_fir(image, kernel, kernel)
    h, w = image.shape[:2]
    factor = int(sigma / 6.0)
    rows, columns = max(round(h / factor), 2), max(round(w / factor), 2)
    # The box reduction and the bilinear enlargement both add variance (in reduced pixels: 1/12 and 1/6).
    kernel_y = _kernel(float(np.sqrt((sigma * rows / h) ** 2 - 0.25)))
    kernel_x = _kernel(float(np.sqrt((sigma * columns / w) ** 2 - 0.25)))
    return _enlarge(_blur_fir(_reduce(image, rows, columns), kernel_y, kernel_x), h, w)


@njit(parallel=True, fastmath=True, cache=True)
def _blur_fir_per_layer(image, kernels):
    """Separable blur with one kernel per layer in one pass, with the boundary rule 'reflect' of scipy.ndimage. kernels: (3, 2 r + 1)."""
    h, w = image.shape[:2]
    radius = (kernels.shape[1] - 1) // 2
    out = np.empty_like(image)
    middle = np.empty_like(image)
    for i in prange(h):
        for j in range(w):
            r0 = r1 = r2 = 0.0
            for m in range(-radius, radius + 1):
                c = (j + m) % (2 * w)
                if c >= w:
                    c = 2 * w - 1 - c
                r0 += kernels[0, m + radius] * image[i, c, 0]
                r1 += kernels[1, m + radius] * image[i, c, 1]
                r2 += kernels[2, m + radius] * image[i, c, 2]
            middle[i, j, 0], middle[i, j, 1], middle[i, j, 2] = r0, r1, r2
    for i in prange(h):
        out[i] = 0.0
        for m in range(-radius, radius + 1):
            c = (i + m) % (2 * h)
            if c >= h:
                c = 2 * h - 1 - c
            for j in range(w):
                out[i, j, 0] += kernels[0, m + radius] * middle[c, j, 0]
                out[i, j, 1] += kernels[1, m + radius] * middle[c, j, 1]
                out[i, j, 2] += kernels[2, m + radius] * middle[c, j, 2]
    return out


def gaussian_blur_per_layer(image: np.ndarray, sigmas: tuple[float, float, float]) -> np.ndarray:
    """Rule 'spread_per_layer_pass': a Gaussian of its own sigma on each layer, in one pass. A sigma of 0 keeps the layer."""
    kernels = [_kernel(float(sigma)) if sigma > 0.0 else np.ones(1, dtype=np.float32) for sigma in sigmas]
    radius = max((len(kernel) - 1) // 2 for kernel in kernels)
    return _blur_fir_per_layer(image, np.stack([np.pad(kernel, radius - (len(kernel) - 1) // 2) for kernel in kernels]))


def gaussian_blur_half_size(image: np.ndarray, sigma: float) -> np.ndarray:
    """Rule 'inhibitor_on_half_size': from HALF_SIZE_SMALLEST_SIGMA, a Gaussian on a half-size image, with bilinear enlargement. The sigma takes out the variance of the box reduction and the enlargement. A smaller sigma stays at full size."""
    if sigma < HALF_SIZE_SMALLEST_SIGMA:
        return gaussian_blur(image, sigma)
    h, w = image.shape[:2]
    rows, columns = max(h // 2, 2), max(w // 2, 2)
    kernel_y = _kernel(float(np.sqrt((sigma * rows / h) ** 2 - 0.25)))
    kernel_x = _kernel(float(np.sqrt((sigma * columns / w) ** 2 - 0.25)))
    return _enlarge(_blur_fir(_reduce(image, rows, columns), kernel_y, kernel_x), h, w)


@njit(parallel=True, fastmath=True, cache=True)
def mix_exposure(q, blurred, strength):
    """(1 - s) q + s blurred, per layer: halation."""
    h, w = q.shape[:2]
    out = np.empty_like(q)
    for i in prange(h):
        for j in range(w):
            for k in range(3):
                out[i, j, k] = (1.0 - strength[k]) * q[i, j, k] + strength[k] * blurred[i, j, k]
    return out


@njit(parallel=True, fastmath=True, cache=True)
def add_adjacency(density, blurred, gain):
    h, w = density.shape[:2]
    out = np.empty_like(density)
    for i in prange(h):
        for j in range(w):
            for k in range(3):
                out[i, j, k] = density[i, j, k] + gain * (density[i, j, k] - blurred[i, j, k])
    return out


@njit(parallel=True, fastmath=True, cache=True)
def density_to_transmittance(density):
    h, w = density.shape[:2]
    out = np.empty_like(density)
    for i in prange(h):
        for j in range(w):
            for k in range(3):
                out[i, j, k] = math.exp(-LOG10 * density[i, j, k])
    return out


@njit(parallel=True, fastmath=True, cache=True)
def flare_density(t, blurred, flare):
    h, w = t.shape[:2]
    out = np.empty_like(t)
    for i in prange(h):
        for j in range(w):
            for k in range(3):
                out[i, j, k] = -math.log10((1.0 - flare) * t[i, j, k] + flare * blurred[i, j, k])
    return out


@njit(parallel=True, fastmath=True, cache=True)
def print_display(density, table, start, step, matrix):
    """Stage 4 and the first part of stage 5: trilinear in the print table, XYZ, linear display RGB."""
    h, w = density.shape[:2]
    n = table.shape[0]
    out = np.empty((h, w, 3), dtype=np.float32)
    for i in prange(h):
        xyz = np.empty(3)
        for j in range(w):
            c0 = min(max((density[i, j, 0] - start[0]) / step[0], 0.0), n - 1.000001)
            c1 = min(max((density[i, j, 1] - start[1]) / step[1], 0.0), n - 1.000001)
            c2 = min(max((density[i, j, 2] - start[2]) / step[2], 0.0), n - 1.000001)
            i0, i1, i2 = int(c0), int(c1), int(c2)
            f0, f1, f2 = c0 - i0, c1 - i1, c2 - i2
            for k in range(3):
                low =((1 - f1) * ((1 - f2) * table[i0, i1, i2, k] + f2 * table[i0, i1, i2 + 1, k])
                       + f1 * ((1 - f2) * table[i0, i1 + 1, i2, k] + f2 * table[i0, i1 + 1, i2 + 1, k]))
                high = ((1 - f1) * ((1 - f2) * table[i0 + 1, i1, i2, k] + f2 * table[i0 + 1, i1, i2 + 1, k])
                        + f1 * ((1 - f2) * table[i0 + 1, i1 + 1, i2, k] + f2 * table[i0 + 1, i1 + 1, i2 + 1, k]))
                value = (1 - f0) * low + f0 * high
                xyz[k] = value * value * value
            for k in range(3):
                out[i, j, k] = matrix[k, 0] * xyz[0] + matrix[k, 1] * xyz[1] + matrix[k, 2] * xyz[2]
    return out


@njit(parallel=True, fastmath=True, cache=True)
def print_display_masked(density, mask_density, tables, mask_start, mask_step, start, step, matrix):
    """Rule 'contrast_mask': as print_display, with one more linear axis over the density of the mask. tables: (masks, n, n, n, 3)."""
    h, w = density.shape[:2]
    m = tables.shape[0]
    n = tables.shape[1]
    out = np.empty((h, w, 3), dtype=np.float32)
    for i in prange(h):
        xyz = np.empty(3)
        for j in range(w):
            c0 = min(max((density[i, j, 0] - start[0]) / step[0], 0.0), n - 1.000001)
            c1 = min(max((density[i, j, 1] - start[1]) / step[1], 0.0), n - 1.000001)
            c2 = min(max((density[i, j, 2] - start[2]) / step[2], 0.0), n - 1.000001)
            c3 = min(max((mask_density[i, j] - mask_start) / mask_step, 0.0), m - 1.000001)
            i0, i1, i2, i3 = int(c0), int(c1), int(c2), int(c3)
            f0, f1, f2, f3 = c0 - i0, c1 - i1, c2 - i2, c3 - i3
            for k in range(3):
                value = 0.0
                for layer, weight in ((i3, 1.0 - f3), (i3 + 1, f3)):
                    t = tables[layer]
                    low = ((1 - f1) * ((1 - f2) * t[i0, i1, i2, k] + f2 * t[i0, i1, i2 + 1, k])
                           + f1 * ((1 - f2) * t[i0, i1 + 1, i2, k] + f2 * t[i0, i1 + 1, i2 + 1, k]))
                    high = ((1 - f1) * ((1 - f2) * t[i0 + 1, i1, i2, k] + f2 * t[i0 + 1, i1, i2 + 1, k])
                            + f1 * ((1 - f2) * t[i0 + 1, i1 + 1, i2, k] + f2 * t[i0 + 1, i1 + 1, i2 + 1, k]))
                    value += weight * ((1 - f0) * low + f0 * high)
                xyz[k] = value * value * value
            for k in range(3):
                out[i, j, k] = matrix[k, 0] * xyz[0] + matrix[k, 1] * xyz[1] + matrix[k, 2] * xyz[2]
    return out


@njit(parallel=True, fastmath=True, cache=True)
def finish_display(rgb, compress, threshold, limit, power):
    """Stage 5, second part: rule 'rgc_style_display_compression', the clip, sRGB. Returns (sRGB, clipped before, clipped after)."""
    h, w = rgb.shape[:2]
    out = np.empty_like(rgb)
    scale = np.empty(3)
    for k in range(3):
        scale[k] = (limit[k] - threshold[k]) / (((1.0 - threshold[k]) / (limit[k] - threshold[k])) ** -power - 1.0) ** (1.0 / power)
    before = np.zeros(h, dtype=np.int64)
    after = np.zeros(h, dtype=np.int64)
    for i in prange(h):
        row_before = 0
        row_after = 0
        values = np.empty(3)
        for j in range(w):
            r, g, b = float(rgb[i, j, 0]), float(rgb[i, j, 1]), float(rgb[i, j, 2])
            if r < 0.0 or g < 0.0 or b < 0.0 or r > 1.0 or g > 1.0 or b > 1.0:
                row_before += 1
            values[0], values[1], values[2] = r, g, b
            if compress:
                a = max(r, g, b)
                for k in range(3):
                    distance = (a - values[k]) / max(abs(a), 1e-9) if a > 0.0 else 0.0
                    if distance > threshold[k]:
                        normal = (distance - threshold[k]) / scale[k]
                        distance = threshold[k] + scale[k] * normal / (1.0 + normal ** power) ** (1.0 / power)
                    values[k] = a - distance * abs(a)
                if values[0] < 0.0 or values[1] < 0.0 or values[2] < 0.0 or values[0] > 1.0 or values[1] > 1.0 or values[2] > 1.0:
                    row_after += 1
            for k in range(3):
                x = min(max(values[k], 0.0), 1.0)
                out[i, j, k] = 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1.0 / 2.4) - 0.055
        before[i] = row_before
        after[i] = row_after
    return out, before.sum(), after.sum()


@njit(fastmath=True)
def _solve(target, base, dyes, weights, total, iterations, a, t):
    """Stage 4: projected Newton for one node, on the wavelengths where the Status weights are not zero. Same steps as
    film_preview.solve_amounts. It stops when the point does not change. Returns the max residual."""
    n = base.shape[0]
    for k in range(3):
        a[k] = max(target[k], 0.0)
    residual = 0.0
    for iteration in range(iterations + 1):
        for w in range(n):
            t[w] = math.exp(-LOG10 * (base[w] + a[0] * dyes[0, w] + a[1] * dyes[1, w] + a[2] * dyes[2, w]))
        jac = np.zeros((3, 3))
        r = np.zeros(3)
        for i in range(3):
            s = 0.0
            for w in range(n):
                s += t[w] * weights[i, w]
            r[i] = -math.log10(s / total[i]) - target[i]
            for d in range(3):
                value = 0.0
                for w in range(n):
                    value += t[w] * weights[i, w] * dyes[d, w]
                jac[i, d] = value / s
        residual = max(abs(r[0]), abs(r[1]), abs(r[2]))
        if iteration == iterations or residual < 1e-11:
            break
        j00, j01, j02 = jac[0, 0] + 1e-9, jac[0, 1], jac[0, 2]
        j10, j11, j12 = jac[1, 0], jac[1, 1] + 1e-9, jac[1, 2]
        j20, j21, j22 = jac[2, 0], jac[2, 1], jac[2, 2] + 1e-9
        c00, c01, c02 = j11 * j22 - j12 * j21, j12 * j20 - j10 * j22, j10 * j21 - j11 * j20
        det = j00 * c00 + j01 * c01 + j02 * c02
        s0 = (r[0] * c00 + r[1] * (j02 * j21 - j01 * j22) + r[2] * (j01 * j12 - j02 * j11)) / det
        s1 = (r[0] * c01 + r[1] * (j00 * j22 - j02 * j20) + r[2] * (j02 * j10 - j00 * j12)) / det
        s2 = (r[0] * c02 + r[1] * (j01 * j20 - j00 * j21) + r[2] * (j00 * j11 - j01 * j10)) / det
        n0, n1, n2 = max(a[0] - s0, 0.0), max(a[1] - s1, 0.0), max(a[2] - s2, 0.0)
        change = abs(n0 - a[0]) + abs(n1 - a[1]) + abs(n2 - a[2])
        a[0], a[1], a[2] = n0, n1, n2
        if change < 1e-12:
            break
    return residual


@njit(parallel=True, fastmath=True, cache=True)
def print_nodes(density, status_target_offset, iterations, m_base, m_dyes, m_weights,
                p_negative_base, p_negative_dyes, p_weights, balance, aim, contrast, flash,
                paper_start, paper_curves, paper_lengths, step,
                s_base, s_dyes, s_weights, v_base, v_dyes, v_weights, v_flare, scale):
    """Stage 4 for N nodes of negative Status M. Returns (XYZ, negative not reached, print not reached, outside the curve)."""
    count = density.shape[0]
    out = np.empty((count, 3))
    m_total = m_weights.sum(axis=1)
    s_total = s_weights.sum(axis=1)
    not_negative = np.zeros(count, dtype=np.int64)
    not_print = np.zeros(count, dtype=np.int64)
    outside = np.zeros(count, dtype=np.int64)
    for node in prange(count):
        a = np.empty(3)
        b = np.empty(3)
        t = np.empty(m_base.shape[0])
        t_paper = np.empty(s_base.shape[0])
        target = density[node] + status_target_offset
        r_negative = _solve(target, m_base, m_dyes, m_weights, m_total, iterations, a, t)
        status = np.empty(3)
        node_outside = 0
        for j in range(3):
            q = 0.0
            for w in range(p_negative_base.shape[0]):
                q += math.exp(-LOG10 * (p_negative_base[w] + a[0] * p_negative_dyes[0, w] + a[1] * p_negative_dyes[1, w]
                                        + a[2] * p_negative_dyes[2, w])) * p_weights[j, w]
            log_h = math.log10(q) + balance[j]
            log_h = aim[j] + contrast[j] * (log_h - aim[j])
            if flash != 0.0:
                log_h = math.log10(10.0 ** log_h + flash * 10.0 ** aim[j])
            c = (log_h - paper_start[j]) / step
            last = paper_lengths[j] - 1
            if c < 0.0 or c > last:
                node_outside += 1
            if c <= 0.0:
                status[j] = paper_curves[j, 0]
            elif c >= last:
                status[j] = paper_curves[j, last]
            else:
                index = int(c)
                status[j] = paper_curves[j, index] + (c - index) * (paper_curves[j, index + 1] - paper_curves[j, index])
        r_print = _solve(status, s_base, s_dyes, s_weights, s_total, iterations, b, t_paper)
        for i in range(3):
            value = 0.0
            for w in range(v_base.shape[0]):
                value += math.exp(-LOG10 * (v_base[w] + b[0] * v_dyes[0, w] + b[1] * v_dyes[1, w] + b[2] * v_dyes[2, w])) * v_weights[i, w]
            out[node, i] = scale * value + v_flare[i]
        not_negative[node] = r_negative > 1e-4
        not_print[node] = r_print > 1e-4
        outside[node] = node_outside
    return out, not_negative.sum(), not_print.sum(), outside.sum()
