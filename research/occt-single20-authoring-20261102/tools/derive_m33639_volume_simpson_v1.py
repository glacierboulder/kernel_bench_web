"""Independent integration of the published torus/cone Boolean geometry.

Use 250 model units as the length unit. The torus has R=3, r=1.
At ordinate y the cone radius is k*(y+4), with k=0.1 and -4<=y<=4.
The X/Z cross-section is integrated using the smaller of the two analytic
heights. Explicit transition ordinates split the outer quadrature.
"""
import argparse
import json
import math
from pathlib import Path


def integrate(function, a, b, tolerance, depth=22):
    if b <= a:
        return 0.0
    middle = (a+b)/2
    fa, fm, fb = function(a), function(middle), function(b)
    estimate = (b-a)*(fa+4*fm+fb)/6

    def refine(left, right, fleft, fmiddle, fright, previous, error, remaining):
        center = (left+right)/2
        fl = function((left+center)/2)
        fr = function((center+right)/2)
        first = (center-left)*(fleft+4*fl+fmiddle)/6
        second = (right-center)*(fmiddle+4*fr+fright)/6
        delta = first+second-previous
        if abs(delta) <= 15*error:
            return first+second+delta/15
        if remaining == 0:
            raise ArithmeticError('quadrature failed its requested convergence test')
        return (refine(left, center, fleft, fl, fmiddle, first, error/2, remaining-1)
                + refine(center, right, fmiddle, fr, fright, second, error/2, remaining-1))

    return refine(a, b, fa, fm, fb, estimate, tolerance, depth)


def roots(a, b, c):
    discriminant = b*b-4*a*c
    if discriminant < 0:
        return []
    return [(-b-math.sqrt(discriminant))/(2*a), (-b+math.sqrt(discriminant))/(2*a)]


def section_area(y, inner_tolerance):
    cone_radius = 0.1*(y+4)
    lower_squared = max(0.0, 4-y*y)
    upper_squared = min(cone_radius*cone_radius, 16-y*y)
    if upper_squared <= lower_squared or cone_radius <= 0:
        return 0.0
    lower, upper = math.sqrt(lower_squared), math.sqrt(upper_squared)
    crossing_rho = (8+y*y+cone_radius*cone_radius)/6
    crossing_squared = crossing_rho*crossing_rho-y*y
    crossing = math.sqrt(max(0.0, crossing_squared))
    torus_end = min(upper, max(lower, crossing))

    def torus_integrand(angle):
        sine, cosine = math.sin(angle), math.cos(angle)
        x = lower+(torus_end-lower)*sine*sine
        height = math.sqrt(max(0.0, 1-(math.hypot(x, y)-3)**2))
        return height*2*(torus_end-lower)*sine*cosine

    torus_part = integrate(torus_integrand, 0, math.pi/2, inner_tolerance)

    def circle_primitive(x):
        ratio = max(-1.0, min(1.0, x/cone_radius))
        return 0.5*(x*math.sqrt(max(0.0, cone_radius*cone_radius-x*x))
                    + cone_radius*cone_radius*math.asin(ratio))

    cone_part = circle_primitive(upper)-circle_primitive(torus_end)
    return 4*(torus_part+cone_part)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    breaks = [-4.0, -2.0, 2.0, 4.0]
    # Cone circle reaches the inner or outer torus radius in the XY plane.
    for radius in [2.0, 4.0]:
        breaks.extend(roots(1.01, 0.08, 0.16-radius*radius))
    # Which analytic height controls the integral at x=0 changes here.
    breaks.extend(roots(1.01, -5.92, 8.16))
    breaks.extend(roots(1.01, 6.08, 8.16))
    breaks = sorted(set(x for x in breaks if -4 <= x <= 4))
    convergence = []
    for epsilon in [1e-8, 1e-10, 1e-12]:
        overlap = sum(integrate(lambda y: section_area(y, epsilon/100), a, b, epsilon/len(breaks))
                      for a, b in zip(breaks, breaks[1:]))
        volume = (2*math.pi*math.pi*3-overlap)*250**3
        convergence.append({'normalized_quadrature_tolerance': epsilon,
                            'overlap_volume': overlap*250**3, 'cut_volume': volume})
    record = {
        'input': {'torus_major_radius': 750, 'torus_minor_radius': 250,
                  'cone_base_radius': 200, 'cone_height': 2000,
                  'cone_base_center': [0, 1000, 0], 'cone_axis': [0, -1, 0]},
        'method': 'Analytic X/Z cross-sections, exact cone circular-segment integral, '
                  'endpoint-regularized torus quadrature, adaptive outer Simpson integration.',
        'normalized_y_breakpoints': breaks,
        'convergence': convergence,
        'predeclared_cut_volume_absolute_limit': 1.0,
        'limits': 'The volume limit allows OCCT construction/intersection approximation. '
                  'Quadrature convergence is numerical evidence, not a certified global bound.',
    }
    args.output.write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(convergence))


if __name__ == '__main__':
    main()
