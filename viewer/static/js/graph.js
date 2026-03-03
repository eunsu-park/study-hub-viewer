/**
 * Topic Dependency Graph — D3.js force-directed visualization.
 * Shared between viewer/ and site/.
 *
 * Expected globals:
 *   window.GRAPH_DATA      — { nodes: [...], links: [...] }
 *   window.GRAPH_TOPIC_URL — URL template, e.g. "/en/{topic}/" (replace {topic})
 */
(function () {
    'use strict';

    const data = window.GRAPH_DATA;
    if (!data || !data.nodes.length) return;

    const TIER_Y = { beginner: 0.12, intermediate: 0.36, advanced: 0.62, expert: 0.88 };

    const container = document.getElementById('graph-container');
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

    // Arrow marker
    svg.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', 'var(--text-muted, #adb5bd)');

    const g = svg.append('g');

    // Zoom
    const zoom = d3.zoom()
        .scaleExtent([0.3, 3])
        .on('zoom', (event) => g.attr('transform', event.transform));
    svg.call(zoom);

    // Node radius based on lesson count
    const lessonExtent = d3.extent(data.nodes, d => d.lessons);
    const rScale = d3.scaleSqrt().domain(lessonExtent).range([6, 18]);

    // Links
    const linkGroup = g.append('g').attr('class', 'graph-links');
    const link = linkGroup.selectAll('line')
        .data(data.links)
        .join('line')
        .attr('class', 'graph-link')
        .attr('marker-end', 'url(#arrowhead)');

    // Nodes
    const nodeGroup = g.append('g').attr('class', 'graph-nodes');
    const node = nodeGroup.selectAll('g')
        .data(data.nodes)
        .join('g')
        .attr('class', 'graph-node')
        .style('cursor', 'pointer');

    node.append('circle')
        .attr('r', d => rScale(d.lessons))
        .attr('fill', d => d.color)
        .attr('stroke', 'var(--bg-primary, #fff)')
        .attr('stroke-width', 2);

    node.append('text')
        .text(d => d.label)
        .attr('dx', d => rScale(d.lessons) + 4)
        .attr('dy', '0.35em')
        .attr('font-size', '11px');

    // Simulation
    const simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.links).id(d => d.id).distance(80))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('collide', d3.forceCollide().radius(d => rScale(d.lessons) + 20))
        .force('x', d3.forceX(width / 2).strength(0.05))
        .force('y', d3.forceY(d => TIER_Y[d.tier] * height || height / 2).strength(0.3))
        .on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });

    // Drag
    const drag = d3.drag()
        .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        })
        .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
        })
        .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        });
    node.call(drag);

    // Build adjacency for hover highlight
    const linkedNodes = new Set();
    const adjacency = {};
    data.links.forEach(l => {
        const sid = typeof l.source === 'object' ? l.source.id : l.source;
        const tid = typeof l.target === 'object' ? l.target.id : l.target;
        if (!adjacency[sid]) adjacency[sid] = new Set();
        if (!adjacency[tid]) adjacency[tid] = new Set();
        adjacency[sid].add(tid);
        adjacency[tid].add(sid);
    });

    function getConnected(id) {
        const s = new Set([id]);
        if (adjacency[id]) adjacency[id].forEach(n => s.add(n));
        return s;
    }

    // Hover highlight
    node.on('mouseenter', (event, d) => {
        const connected = getConnected(d.id);
        node.classed('dimmed', n => !connected.has(n.id));
        node.classed('highlighted', n => connected.has(n.id));
        link.classed('dimmed', l => {
            const sid = typeof l.source === 'object' ? l.source.id : l.source;
            const tid = typeof l.target === 'object' ? l.target.id : l.target;
            return !connected.has(sid) || !connected.has(tid);
        });
    }).on('mouseleave', () => {
        node.classed('dimmed', false).classed('highlighted', false);
        link.classed('dimmed', false);
    });

    // Click to navigate
    node.on('click', (event, d) => {
        if (event.defaultPrevented) return; // ignore drag
        const url = window.GRAPH_TOPIC_URL.replace('{topic}', d.id);
        window.location.href = url;
    });

    // Responsive resize
    const ro = new ResizeObserver(entries => {
        for (const entry of entries) {
            const w = entry.contentRect.width;
            const h = entry.contentRect.height;
            svg.attr('width', w).attr('height', h);
            simulation.force('x', d3.forceX(w / 2).strength(0.05));
            simulation.force('y', d3.forceY(d => TIER_Y[d.tier] * h || h / 2).strength(0.3));
            simulation.alpha(0.3).restart();
        }
    });
    ro.observe(container);
})();
