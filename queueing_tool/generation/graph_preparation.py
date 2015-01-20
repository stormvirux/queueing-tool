import graph_tool.all as gt
import numpy          as np

def prepare_graph(g, g_colors, q_cls, q_arg, q_colors, graph_type=None) :
    if isinstance(g, str) :
        g = gt.load_graph(g, fmt='xml')
    elif not isinstance(g, gt.Graph) :
        raise Exception("Need to supply a graph (or the location of a graph) when initializing")

    g.reindex_edges()
    vertex_t_color    = g.new_vertex_property("vector<double>")
    vertex_pen_color  = g.new_vertex_property("vector<double>")
    vertex_color      = g.new_vertex_property("vector<double>")
    halo_color        = g.new_vertex_property("vector<double>")
    vertex_t_size     = g.new_vertex_property("double")
    vertex_halo_size  = g.new_vertex_property("double")
    vertex_pen_width  = g.new_vertex_property("double")
    vertex_size       = g.new_vertex_property("double")

    control           = g.new_edge_property("vector<double>")
    edge_color        = g.new_edge_property("vector<double>")
    edge_t_color      = g.new_edge_property("vector<double>")
    edge_width        = g.new_edge_property("double")
    arrow_width       = g.new_edge_property("double")
    edge_length       = g.new_edge_property("double")
    edge_times        = g.new_edge_property("double")
    edge_t_size       = g.new_edge_property("double")
    edge_t_distance   = g.new_edge_property("double")
    edge_t_parallel   = g.new_edge_property("bool")

    vertex_props = set()
    for key in g.vertex_properties.keys() :
        vertex_props.add(key)

    edge_props = set()
    for key in g.edge_properties.keys() :
        edge_props.add(key)

    if graph_type == 'osm' :
        has_garage  = 'garage' in vertex_props
        has_destin  = 'destination' in vertex_props
        has_light   = 'light' in vertex_props
        has_egarage = 'garage' in edge_props
        has_edestin = 'destination' in edge_props
        has_elight  = 'light' in edge_props

        vType   = g.new_vertex_property("int")
        eType   = g.new_edge_property("int")
        for v in g.vertices() :
            if has_garage and g.vp['garage'][v] :
                e = g.edge(v,v)
                if isinstance(e, gt.Edge) :
                    eType[e]  = 1
                vType[v]    = 1
            if has_destin and g.vp['destination'][v] :
                e = g.edge(v,v)
                if isinstance(e, gt.Edge) :
                    eType[e]  = 2
                vType[v]  = 2
            if has_light and g.vp['light'][v] :
                e = g.edge(v,v)
                if isinstance(e, gt.Edge) :
                    eType[e]  = 3
                vType[v]  = 3

        for e in g.edges() :
            if has_egarage and g.ep['garage'][e] :
                eType[e]  = 1
            if has_edestin and g.ep['destination'][e] :
                eType[e]  = 2
            if has_elight and g.ep['light'][e] :
                eType[e]  = 3

        g.vp['vType'].a = vType.a + 1
        g.ep['eType'].a = eType.a + 1

    if 'pos' not in vertex_props :
        g.vp['pos'] = gt.sfdp_layout(g, epsilon=1e-2, cooling_step=0.95)

    nV  = g.num_vertices()
    nE  = g.num_edges()

    has_length  = 'edge_length' in edge_props
    queues      = set_queues(g, q_colors, q_cls, q_arg, 'cap' in vertex_props)

    for k, e in enumerate(g.edges()) :
        p2  = np.array(g.vp['pos'][e.target()])
        p1  = np.array(g.vp['pos'][e.source()])
        edge_length[e]  = g.ep['edge_length'][e] if has_length else np.linalg.norm(p1 - p2)
        edge_t_color[e] = [0, 0, 0, 1]
        if e.target() == e.source() :
            edge_color[e] = [0, 0, 0, 0]
        else :
            control[e]    = [0, 0, 0, 0]
            edge_color[e] = queues[k].colors['edge_normal']

    for v in g.vertices() :
        e = g.edge(v, v)
        vertex_t_color[v] = g_colors['text_normal']
        halo_color[v]     = g_colors['halo_normal']
        if isinstance(e, gt.Edge) :
            vertex_pen_color[v] = queues[g.edge_index[e]].current_color('pen')
            vertex_color[v]     = queues[g.edge_index[e]].current_color()
        else :
            vertex_pen_color[v] = [0.0, 0.5, 1.0, 1.0]
            vertex_color[v]     = g_colors['vertex_normal'] 

    edge_width.a  = 1.25
    arrow_width.a = 8
    edge_times.a  = 1
    edge_t_size.a = 8
    edge_t_distance.a = 8

    vertex_t_size.a     = 8
    vertex_halo_size.a  = 1.3
    vertex_pen_width.a  = 1.1
    vertex_size.a       = 8

    g.vp['vertex_t_color']   = vertex_t_color
    g.vp['vertex_pen_color'] = vertex_pen_color
    g.vp['vertex_color']     = vertex_color
    g.vp['halo_color']       = halo_color
    g.vp['vertex_t_pos']     = g.new_vertex_property("double")
    g.vp['vertex_t_size']    = vertex_t_size
    g.vp['vertex_halo_size'] = vertex_halo_size
    g.vp['vertex_pen_width'] = vertex_pen_width
    g.vp['vertex_size']      = vertex_size
    g.vp['text']             = g.new_vertex_property("string")
    g.vp['halo']             = g.new_vertex_property("bool")

    g.ep['edge_t_size']      = edge_t_size
    g.ep['edge_t_distance']  = edge_t_distance
    g.ep['edge_t_parallel']  = g.new_edge_property("bool")
    g.ep['edge_t_color']     = edge_t_color
    g.ep['text']             = g.new_edge_property("string")
    g.ep['control']          = control
    g.ep['edge_color']       = edge_color
    g.ep['edge_width']       = edge_width
    g.ep['edge_length']      = edge_length
    g.ep['arrow_width']      = arrow_width
    g.ep['edge_times']       = edge_times
    return g, queues


def set_queues(g, colors, q_cls, q_arg, has_cap) :
    queues    = [0 for k in range(g.num_edges())]

    for e in g.edges() :
        qedge = (int(e.source()), int(e.target()), g.edge_index[e])
        eType = g.ep['eType'][e]

        if has_cap and 'nServers' not in q_arg[eType] :
            q_arg[eType]['nServers'] = max(g.vp['cap'][e.target()] // 2, 1)

        queues[qedge[2]] = q_cls[eType](edge=qedge, **q_arg[eType])
        #queues[qedge[2]].colors = colors[eType]

    return queues