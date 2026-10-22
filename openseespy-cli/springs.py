"""Static clay/sand backbone parameters in kN, m (not a cyclic loading model)."""
import math


def effective_stress(plan, depth):
    """Integrate total unit weight, subtracting water weight below the water line."""
    water_depth = -plan['water_elevation_m']
    stress = 0.0
    for layer in plan['layers']:
        top, bottom = -layer['top'], min(depth, -layer['bottom'])
        if bottom <= top:
            continue
        submerged = max(0.0, bottom - max(top, water_depth))
        stress += layer['weight'] * (bottom - top) - plan['opensees']['water_unit_weight_kn_m3'] * submerged
    return stress


def backbone(layer, depth, stress, diameter):
    """Return soilType, distributed pult [kN/m], y50 [m].

    Clay: Matlock shallow/deep capacity and y50=2.5*epsilon50*D.
    Sand: API shallow/deep wedge capacity, static A=max(0.9,3-0.8*z/D),
    and y50 from the half-capacity point of A*pu*tanh(k*z*y/(A*pu)).
    PySimple1 approximates these backbones; it is not OpenPile's exact curve.
    See README references and documented assumptions.
    """
    p = layer['parameters']
    if layer['model'] == 'API_clay':
        su = p['Su']
        capacity = min(9 * su * diameter,
                       (3 * su + stress) * diameter + p['J'] * su * depth)
        return 1, capacity, 2.5 * p['eps50'] * diameter
    phi = math.radians(p['phi'])
    alpha = phi / 2
    beta = math.pi / 4 + alpha
    tb, ta, tp = math.tan(beta), math.tan(alpha), math.tan(phi)
    denominator = math.tan(beta - phi)
    ka = math.tan(math.pi / 4 - alpha)**2
    c1 = (0.4 * tp * math.sin(beta) / (denominator * math.cos(alpha))
          + tb**2 * ta / denominator + 0.4 * tb * (tp * math.sin(beta) - ta))
    c2 = tb / denominator - ka
    c3 = 0.4 * tp * tb**4 + ka * (tb**8 - 1)
    capacity = max(0.9, 3 - 0.8 * depth / diameter) * stress * min(
        c1 * depth + c2 * diameter, c3 * diameter)
    y50 = math.atanh(0.5) * capacity / (p['initial_subgrade_modulus'] * depth)
    return 2, capacity, y50


def mesh_and_springs(plan):
    """Split at layer/water boundaries; attach a spring for each half-element.

    A half-element's capacity is sampled at its midpoint and multiplied by its
    length. Separate springs preserve the two soils at an interface node.
    This also avoids an arbitrary zero-depth sand spring.
    """
    projection = plan.get('projection_height_m', 0.0)
    boundaries = {-projection, 0.0, plan['embedment_m']}
    boundaries.update(-layer['bottom'] for layer in plan['layers'])
    water = -plan['water_elevation_m']
    if 0 < water < plan['embedment_m']:
        boundaries.add(water)
    edges = sorted(boundaries)
    nodes = [edges[0]]
    for start, end in zip(edges, edges[1:]):
        count = math.ceil((end - start) / plan['mesh_m'])
        nodes.extend(start + (end - start) * i / count for i in range(1, count + 1))
    springs = []
    for i, (start, end) in enumerate(zip(nodes, nodes[1:])):
        if end <= 0:
            continue  # Exposed beam has no soil springs. Ground remains a mesh node.
        length = (end - start) / 2
        for node, depth in ((i + 1, start + length / 2), (i + 2, end - length / 2)):
            layer_index, layer = next((j, l) for j, l in enumerate(plan['layers']) if -l['top'] <= depth < -l['bottom'])
            stress = effective_stress(plan, depth)
            soil_type, distributed, y50 = backbone(layer, depth, stress, plan['diameter_m'])
            pult = distributed * length
            if not all(math.isfinite(v) and v > 0 for v in (pult, y50)):
                raise ValueError(f'Invalid spring capacity/displacement at depth {depth} m.')
            springs.append(dict(node=node, layer_index=layer_index, sample_depth_m=depth,
                                tributary_length_m=length, effective_stress_kpa=stress,
                                soil_type=soil_type, pult_kn=pult, y50_m=y50,
                                Cd=plan['opensees']['drag_ratio']))
    return nodes, springs
