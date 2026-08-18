import bpy #type: ignore

#post-processing strip helpers
def stitch_strips(strips):
    if not strips:
        return []

    final = strips[0][:]

    for s in strips[1:]:
        if not s:
            continue

        # Insert degenerate bridge
        final.extend([
            final[-1],  # repeat last vertex of current strip
            s[0],       # jump to next strip
            s[0]        # repeat first vertex of next strip
        ])

        final.extend(s[1:])

    return final

def dist(a, b, vert_pos):
    ax, ay = vert_pos[a]
    bx, by = vert_pos[b]
    return (ax - bx)**2 + (ay - by)**2  # squared distance (faster)

def reorder_strips(strips, vert_pos):
    if not strips:
        return []

    remaining = strips[:]
    ordered = [remaining.pop(0)]

    while remaining:
        last = ordered[-1]
        last_end = last[-1]

        best_idx = None
        best_score = float('inf')
        best_strip = None

        for i, s in enumerate(remaining):
            # forward
            d1 = dist(last_end, s[0], vert_pos)

            # reversed
            d2 = dist(last_end, s[-1], vert_pos)

            if d1 < best_score:
                best_score = d1
                best_idx = i
                best_strip = s

            if d2 < best_score:
                best_score = d2
                best_idx = i
                best_strip = list(reversed(s))

        ordered.append(best_strip)
        remaining.pop(best_idx)

    return ordered

#strip helpers
def get_third_vertex(tri, edge):
    return next(v for v in tri if v not in edge)


def get_adjacent_triangle(current_tri, edge, edge_map):
    key = tuple(sorted(edge))
    tris = edge_map[key]

    if len(tris) < 2:
        return None  # boundary

    return tris[0] if tris[1] == current_tri else tris[1]

def lookahead_score(candidate, tris, edge_map, visited, unused_tris, depth):
    tri, edge, _ = candidate

    score = 0
    local_visited = set(visited)

    current_tri = tri
    current_edge = edge

    for _ in range(depth):
        next_tri = get_adjacent_triangle(current_tri, current_edge, edge_map)

        if next_tri is None or next_tri in local_visited or next_tri not in unused_tris:
            break

        next_indices = tris[next_tri]
        new_vert = get_third_vertex(next_indices, current_edge)

        local_visited.add(next_tri)
        score += 1

        current_edge = (current_edge[1], new_vert)
        current_tri = next_tri

    return score

def get_possible_next_tris(current_tri, current_edge, tris, edge_map, visited, unused_tris):
    candidates = []

    next_tri = get_adjacent_triangle(current_tri, current_edge, edge_map)

    if next_tri is None or next_tri in visited or next_tri not in unused_tris:
        return candidates

    next_indices = tris[next_tri]
    new_vert = get_third_vertex(next_indices, current_edge)

    # Option 1: standard forward
    edge1 = (current_edge[1], new_vert)
    candidates.append((next_tri, edge1, new_vert))

    return candidates

def grow_direction(current_tri, current_edge, tris, edge_map, visited, unused_tris):
    grown = []

    while True:
        candidates = get_possible_next_tris(current_tri, current_edge, tris, edge_map, visited, unused_tris)
        if not candidates:
            break

        depth = 3 if len(unused_tris) > 20 else 10

        best_tri, best_edge, new_vert = max(
            candidates,
            key=lambda c: lookahead_score(c, tris, edge_map, visited, unused_tris, depth)
        )

        if best_tri not in unused_tris:
            break

        grown.append(new_vert)
        visited.add(best_tri)
        current_tri = best_tri
        current_edge = best_edge

    return grown

def grow_strip(start_tri_index, start_edge, tris, edge_map, unused_tris):
    tri_indices = tris[start_tri_index]

    v1, v2 = start_edge
    v0 = get_third_vertex(tri_indices, start_edge)

    visited = {start_tri_index}

    forward = grow_direction(
        start_tri_index,
        (v2, v0),
        tris,
        edge_map,
        visited,
        unused_tris
    )

    backward = grow_direction(
        start_tri_index,
        (v0, v1),
        tris,
        edge_map,
        visited,
        unused_tris
    )

    strip = list(reversed(backward)) + [v1, v2, v0] + forward

    a, b, c = strip[0:3]
    src = tris[start_tri_index]

    if (a, b, c) != src:
        # flip strip phase
        strip[0], strip[1] = strip[1], strip[0]
    return strip, visited

def stripify(tris, vert_pos=None):
    edge_map = {}
    
    for tri_index, indices in enumerate(tris):
        a, b, c = indices
        edges = [
            tuple(sorted((a, b))),
            tuple(sorted((b, c))),
            tuple(sorted((c, a))),
        ]
        
        for edge in edges:
            if edge not in edge_map:
                edge_map[edge] = []
            edge_map[edge].append(tri_index)
            
    boundary_edges = {
        edge: tris
        for edge, tris in edge_map.items()
        if len(tris) == 1
    }
    
    start_candidates = []

    for edge, tri_list in boundary_edges.items():
        tri_index = tri_list[0]
        start_candidates.append((tri_index, edge))

    unused_tris = set(range(len(tris)))
        
    print("\n--- Strip Growth ---")

    all_strips = []

    while unused_tris:
        best_strip = None
        best_used = set()

        for tri_index, edge in start_candidates:
            if tri_index not in unused_tris:
                continue

            strip, visited = grow_strip(
                tri_index, edge, tris, edge_map, unused_tris
            )

            if best_strip is None or len(visited) > len(best_used):
                best_strip = strip
                best_used = visited
                best_start = (tri_index, edge)

        if best_strip:
            print(f"\nSELECTED Start Tri {best_start[0]}, Edge {best_start[1]}")
            print(f"Final Strip: {best_strip}")

        if not best_strip:
            break

        all_strips.append(best_strip)
        unused_tris -= best_used

    final_strip = stitch_strips(all_strips)
    print(f"\n--- Final Stitched Strip ---\n{final_strip}")

    #print("\n--- TRIANGLES FROM FINAL STRIP ---")
    for i in range(len(final_strip) - 2):
        a, b, c = final_strip[i:i+3]
        #print((a, b, c))

    return all_strips
    
#stripify_object(bpy.context.object, bpy.context)