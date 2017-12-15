
;(function(undefined) {
  'use strict';

  /**
   * GEXF Parser
   * ============
   *
   * Author: PLIQUE Guillaume (Yomguithereal)
   * URL: https://github.com/Yomguithereal/gexf-parser
   * Version: 1.0
   */

  /**
   * Helper Namespace
   * -----------------
   *
   * A useful batch of function dealing with DOM operations and types.
   */
  var _helpers = {
    nodeListToArray: function(nodeList) {

      // Return array
      var children = [];

      // Iterating
      for (var i = 0, len = nodeList.length; i < len; ++i) {
        if (nodeList[i].nodeName !== '#text')
          children.push(nodeList[i]);
      }

      return children;
    },
    nodeListEach: function(nodeList, func) {

      // Iterating
      for (var i = 0, len = nodeList.length; i < len; ++i) {
        if (nodeList[i].nodeName !== '#text')
          func(nodeList[i]);
      }
    },
    nodeListToHash: function(nodeList, filter) {

      // Return object
      var children = {};

      // Iterating
      for (var i = 0; i < nodeList.length; i++) {
        if (nodeList[i].nodeName !== '#text') {
          var prop = filter(nodeList[i]);
          children[prop.key] = prop.value;
        }
      }

      return children;
    },
    namedNodeMapToObject: function(nodeMap) {

        // Return object
      var attributes = {};

      // Iterating
      for (var i = 0; i < nodeMap.length; i++) {
        attributes[nodeMap[i].name] = nodeMap[i].value;
      }

      return attributes;
    },
    getFirstElementByTagNS: function(node, ns, tag) {
      var el = node.getElementsByTagName(ns + ':' + tag)[0];

      if (!el)
        el = node.getElementsByTagNameNS(ns, tag)[0];

      if (!el)
        el = node.getElementsByTagName(tag)[0];

      return el;
    },
    getAttributeNS: function(node, ns, attribute) {
      var attr_value = node.getAttribute(ns + ':' + attribute);

      if (attr_value === undefined)
        attr_value = node.getAttributeNS(ns, attribute);

      if (attr_value === undefined)
        attr_value = node.getAttribute(attribute);

      return attr_value;
    },
    enforceType: function(type, value) {

      switch (type) {
        case 'boolean':
          value = (value === 'true');
          break;

        case 'integer':
        case 'long':
        case 'float':
        case 'double':
          value = +value;
          break;
      }

      return value;
    },
    getRGB: function(values) {
      return (values[3]) ?
        'rgba(' + values.join(',') + ')' :
        'rgb(' + values.slice(0, -1).join(',') + ')';
    }
  };


  /**
   * Parser Core Functions
   * ----------------------
   *
   * The XML parser's functions themselves.
   */

  /**
   * Node structure.
   * A function returning an object guarded with default value.
   *
   * @param  {object} properties The node properties.
   * @return {object}            The guarded node object.
   */
  function Node(properties) {

    // Possible Properties
    return {
      id: properties.id,
      index: properties.index,
      label: properties.label,
      attributes: properties.attributes || {},
      viz: properties.viz || {},
      spell: properties.spell || {}
    };
  }


  /**
   * Edge structure.
   * A function returning an object guarded with default value.
   *
   * @param  {object} properties The edge properties.
   * @return {object}            The guarded edge object.
   */
  function Edge(properties, nodeList) {

    var list = _helpers.nodeListToArray(nodeList);

    function findNodeSource (node) {
      return node.id === properties.source;
    }

    function findNodeTarget (node) {
      return node.id === properties.target;
    }

    // Possible Properties
    return {
      id: properties.id,
      type: properties.type || 'undirected',
      label: properties.label || '',
      source: list.indexOf(list.find(findNodeSource)),
      target: list.indexOf(list.find(findNodeTarget)),
      value: +properties.value || 1.0,
      viz: properties.viz || {},
      spell: properties.spell || {}
    };
  }

  /**
   * Graph parser.
   * This structure parse a gexf string and return an object containing the
   * parsed graph.
   *
   * @param  {string} xml The xml string of the gexf file to parse.
   * @return {object}     The parsed graph.
   */
  function Graph(xml) {
    var _xml = {};

    // Basic Properties
    //------------------
    _xml.els = {
      root: xml.getElementsByTagName('gexf')[0],
      graph: xml.getElementsByTagName('graph')[0],
      meta: xml.getElementsByTagName('meta')[0],
      model: xml.getElementsByTagName('attribute'),
      nodes: xml.getElementsByTagName('node'),
      links: xml.getElementsByTagName('edge')
    };

    _xml.hasViz = !!_helpers.getAttributeNS(_xml.els.root, 'xmlns', 'viz');
    _xml.version = _xml.els.root.getAttribute('version') || '1.0';
    _xml.mode = _xml.els.graph.getAttribute('mode') || 'static';
    _xml.timeformat = _xml.els.graph.getAttribute('timeformat') || null;

    var edgeType = _xml.els.graph.getAttribute('defaultedgetype');
    _xml.defaultEdgetype = edgeType || 'undirected';


    // Parser Functions
    //------------------

    // Meta Data
    function _metaData() {

      var metas = {};
      if (!_xml.els.meta)
        return metas;

      // Last modified date
      metas.lastmodifieddate = _xml.els.meta.getAttribute('lastmodifieddate');

      // Other information
      _helpers.nodeListEach(_xml.els.meta.childNodes, function(child) {
        metas[child.tagName.toLowerCase()] = child.textContent;
      });

      return metas;
    }

    // Model
    function _model() {
      var attributes = [];

      // Iterating through attributes
      _helpers.nodeListEach(_xml.els.model, function(attr) {

        // Properties
        var properties = {
          id: attr.getAttribute('id') || attr.getAttribute('for'),
          type: attr.getAttribute('type') || 'string',
          title: attr.getAttribute('title') || ''
        };

        // Defaults
        var default_el = _helpers.nodeListToArray(attr.childNodes);

        if (default_el.length > 0)
          properties.defaultValue = default_el[0].textContent;

        // Creating attribute
        attributes.push(properties);
      });

      return attributes;
    }

    // Nodes
    function _nodes(model) {
      var nodes = [];

      // Iteration through nodes
      _helpers.nodeListEach(_xml.els.nodes, function(n) {

        // Basic properties
        var properties = {
          id: n.getAttribute('id'),
          label: n.getAttribute('label') || ''
        };

        // Retrieving data from nodes if any
        if (model.length > 0)
          properties.attributes = _nodeData(model, n);

        // Retrieving viz information
        if (_xml.hasViz)
          properties.viz = _nodeViz(n);

        properties.spell = _nodeSpell(n);

        // Pushing node
        nodes.push(Node(properties));
      });

      return nodes;
    }

    // Spells from nodes
    function _nodeSpell(node) {
      var spells = node.getElementsByTagName('spells')[0];
      
      if (spells) {
        var spell = spells.getElementsByTagName('spell');
        var interval = [];
        
        for ( var i = 0; i < spell.length; i++ ) {
          var start = ( (_xml.timeformat !== "date") ? parseFloat(spell[i].getAttribute("start")) || -Infinity :
              (spell[i].getAttribute('start') ? new Date(spell[i].getAttribute('start')) : -Infinity)  );

          var end = ( (_xml.timeformat !== "date") ? parseFloat(spell[i].getAttribute("end")) || Infinity :
              (spell[i].getAttribute('end') ? new Date(spell[i].getAttribute('end')) : Infinity)  );

          interval.push([start, end]);
        }

        return interval;

      } else {
        return;
      }

    }

    // Data from nodes
    function _nodeData(model, node) {

      var data = {};
      var attvalues_els = node.getElementsByTagName('attvalue');

      // Getting Node Indicated Attributes
      var ah = _helpers.nodeListToHash(attvalues_els, function(el) {
        var attributes = _helpers.namedNodeMapToObject(el.attributes);
        var key = attributes.id || attributes['for'];

        // Returning object
        return { key: key, value: attributes.value };

      });


      // Iterating through model
      model.map(function(a) {
        // Default value?
        var att_title = a.title.toLowerCase();
        data[att_title] = !(a.id in ah) && 'defaultValue' in a ?
          _helpers.enforceType(a.type, a.defaultValue) : 
          _helpers.enforceType(a.type, ah[a.id]);
      });

      return data;
    }

    // Viz information from nodes
    function _nodeViz(node) {
      var viz = {};

      // Color
      var color_el = _helpers.getFirstElementByTagNS(node, 'viz', 'color');

      if (color_el) {
        var color = ['r', 'g', 'b', 'a'].map(function(c) {
          return color_el.getAttribute(c);
        });

        viz.color = _helpers.getRGB(color);
      }

      // Position
      var pos_el = _helpers.getFirstElementByTagNS(node, 'viz', 'position');

      if (pos_el) {
        viz.position = {};

        ['x', 'y', 'z'].map(function(p) {
          viz.position[p] = +pos_el.getAttribute(p);
        });
      }

      // Size
      var size_el = _helpers.getFirstElementByTagNS(node, 'viz', 'size');
      if (size_el)
        viz.size = +size_el.getAttribute('value');

      // Shape
      var shape_el = _helpers.getFirstElementByTagNS(node, 'viz', 'shape');
      if (shape_el)
        viz.shape = shape_el.getAttribute('value');

      return viz;
    }

    // Edges
    function _edges(default_type) {
      var edges = [];

      // Iteration through edges
      _helpers.nodeListEach(_xml.els.links, function(e) {

        // Creating the edge
        var properties = _helpers.namedNodeMapToObject(e.attributes);
        if (!('type' in properties)) {
          properties.type = default_type;
        }

        // Retrieving viz information
        if (_xml.hasViz)
          properties.viz = _edgeViz(e);

        properties.spell = _edgeSpell(e);

        edges.push(Edge(properties, _xml.els.nodes));
      });

      return edges;
    }

    // Spells from edges
    function _edgeSpell(edge) {
      var start = ( (_xml.timeformat !== "date") ? parseFloat(edge.getAttribute("start")) || -Infinity :
          (edge.getAttribute('start') ? new Date(edge.getAttribute('start')) : -Infinity)  );

      var end = ( (_xml.timeformat !== "date") ? parseFloat(edge.getAttribute("end")) || Infinity :
          (edge.getAttribute('end') ? new Date(edge.getAttribute('end')) : Infinity)  );

      return [start, end];
    }

    // Viz information from edges
    function _edgeViz(edge) {
      var viz = {};

      // Color
      var color_el = _helpers.getFirstElementByTagNS(edge, 'viz', 'color');

      if (color_el) {
        var color = ['r', 'g', 'b', 'a'].map(function(c) {
          return color_el.getAttribute(c);
        });

        viz.color = _helpers.getRGB(color);
      }

      // Shape
      var shape_el = _helpers.getFirstElementByTagNS(edge, 'viz', 'shape');
      if (shape_el)
        viz.shape = shape_el.getAttribute('value');

      // Thickness
      var thick_el = _helpers.getFirstElementByTagNS(edge, 'viz', 'thickness');
      if (thick_el)
        viz.thickness = +thick_el.getAttribute('value');

      return viz;
    }


    // Returning the Graph
    //---------------------
    _xml.model = _model();

    return {
      version: _xml.version,
      mode: _xml.mode,
      timeformat: _xml.timeformat,
      defaultEdgeType: _xml.defaultEdgetype,
      meta: _metaData(),
      model: _xml.model,
      nodes: _nodes(_xml.model),
      links: _edges(_xml.defaultEdgetype)
    };
  }

  /**
   * Dynamics attributes parser.
   * This structure parse a gexf string and return an object containing the
   * dynamics attributes.
   *
   * @param  {string} xml The xml string of the gexf file to parse.
   * @return {object}     The dynamics attributes and its values.
   */
  function dynamicAttributes(xml, timeformat) {

    var _xml = {};

    _xml.els = {
      nodes: xml.getElementsByTagName('node'),
      attributes: xml.getElementsByTagName('attributes')
    }

    for ( var i = 0; i < _xml.els.attributes.length; i++ ) {
      if (_xml.els.attributes[i].getAttribute("mode") === "dynamic")
        _xml.els.attributes = _xml.els.attributes[i];
    }

    var x = {};
    for ( var i = 0; i < _xml.els.attributes.children.length; i++ ) {
      var att = x[_xml.els.attributes.children[i].getAttribute("title")] = [];

      var node = 0;
      _helpers.nodeListEach(_xml.els.nodes, function(n) { 
        att[node] = { interval: [], index: node }

        for ( var j = 0; j < n.getElementsByTagName('attvalue').length; j++ ) {
          if (n.getElementsByTagName('attvalue')[j].getAttribute("for") === _xml.els.attributes.children[i].getAttribute("id")) {

            var element = n.getElementsByTagName('attvalue')[j];

            var start = ( (timeformat !== "date") ? parseFloat(element.getAttribute("start")) || -Infinity :
              (element.getAttribute('start') ? new Date(element.getAttribute('start')) : -Infinity)  );

            var end = ( (timeformat !== "date") ? parseFloat(element.getAttribute("end")) || Infinity :
              (element.getAttribute('end') ? new Date(element.getAttribute('end')) : Infinity)  );

            var value = element.getAttribute("value");

            att[node].interval.push([start, end, value]);

          }
        }

        node++;
      });

    }

    return x;

  }


  /**
   * Public API
   * -----------
   *
   * User-accessible functions.
   */

  // Fetching GEXF with XHR
  function fetch(gexf_url, callback) {
    var xhr = (function() {
      if (window.XMLHttpRequest)
        return new XMLHttpRequest();

      var names,
          i;

      if (window.ActiveXObject) {
        names = [
          'Msxml2.XMLHTTP.6.0',
          'Msxml2.XMLHTTP.3.0',
          'Msxml2.XMLHTTP',
          'Microsoft.XMLHTTP'
        ];

        for (i in names)
          try {
            return new ActiveXObject(names[i]);
          } catch (e) {}
      }

      return null;
    })();

    if (!xhr)
      throw 'XMLHttpRequest not supported, cannot load the file.';

    // Async?
    var async = (typeof callback === 'function'),
        getResult;

    // If we can't override MIME type, we are on IE 9
    // We'll be parsing the response string then.
    if (xhr.overrideMimeType) {
      xhr.overrideMimeType('text/xml');
      getResult = function(r) {
        return r.responseXML;
      };
    }
    else {
      getResult = function(r) {
        var p = new DOMParser();
        return p.parseFromString(r.responseText, 'application/xml');
      };
    }

    xhr.open('GET', gexf_url, async);

    if (async)
      xhr.onreadystatechange = function() {
        if (xhr.readyState === 4)
          callback(getResult(xhr));
      };

    xhr.send();

    return (async) ? xhr : getResult(xhr);
  }

  // Parsing the GEXF File
  function parse(gexf) {
    return Graph(gexf);
  }

  // Fetch and parse the GEXF File
  function fetchAndParse(gexf_url, callback) {
    if (typeof callback === 'function') {
      return fetch(gexf_url, function(gexf) {
        callback(Graph(gexf));
      });
    } else
      return Graph(fetch(gexf_url));
  }

  
  function parseDynamicAttributes(gexf, timeformat) {
    return dynamicAttributes(fetch(gexf), timeformat);
  }


  /**
   * Exporting
   * ----------
   */
  this.GexfParser = {

    // Functions
    parse: parse,
    fetch: fetchAndParse,
    dynamic: parseDynamicAttributes,

    // Version
    version: '0.1'
  };

}).call(this);
