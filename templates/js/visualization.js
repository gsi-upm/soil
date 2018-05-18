
;(function(undefined) {
  "use strict";

  /**
   * Graph Visualization
   * ===================
   *
   * Author: Tasio Méndez (tasiomendez)
   * URL: https://github.com/tasiomendez/
   * Version: 0.1
   */

  // Private constants
  var focus_opacity = 0.1,
      radius = 8,
      shape_size = 16,
      required_node = ['id', 'index', 'label', 'px', 'py', 'spells', 'weight', 'x', 'y', 'pos', 'scx', 'scy'];

  // Private variables
  var width,
      height,
      graph,              // JSON data for the graph
      model,              // Definition of the attributes of the nodes
      linkedByIndex,      // Nodes linked by index
      name,               // Name of the graph (id for svg item)
      svg,                // Svg item
      force,              // Set up the force layout
      color,              // Color for nodes
      zoom,               // Zoom

      groot,              // Append sections to svg to have nodes and edges separately
      graph_wrapper,
      glinks,
      gnodes,
      background_image,
      background_opacity,
      background_filter_color,
      data_node,          // Actual node data for the graph
      data_link,          // Actual link data for the graph

      link,               // Line svgs
      node,               // Circles for the nodes
      shape_property,     // Property to whom the shape will be applied
      shapes,             // Dictionary of shapes for nodes
      colors,             // Dictionary of colors for nodes
      background;         // Background of the graph

  Number.prototype.between = function(min, max) {
    var min = (min || min === 0) ? min : Math.max(),
        max = (max || max === 0) ? max : Math.min();

    return ( this > min && this <= max ) || ( min === 0 && this === 0 );
  };

  Number.prototype.is_type = function() {
    if ( typeof(this) === 'number' )
      return ( Number.isInteger(this) ) ? 'int' :  'float';
    else 
      return false;
  }

  String.prototype.is_type = function() {
    return "string";
  }

  var lastFocusNode;
  var _helpers = {
    set_node: function(node, property, time) {
      // Add nodes if data has more nodes than before
      node.enter().append('circle')
          .attr('class', 'node')
          .attr('r', radius)
          .style('fill', function (d) {
              if ( Array.isArray(d[property]) ) {
                var color_node = _helpers.set_color(property, d[property][0][0]);
                d[property].forEach(function(p) {
                  if ( time.between(p[1], p[2]) ) color_node = _helpers.set_color(property, p[0]);
                });
                return color_node;
              } else {
                return _helpers.set_color(property, d[property]);
              }
          })
          .style('stroke', function(d) {
              if (_helpers.set_shape(d[shape_property]) !== (-1))
                if ( Array.isArray(d[property]) ) {
                  var color_node = _helpers.set_color(property, d[property][0][0]);
                  d[property].forEach(function(p) {
                    if ( time.between(p[1], p[2]) ) color_node = _helpers.set_color(property, p[0]);
                  });
                  return color_node;
                } else {
                  return _helpers.set_color(property, d[property]);
                }
              else 
                return '#ffffff';
          })
          // Cancel zoom movement so you can move the node
          .on('mousedown', function(d) {
              d3.event.stopPropagation();
          })
          // Double-click to focus neighbours
          .on('dblclick', function(d) {
              d3.event.stopPropagation();
              if (d === lastFocusNode) {
                  lastFocusNode = undefined;
                  node.style('opacity', 1);
                  link.style('opacity', 1);
              } else {
                  lastFocusNode = d;
                  _helpers.set_focus(d);
              }
          }).call(force.drag);

      // Remove nodes if data has less nodes than before
      node.exit().remove();

      // Update existing nodes
      node.attr('class', 'node')
          .attr('r', radius)
          .style('fill', function (d) {
              if (_helpers.set_shape(d[shape_property]) !== (-1)) {
                return 'url(#' + _helpers.set_shape(d[shape_property]) + ')';
              }
              if ( Array.isArray(d[property]) ) {
                var color_node = _helpers.set_color(property, d[property][0][0]);
                d[property].forEach(function(p) {
                  if ( time.between(p[1], p[2]) ) color_node = _helpers.set_color(property, p[0]);
                });
                return color_node;
              } else {
                return _helpers.set_color(property, d[property]);
              }
          })
          .style('stroke', function(d) {
              if (_helpers.set_shape(d[shape_property]) !== (-1))
                if ( Array.isArray(d[property]) ) {
                  var color_node = _helpers.set_color(property, d[property][0][0]);
                  d[property].forEach(function(p) {
                    if ( time.between(p[1], p[2]) ) color_node = _helpers.set_color(property, p[0]);
                  });
                  return color_node;
                } else {
                  return _helpers.set_color(property, d[property]);
                }
              else 
                return '#ffffff';
          })
          .on('dblclick', function(d) {
            d3.event.stopPropagation();
            if (d === lastFocusNode) {
                lastFocusNode = undefined;
                node.style('opacity', 1);
                link.style('opacity', 1);
            } else {
                lastFocusNode = d;
                _helpers.set_focus(d);
            }
          });
    },
    set_link: function(link) {
      // Remove links if data has more links than before
      link.enter().append('line')
          .attr('class', 'link')
          .style('stroke-width', function (d) {
              return Math.sqrt(d.value);
          });

      // Remove links if data has less links than before
      link.exit().remove();
    },
    isConnected: function(source, neighbour) {
      return linkedByIndex[source.id + ',' + neighbour.id] || 
              linkedByIndex[neighbour.id + ',' + source.id];
    },
    set_focus: function(d) {
      node.style('opacity', function(o) {
          return _helpers.isConnected(d,o) || d.index == o.index ? 1 : focus_opacity;
      });
      link.style('opacity', function(o) {
          return o.source.index == d.index || o.target.index == d.index ? 1 : focus_opacity;
      });
    },
    push_once: function(array, item, key) {
      for (var i in array) {
        if ( array[i][key] == item[key] ) return false;
      }
      array.push(item);
      return true;
    },
    set_color: function(property, value) {
      if ( colors instanceof Array ) {
        for ( var c in colors ) {
          if ( colors[c][property] == value ) { return colors[c]['color']; }
        }
        return color(value);
      } else {
        return color(value);
      }
    },
    set_shape: function(value) {
      if ( shapes instanceof Object && shape_property ) {
        for ( var s in shapes ) {
          var str_value = (value.includes('class')) ? value.split('.').pop().split('\'')[0] : value;
          if ( str_value == s ) return shapes[s];
        }
        return (-1);
      } else {
        return (-1);
      }
    }
  }


  /**
   * Graph Visualization Core Functions
   * ----------------------------------
   *
   * The graph visualization functions themselves.
   */

  function Graph() {
    // Color
    color = d3.scale.category20();

    // Set up the force layout
    force = d3.layout.force()
                     .charge(-500)
                     .linkDistance(30)
                     .size([width, height]);

    // Append sections to svg to have nodes and edges separately
    groot  = svg.append('g').attr('id', 'root');

    // Set background
    if ( background !== undefined ) {
      var rect = groot.append('rect').attr('fill', background_filter_color);
      background_image = groot.append('image').attr('href', background).style('opacity', background_opacity);
      graph_wrapper = groot.append('g')   .attr('id', 'graph-wrapper');
      glinks = graph_wrapper.append('g')  .attr('id', 'links');
      gnodes = graph_wrapper.append('g')  .attr('id', 'nodes');
    } else {
      glinks = groot.append('g')  .attr('id', 'links');
      gnodes = groot.append('g')  .attr('id', 'nodes');
    }

    // Add patterns for shapes
    var defs = [];
    for ( var i in shapes )
      if (!defs.includes(shapes[i])) defs.push(shapes[i])
    
    svg.append('defs')
       .selectAll('pattern')
       .data(defs)
       .enter()
       .append('pattern')
       .attr('id', function(d, i) {
          return d;
       })
       .attr('patternUnits', 'objectBoundingBox')
       .attr('width', 1)
       .attr('height', 1)
       .append('image')
       .attr('href', function(d) {
          return window.location.protocol + '//' + window.location.host + '/img/svg/' + d + '.svg';
       })
       .attr('width', shape_size)
       .attr('height', shape_size);

    // Zoom
    zoom = d3.behavior
             .zoom()
             .scaleExtent([1/5, 10])
             .on('zoom', function () {
                //console.trace("zoom", d3.event.translate, d3.event.scale);
                groot.attr('transform',
                        'translate(' + d3.event.translate + ')scale(' + d3.event.scale     + ')');
            });

    // Activate zoom for the svg item
    svg.style('background-color', 'rgb(255,255,255)')
       .call(zoom);

    // Update linkedByIndex 
    linkedByIndex = {};
    graph.links.forEach(function(d) {
        linkedByIndex[d.source.id + ',' + d.target.id] = true;
    });

    // Creates the graph data structure out of the json data
    force.nodes(graph.nodes)
         .links(graph.links)
         .start();

    // Now we are giving the SVGs coordinates - the force layout is generating the coordinates 
    // which this code is using to update the attributes of the SVG elements
    force.on('tick', function () {

        link.attr('x1', function (d) {
            if ( d.source.scx ) return d.source.scx;
            else return d.source.x;
        }).attr('y1', function (d) {
            if ( d.source.scy ) return d.source.scy;
            else return d.source.y;
        }).attr('x2', function (d) {
            if ( d.target.scx ) return d.target.scx;
            else return d.target.x;
        }).attr('y2', function (d) {
            if ( d.target.scy ) return d.target.scy;
            else return d.target.y;
        });

        node.attr('transform',  function translate(d) {
            if ( d.scx || d.scy ) return 'translate(' + d.scx + ',' + d.scy + ')';
            else return 'translate(' + d.x + ',' + d.y + ')';
        });
    });

  }

  function update_data(property, time) {

    // Reset data
    var delete_links = true;
    data_node = [];
    data_link = graph.links.slice();

    // Nodes 
    graph.nodes.forEach(function(node) {
      if (Array.isArray(node.spells)) {
          node.spells.forEach( function(d) {
            if ( time.between(d[0], d[1]) ) {
              data_node.push(node);
            } else {
              graph.links.forEach(function(link) {
                if (link.source === node || link.target === node)
                    data_link.splice(data_link.indexOf(link), 1);
              });
            }
          });

      } else {
          data_node.push(node);
      }
    });

    // Links
    graph.links.forEach(function(link) {
      if ( !(time.between(link.start, link.end)) && data_link.includes(link) )
          data_link.splice(data_link.indexOf(link), 1);
    });

    // Reset force
    force.stop()
         .nodes(data_node)
         .links(data_link)
         .start();

    // Create all the line svgs but without locations
    link = glinks.selectAll('.link').data(data_link);
    _helpers.set_link(link);

    // Do the same with the circles for the nodes - no
    node = gnodes.selectAll('.node').data(data_node);
    _helpers.set_node(node, property, time);

    // Node Attributes
    var statistics = {}
    self.GraphVisualization.statistics = {};
    data_node.forEach(function(n) {
      // Count node properties
      if ( Array.isArray(n[property]) ) {
        n[property].forEach(function(p) {
          if ( time.between(p[1], p[2]) ) statistics[p[0]] = (!statistics[p[0]]) ? 1 : statistics[p[0]] + 1;
        });
      } else {  statistics[n[property]] = (!statistics[n[property]]) ? 1 : statistics[n[property]] + 1; }
    });
    for ( i in statistics ) {
      statistics[i] = (statistics[i] / data_node.length * 100).toFixed(2);
    }
    self.GraphVisualization.statistics = statistics
  }

  function get_models(graph) {

    var models = { 'dynamic': [], 'static': [] }

    graph['nodes'].forEach(function(node) {
      for ( var att in node ) {
        if (!required_node.includes(att)) {
          if ( Array.isArray(node[att]) ) _helpers.push_once(models['dynamic'], { 'title': att, 'type': node[att][0][0].is_type() }, 'title');
          else _helpers.push_once(models['static'], { 'title': att, 'type': typeof(node[att]) }, 'title');
        }
      }
    });

    return models;
  }


  /**
   * Public API
   * -----------
   *
   * User-accessible functions.
   */

  /**
   * Create the space where the graph will we drawn.
   * A function that identifies the svg item.
   *
   * @param   {object}    id            The id of the svg item.
   * @return  {object}                  This class.
   */
  function create(id, n_height, n_width, callback) {
    name = id;
    svg = d3.select('svg#' + name)
            .attr('width', n_width)
            .attr('height', n_height)
            .style('background-color', 'rgba(128,128,128,0.1)');

    height  = n_height;
    width   = n_width

    if (callback) { callback(this.GraphVisualization);  }
    else          { return this.GraphVisualization      }
  }

  /**
   * Import JSON and attributes.
   * A function that imports the graph and the attributes of all the nodes.
   *
   * @param   {object}    json          The json structure of the graph.
   * @param   {object}    callback      A function called at the end.
   */
  function importJSON(json, callback) {
    reset()
    graph = json;

    // Create the graph itself
    Graph();

    self.GraphVisualization.nodes = graph.nodes.length;
    self.GraphVisualization.links = graph.links.length;
    self.GraphVisualization.model = get_models(json);

    // Draw graph with default property and time for the first time
    update_data(self.GraphVisualization.model.dynamic[0].title, 0);

    if (callback) { callback(); }
  }

  /**
   * Set link distance.
   * A function that set the link distance. If it is not called, it uses 30 as default
   *
   * @param   {object}    distance      Distance.
   * @param   {object}    callback      A function called at the end.
   */
  function set_link_distance(distance, callback) {
    if (graph) {
      force.stop().linkDistance(distance).start();

      // Update radius of the nodes to see them better
      var r = d3.scale.linear().domain([30, 1000]).range([8, 24]);
      radius = r(distance);
      node.attr('r', radius);

      var s = d3.scale.linear().domain([30, 1000]).range([16, 48]);
      if ( shapes instanceof Object && shape_property ) {
        svg.selectAll('pattern image').attr('width', s(distance)).attr('height', s(distance));
      }

      if (callback) { callback(radius); }
    }
  }

  /**
   * Set background image.
   * A function that set a background image.
   *
   * @param   {object}    image         Path to image.
   */
  function set_background(image, set_opacity, set_color) {
    background = image;
    background_opacity = set_opacity || 0.8;
    background_filter_color = set_color || 'white';
  }

  /**
   * Set property and instant of time.
   * A function that draws the graph depends on the property and instant of time selected.
   *
   * @param   {object}    property      Property to show.
   * @param   {object}    time          Instant of time.
   * @param   {object}    callback      A function called at the end.
   */
  function update_graph(property, time, callback) {
    if (graph) {
      update_data(property, time);

      if (callback) { callback(); }
    }
  }

  /**
   * Set shapes and color of graph.
   * A function that set the shapes and colors of the nodes depending on their status.
   *
   * @param   {object}    set_shapes    Shapes for nodes.
   * @param   {object}    set_colors    Colors for nodes.
   * @param   {object}    callback      A function called at the end.
   */
  function set_params(set_shape_property, set_shapes, set_colors, callback) {
    shape_property = set_shape_property;
    shapes = set_shapes;
    colors = set_colors;

    self.GraphVisualization.shapes = shapes;
    self.GraphVisualization.colors = colors;

    if (callback) { callback(); }
  }  

  /**
   * Adjust the graph to the whole area.
   * A function that adjust the graph to the svg item.
   *
   * @param   {object}    padding       Space from the graph to the border.
   *                                    85% by default.
   * @param   {object}    transition    Duration of the zoom action.
   *                                    750 milliseconds by default.
   * @param   {object}    callback      A function called at the end.
   */
  function zoom_to_fit(padding, transition, callback) {

    var bounds = groot.node().getBBox();
    var parent = groot.node().parentElement;
    var fullWidth = parent.clientWidth,
        fullHeight = parent.clientHeight;
    var widthBounds = bounds.width,
        heightBounds = bounds.height;
    var midX = bounds.x + widthBounds / 2,
        midY = bounds.y + heightBounds / 2;
    if (widthBounds == 0 || heightBounds == 0) return; // nothing to fit
    var scale = (padding || 0.85) / Math.max(widthBounds / fullWidth, heightBounds / fullHeight);
    var translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];

    //console.trace("zoomFit", translate, scale);
    groot
        .transition()
        .duration(transition || 750) // milliseconds
        .call(zoom.translate(translate).scale(scale).event);

    if (callback) { callback(); }
  }

  /**
   * Reset the whole graph.
   * A function that reset the svg item.
   *
   */
  function reset() {
    d3.select('svg#' + name)
      .html('')
      .attr('width', width)
      .attr('height', height)
      .style('background-color', 'rgba(128,128,128,0.1)');
  }

  /**
   * Get color for a value.
   * A function that get the color of a node or a group of nodes.
   *
   * @param   {object}    value         Value.
   * @return  {object}    color         The color in hexadecimal.
   */
  function color(property, value) {
    if (graph) {
      return _helpers.set_color(property, value);
    }
  }

  /**
   * Get attributes at one moment given.
   * A function that get the attributes of all nodes at a specific time.
   *
   * @param   {object}    time          Instant of time.
   * @param   {object}    callback      A function called at the end.
   * @return  {object}    object        An object with the number of nodes.
   */
  function get_attributes(property, time, callback) {
    var attrs = {}

    graph.nodes.forEach(function(node) {

      if (Array.isArray(node.spells)) {
          node.spells.forEach( function(d) {
            if ( time.between(d[0], d[1]) ) { 

              if (Array.isArray(node[property])) {
                node[property].forEach( function(p) {
                  if ( time.between(p[1], p[2]) ) attrs[p[0]] = (!attrs[p[0]]) ? 1 : attrs[p[0]] + 1;
                });
              } else { attrs[node[property]] = (!attrs[node[property]]) ? 1 : attrs[node[property]] + 1;  }

            } 
          });

      } else {

        if (Array.isArray(node[property])) {
          node[property].forEach( function(p) {
            if ( time.between(p[1], p[2]) ) attrs[p[0]] = (!attrs[p[0]]) ? 1 : attrs[p[0]] + 1;
          });
        } else { attrs[node[property]] = (!attrs[node[property]]) ? 1 : attrs[node[property]] + 1; }

      }
    });

    if (callback) { callback(attrs); }
    else { return attrs }
  }

  /**
   * Get nodes at one moment given.
   * A function that get the number of nodes at a specific time.
   *
   * @param   {object}    time          Instant of time.
   * @param   {object}    callback      A function called at the end.
   * @return  {object}    number        The number of nodes.
   */
  function get_nodes(time, callback) {
    var total_nodes = 0;
    graph.nodes.forEach(function(node) {
      if (Array.isArray(node.spells)) {
          node.spells.forEach( function(d) {
            if ( time.between(d[0], d[1]) ) { total_nodes++; } 
          });
      } else {
          total_nodes++;
      }
    });

    if (callback) { callback(total_nodes); }
    else { return total_nodes }
  }


  /**
   * Exporting
   * ---------
   */
  this.GraphVisualization = {

    // Functions
    create: create,
    import: importJSON,
    update_graph: update_graph,
    set_params: set_params,
    set_link_distance: set_link_distance,
    set_background: set_background,
    fit: zoom_to_fit,
    reset: reset,

    // Attributes
    model: {},
    nodes: undefined,
    links: undefined,

    // Getters
    color: color,
    shapes: shapes,
    colors: colors,
    get_attributes: get_attributes,
    get_nodes: get_nodes,

    // Statistics
    statistics: {},

    // Version
    version: '0.1'
  };

}).call(this);
