"""Derive M24097's section independently from the serialized input surfaces.

The first face is a bicubic tensor patch. The second is a linear extrusion
of a degree-four B-spline along X. Solve the two Y/Z equations for the patch
parameters at each basis-curve parameter. No OCCT intersection or F output is
used. The finite polylines provide a convergence check, not a global bound.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def cubic(t):
    return [(1-t)**3, 3*t*(1-t)**2, 3*t*t*(1-t), t**3]


def derivative(t):
    return [-3*(1-t)**2, 3*(1-t)*(1-3*t), 3*t*(2-3*t), 3*t*t]


def patch_value(poles, u, v, du=False, dv=False):
    bu = derivative(u) if du else cubic(u)
    bv = derivative(v) if dv else cubic(v)
    return [sum(bu[i]*bv[j]*poles[i][j][axis] for i in range(4) for j in range(4))
            for axis in range(3)]


def curve_value(poles, knots, degree, parameter):
    span = len(poles)-1
    if parameter < knots[len(poles)]:
        span = next(i for i in range(degree, len(poles))
                    if knots[i] <= parameter < knots[i+1])
    values = [list(poles[span-degree+j]) for j in range(degree+1)]
    for level in range(1, degree+1):
        for j in range(degree, level-1, -1):
            i = span-degree+j
            alpha = (parameter-knots[i])/(knots[i+degree-level+1]-knots[i])
            values[j] = [(1-alpha)*values[j-1][axis]+alpha*values[j][axis]
                         for axis in range(3)]
    return values[degree]


def point_on_section(patch, curve, knots, parameter):
    target = curve_value(curve, knots, 4, parameter)
    u = target[2]-19
    v = (17.73590088-target[1])/2.4
    for iteration in range(20):
        point = patch_value(patch, u, v)
        residual_y, residual_z = point[1]-target[1], point[2]-target[2]
        if math.hypot(residual_y, residual_z) < 2e-13:
            break
        du = patch_value(patch, u, v, du=True)
        dv = patch_value(patch, u, v, dv=True)
        determinant = du[1]*dv[2]-dv[1]*du[2]
        if abs(determinant) < 1e-12:
            raise ValueError('singular independent surface equations')
        u -= (residual_y*dv[2]-residual_z*dv[1])/determinant
        v -= (du[1]*residual_z-du[2]*residual_y)/determinant
    else:
        raise ValueError('independent surface equations did not converge')
    if not (0 <= u <= 1 and 0 <= v <= 1 and -400 <= -78.64-point[0] <= 0):
        raise ValueError('derived intersection leaves the trimmed input domains')
    return point, u, v, math.hypot(residual_y, residual_z)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    first = args.input_dir/'bug24097_face1.brep'
    second = args.input_dir/'bug24097_face2.brep'
    lines = first.read_text().split('Surfaces 5\n', 1)[1].splitlines()
    header = lines[0].split()
    if header[:11] != ['9', '0', '0', '0', '0', '3', '3', '4', '4', '2', '2']:
        raise ValueError('unexpected bicubic patch format')
    coordinates = list(map(float, header[11:] + ' '.join(lines[1:4]).split()))
    patch = [[coordinates[(i*4+j)*3:(i*4+j+1)*3] for j in range(4)] for i in range(4)]
    lines = second.read_text().split('Surfaces 3\n', 1)[1].splitlines()
    if list(map(float, lines[0].split())) != [6, -1, 0, 0]:
        raise ValueError('expected X-directed extrusion')
    header = lines[1].split()
    if header[:6] != ['7', '0', '0', '4', '101', '34']:
        raise ValueError('unexpected extrusion basis format')
    coordinates = list(map(float, header[6:]))
    curve = [coordinates[i:i+3] for i in range(0, len(coordinates), 3)]
    if len(curve) != 101:
        raise ValueError('unexpected number of basis poles')
    pairs = lines[2].split()
    knots = []
    for i in range(0, len(pairs), 2):
        knots.extend([float(pairs[i])]*int(pairs[i+1]))
    if len(knots) != 106:
        raise ValueError('unexpected knot multiplicity')
    # Derivatives of a Bezier patch lie in the convex hull of its derivative
    # control points. These bounds establish a unique Y/Z inverse throughout
    # this input rectangle, independently of the numerical Newton iterates.
    du_poles = [[3*(patch[i+1][j][axis]-patch[i][j][axis]) for axis in range(3)]
                for i in range(3) for j in range(4)]
    dv_poles = [[3*(patch[i][j+1][axis]-patch[i][j][axis]) for axis in range(3)]
                for i in range(4) for j in range(3)]
    z_u_min = min(point[2] for point in du_poles)
    y_v_max = max(point[1] for point in dv_poles)
    y_u_bound = max(abs(point[1]) for point in du_poles)
    z_v_bound = max(abs(point[2]) for point in dv_poles)
    y_at_fixed_z_upper = y_v_max + y_u_bound*z_v_bound/z_u_min
    y_min, y_max = min(p[1] for p in curve), max(p[1] for p in curve)
    z_min, z_max = min(p[2] for p in curve), max(p[2] for p in curve)
    domain_bracketed = (
        max(p[2] for p in patch[0]) < z_min
        and min(p[2] for p in patch[-1]) > z_max
        and min(row[0][1] for row in patch) > y_max
        and max(row[-1][1] for row in patch) < y_min
    )
    if z_u_min <= 0 or y_at_fixed_z_upper >= 0 or not domain_bracketed:
        raise ValueError('global uniqueness/domain argument does not apply to these inputs')
    convergence = []
    samples = []
    worst = 0.0
    for intervals in [256, 512, 1024, 2048]:
        samples = [point_on_section(patch, curve, knots, i/intervals)
                   for i in range(intervals+1)]
        length = sum(math.dist(samples[i][0], samples[i+1][0]) for i in range(intervals))
        worst = max(worst, max(row[3] for row in samples))
        convergence.append({'intervals': intervals, 'polyline_length': length})
    result = {
        'method': 'Independent de Boor evaluation plus bicubic Y/Z Newton solve',
        'input_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [first, second]},
        'original_upstream_approximate_length': 0.125,
        'convergence': convergence,
        'maximum_equation_residual': worst,
        'global_inverse_checks': {
            'z_u_derivative_lower_bound': z_u_min,
            'y_derivative_at_fixed_z_upper_bound': y_at_fixed_z_upper,
            'basis_y_range': [y_min, y_max],
            'basis_z_range': [z_min, z_max],
            'entire_basis_range_bracketed_by_patch': domain_bracketed,
            'argument': 'Z increases strictly in U. At fixed Z, Y decreases strictly in V. '
                        'The patch boundaries bracket the whole basis-curve convex hull. '
                        'Each basis parameter therefore has exactly one interior patch point.',
        },
        'witnesses': [{'basis_parameter': i/2048, 'point': samples[i][0],
                       'patch_u': samples[i][1], 'patch_v': samples[i][2]}
                      for i in [0, 256, 512, 768, 1024, 1280, 1536, 1792, 2048]],
        'bounds': 'All derived points lie inside both finite parameter rectangles.',
        'limits': 'Finite convergence and witnesses do not certify a global continuous error bound.',
    }
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'length': length, 'maximum_equation_residual': worst,
                      'endpoints': [samples[0][0], samples[-1][0]]}))


if __name__ == '__main__':
    main()
