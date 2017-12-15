//<![CDATA[
    window.onload = function() {
        "use strict";


        // Public variables (User Configuration)
        var colorProperty,
            speed = 1000;

        // Private variables
        var width = window.innerWidth * 0.75,
            height = window.innerHeight * 4 / 5,
            focus_opacity = 0.1,
            radius = 8;

        // Private Graph variables
        var color,              // Color for nodes
            zoom,               // Zoom
            force,              // Set up the force layout
            svg,                // Svg item

            groot,              // Append sections to svg to have nodes and edges separately
            glinks,
            gnodes,
            data_node,          // Actual node data for the graph
            data_link,          // Actual link data for the graph

            graph,              // Graph 
            atts,               // Dynamic attributes if it is necessary
            linkedByIndex,      // Nodes linked by index
            link,               // Line svgs
            node;               // Circles for the nodes

        // Private Timeline variables
        var minInterval,        // Min value of the graph
            maxInterval,        // Max value of the graph
            minUnix,            // Min value for the timeline
            maxUnix,            // Max value for the timeline
            stepUnix,           // Step value for the timeline
            slider,             // Slider
            time,               // Variable to calculate date intervals
            play;               // Constant for the interval to play the simulation



        d3.select('#graph')
            .attr("width", width)
            .attr("height", height);

        d3.select('#slider3').attr("width", width).call(d3.slider().axis(true)
            .min(0).max(100)
        );

        $('.load').css("left", width / 2 - 25)
                  .css("top", height / 2);
        $('#configuration').css("height", height)

        loader(false);

        $('#file').change(function() {  
            var index = $('.custom-file-input').val().lastIndexOf("\\") + 1;
            $('.custom-file-control').attr("data-content", 
                $('.custom-file-input').val().substr(index) || "Choose file...");

            $.ajax({
                        url: 'upload.php', // point to server-side PHP script
                        type: 'POST',
                        data: new FormData($('form')[0]),
                        timeout: 3000,
                        cache: false,
                        contentType: false,
                        processData: false,
                        beforeSend: function() {
                            clearPreviousGraph();
                        }

                    }).done(function(response) {
                        // Show loader
                        loader(true);
                        $('.alert-danger').hide();

                        // Load File
                        setTimeout(function() {
                            loadFile(response);
                        }, 100);
                        
                    }).fail(function(response) {
                        loader(false);
                        $('#error-message').text(response.responseText || "Connection timed out");
                        $('.alert-danger').show();
                    });
        });

        function clearPreviousGraph() {
            $('#graph').html('');
            $('#slider3').html('');
            $('#properties-dynamic').html('').show();
            $('#properties-static').html('').show();
            $('#percentTable > tbody').empty();
            $('#info-graph > tbody').empty();
            $('#info-graph > tbody').empty();
        }

        function loader(show) {
            $('.load').show();
            // Show loader
            if (show) {
                $('svg#graph').css("background-color", "white");
                $('.load').text("").addClass("loader");

            // Show "No File"
            } else {
                $('svg#graph').css("background-color", "rgba(128,128,128,0.1)");
                $('.load').text("No file").removeClass("loader");
            }
        }

=====================================================================================================================================================================

        function loadFile(file) {

            /**
             * GRAPH
             */

            // Color
            color = d3.scale.category20();

            // Zoom
            zoom = d3.behavior
                .zoom()
                .scaleExtent([1/10, 10])
                .on('zoom', function () {
                    //console.trace("zoom", d3.event.translate, d3.event.scale);
                    groot.attr('transform',
                        'translate(' + d3.event.translate + ')scale(' + d3.event.scale     + ')');
                });

            // Set up the force layout
            force = d3.layout.force()
                .charge(-500)
                .linkDistance(30)
                .size([width, height]);

            // Activate zoom for the svg item
            svg = d3.select('#graph')
                    .attr("width", width)
                    .attr("height", height)
                    .call(zoom);

            // Append sections to svg to have nodes and edges separately
            groot = svg.append("g")     .attr("id", "root");
            glinks = groot.append("g")  .attr("id", "links");
            gnodes = groot.append("g")  .attr("id", "nodes");



            // Read the data from the graph
            graph = GexfParser.fetch(file);
            console.log("Graph", graph);

            if (graph.mode === "dynamic") {
                atts = GexfParser.dynamic(file, graph.timeformat)
                colorProperty = graph.model[0].title;
                console.log("Dynamic Attributes", atts);
            } else {
                atts = null;
            }

            // Number of nodes and links info table
            $('<tr>').appendTo('#info-graph > tbody');
            $('<th>').text('Nodes:').appendTo('#info-graph > tbody tr:nth-child(1)');
            $('<th>').text(graph.nodes.length).addClass('text-right').appendTo('#info-graph > tbody tr:nth-child(1)');
            
            $('<tr>').appendTo('#info-graph > tbody');
            $('<th>').text('Links:').appendTo('#info-graph > tbody tr:nth-child(2)');
            $('<th>').text(graph.links.length).addClass('text-right').appendTo('#info-graph > tbody tr:nth-child(2)');



            // Update linkedByIndex 
            linkedByIndex = {};
            graph.links.forEach(function(d) {
                linkedByIndex[d.source + "," + d.target] = true;
            });


            // Creates the graph data structure out of the json data
            force.nodes(graph.nodes)
                 .links(graph.links)
                 .start();

            // Create all the line svgs but without locations yet
            link = glinks.selectAll(".link").data(graph.links);
            set_link(link);

            // Do the same with the circles for the nodes - no
            var lastFocusNode;
            node = gnodes.selectAll(".node").data(graph.nodes);
            set_node(node);

            // Now we are giving the SVGs coordinates - the force layout is generating the coordinates which this code is using to update the attributes 
            // of the SVG elements
            force.on("tick", function () {

                link.attr("x1", function (d) {
                    return d.source.x;
                })
                .attr("y1", function (d) {
                    return d.source.y;
                })
                .attr("x2", function (d) {
                    return d.target.x;
                })
                .attr("y2", function (d) {
                    return d.target.y;
                });

                node.attr('transform',  function translate(d) {
                    return 'translate(' + d.x + ',' + d.y + ')';
                });
            });

            function set_node(node) {
                // Add nodes if the data has more nodes than before
                node.enter().append("circle")
                    .attr("class", "node")
                    .attr("r", radius)
                    .style("fill", function (d) {
                        return color(d.attributes[colorProperty]);
                    })
                    // Cancel zoom movement so you can move the node
                    .on("mousedown", function(d) {
                        d3.event.stopPropagation();
                    })
                    // Double-click to focus neighbours
                    .on("dblclick", function(d) {
                        d3.event.stopPropagation();
                        if (d === lastFocusNode) {
                            lastFocusNode = undefined;
                            node.style("opacity", 1);
                            link.style("opacity", 1);
                        } else {
                            lastFocusNode = d;
                            set_focus(d);
                        }
                    }).call(force.drag);

                // Remove nodes if the data has less nodes than before
                node.exit().remove();
            }

            function set_link(link) {
                // Remove links if the data has more links than before
                link.enter().append("line")
                    .attr("class", "link")
                    .style("stroke-width", function (d) {
                        return Math.sqrt(d.value);
                    });

                // Remove links if the data has less links than before
                link.exit().remove();
            }

            function set_focus(d) {

                node.style("opacity", function(o) {
                    return isConnected(d,o) || d.index == o.index ? 1 : focus_opacity;
                });

                link.style("opacity", function(o) {
                    return o.source.index == d.index || o.target.index == d.index ? 1 : focus_opacity;
                });

                function isConnected(source, neighbour) {
                    return linkedByIndex[source.index + "," + neighbour.index] || 
                            linkedByIndex[neighbour.index + "," + source.index];
                }
            }

=====================================================================================================================================================================

            /**
             * TIMELINE
             */

            // Maximum and minimum of all the intervals
            minInterval = Math.min();
            maxInterval = Math.max();
            _helpers.attributesInterval(atts, function(d) {
                if ( d[0] < minInterval && d[0] != -Infinity ) minInterval = d[0];
                if ( d[1] < minInterval && d[0] != +Infinity ) minInterval = d[1];
                if ( d[0] > maxInterval && d[0] != -Infinity ) maxInterval = d[0];
                if ( d[1] > maxInterval && d[1] != +Infinity ) maxInterval = d[1];
            });

            // Transform dates to ints 
            if ( graph.timeformat === "date" ) {
                time = d3.scale.linear().domain([minInterval, maxInterval]).range([1, 20]);
                // Attributes
                _helpers.attributesInterval(atts, function(d) {
                    if (d[0] !== -Infinity) d[0] = time(d[0]);
                    if (d[1] !== +Infinity) d[1] = time(d[1]);
                });
                // Nodes
                graph.nodes.forEach( function(node) {
                    if (Array.isArray(node.spell)) {
                        node.spell.forEach( function(d) {
                            if (d[0] !== -Infinity) d[0] = time(d[0]);
                            if (d[1] !== +Infinity) d[1] = time(d[1]);
                        });
                    }
                });
                // Links
                graph.links.forEach( function(link) {
                    if (link.spell[0] !== -Infinity) link.spell[0] = time(link.spell[0]);
                    if (link.spell[1] !== +Infinity) link.spell[1] = time(link.spell[1]);
                });
                minInterval = 1;
                maxInterval = 20;
            }


            stepUnix = (maxInterval - minInterval) / 200;
            minUnix = (minInterval !== Math.min()) ? minInterval - 2 * stepUnix : 0;
            maxUnix = (maxInterval !== Math.max()) ? maxInterval + 2 * stepUnix : minUnix + 20;

            // Create the slider
            slider = d3.slider();
            d3.select("#slider3").attr("width", width).call(slider.axis(true)
                .min(minUnix).max(maxUnix).step(stepUnix).value(maxUnix)
                .on("slide", function(evt, value) {
                    updateData(value);
                })
            );

            function updateData(value) {

                var statics = {};
                $('#percentTable > tbody').empty();

                // Reset data
                var delete_links = true;
                data_node = [];
                data_link = graph.links.slice();

                // Nodes 
                graph.nodes.forEach(function(n) {
                    if (Array.isArray(n.spell)) {
                        n.spell.forEach( function(d) {
                            if (d[0] < value && value <= d[1]) {
                                data_node.push(n);
                                delete_links = false;
                            }
                        });
                        if (delete_links) {
                            graph.links.forEach(function(e) {
                                if (e.source === n || e.target === n) {
                                    data_link.splice(data_link.indexOf(e), 1);
                                }
                            });
                        }
                    } else {
                        data_node.push(n);
                    }
                });

                // Links
                graph.links.forEach(function(e) {
                    if ( !(e.spell[0] < value && value <= e.spell[1]) && data_link.includes(e) )
                        data_link.splice(data_link.indexOf(e), 1);
                });

                // Reset force
                force.stop()
                     .nodes(data_node)
                     .links(data_link)
                     .start();

                // Redraw Graph
                link = glinks.selectAll(".link").data(data_link);
                set_link(link);

                node = gnodes.selectAll(".node").data(data_node);
                set_node(node);

                
                // Node Attributes
                data_node.forEach(function(n) {

                    for (var property in atts) {

                        var interval = atts[property][n.index].interval

                        for ( var i = 0; i < interval.length; i++ ) {
                            //console.log(interval[i][0], value, interval[i][1], "->", interval[i][2])
                            if (interval[i][0] < value && value <= interval[i][1]) 
                                n.attributes[property] = interval[i][2];
                            else if (value === minUnix) 
                                n.attributes[property] = interval[0][2];
                        }
                    }

                    // Count node properties
                    statics[n.attributes[colorProperty]] = (!statics[n.attributes[colorProperty]]) ? 1 : 
                        statics[n.attributes[colorProperty]] + 1;

                });

                node.style("fill", function (d) {
                    return color(d.attributes[colorProperty]);
                });

                // Show the five properties with more percentage
                var staticsSorted = Object.keys(statics).sort(function(a,b) {
                    return statics[b] - statics[a];
                });

                for ( var i = 0; ( i < staticsSorted.length ) && ( i < 5 ); i++ ) {
                    var percent = statics[staticsSorted[i]] / data_node.length * 100;

                    var propertyName = (staticsSorted[i].includes("class")) ? 
                                        staticsSorted[i].split('.').pop().split('\'')[0] : staticsSorted[i];

                    // Draw table every time
                    var appendTo = '#percentTable > tbody tr:nth-child(' + Number(i + 1) + ')';

                    $('<tr>').addClass('col-sm-12').appendTo('#percentTable > tbody');
                    $('<td>').css("background-color", color(staticsSorted[i])).addClass('col-sm-1').attr('data-value', staticsSorted[i]).appendTo(appendTo);
                    $('<td>').addClass('text-left col-sm-4').text(percent.toFixed(2) + " %").appendTo(appendTo);
                    $('<td>').addClass('text-right col-sm-6 property-name').text(propertyName).appendTo(appendTo);
                }

                return;
            }

=====================================================================================================================================================================

            /**
             * PAGE ELEMENTS
             */

            $('.load').hide();

            $('button#button_play').on('click', function() {

                $('button#button_play').addClass('pressed').prop("disabled", true);
                $('#speed-slider').slider('disable');
                slider.step( 1 / speed );
                
                if (slider.value() >= maxUnix) {
                    slider.value(minUnix);
                    updateData(slider.value());

                    setTimeout(player, 2000);
                } else {
                    player();
                }

                var i = slider.value();
                function player() {
                    clearInterval(play);
                    play = setInterval(function() {

                        if (slider.value() + slider.step() >= maxUnix) {
                            slider.value(maxUnix);
                            slider.step(stepUnix);
                            clearInterval(play);
                            $('button#button_play').removeClass('pressed').prop("disabled", false);
                            $('#speed-slider').slider('enable');
                        } else {
                            updateData(slider.value());
                            slider.value(i);
                            i += slider.step();
                        }

                    }, 5);
                }
            });

            $('button#button_pause').on('click', function() {
                clearInterval(play);
                slider.step(stepUnix);
                $('button#button_play').removeClass('pressed').prop("disabled", false);
                $('#speed-slider').slider('enable');
            });

            var dynamicArray = _helpers.dynamicAttsToArray(atts);
            for (var i = 0; i < graph.model.length; i++) {
                if ( dynamicArray.includes(graph.model[i].title) )
                    $('<option>').val(graph.model[i].title).text(graph.model[i].title).appendTo('#properties-dynamic');
                else 
                    $('<option>').val(graph.model[i].title).text(graph.model[i].title).appendTo('#properties-static');
            }

            // Hide optgroups if they are empty
            if ( $('#properties-static').children().length === 0 ) $('#properties-static').hide();
            if ( $('#properties-dynamic').children().length === 0 ) $('#properties-dynamic').hide();

            $('select#properties').change(function() {
                colorProperty = $('select#properties').val();
                updateData(slider.value());
            });

            $('button#button_zoomFit').click(function() {

                var paddingPercent = 0.7;
                var transitionDuration = 750;

                var bounds = groot.node().getBBox();
                var parent = groot.node().parentElement;
                var fullWidth = parent.clientWidth,
                    fullHeight = parent.clientHeight;
                var widthBounds = bounds.width,
                    heightBounds = bounds.height;
                var midX = bounds.x + widthBounds / 2,
                    midY = bounds.y + heightBounds / 2;
                if (widthBounds == 0 || heightBounds == 0) return; // nothing to fit
                var scale = (paddingPercent || 0.75) / Math.max(widthBounds / fullWidth, heightBounds / fullHeight);
                var translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];

                //console.trace("zoomFit", translate, scale);
                groot
                    .transition()
                    .duration(transitionDuration || 0) // milliseconds
                    .call(zoom.translate(translate).scale(scale).event);
            });

            // Speed for the timeline
            $('#speed-slider').slider('enable').on('change', function(value) {
                speed = value.value.newValue;
            });

            // Link distance between the nodes
            $('#link-distance-slider').slider('enable').on('change', function(value) {
                force.stop().linkDistance(value.value.newValue).start();

                // Update radius of the nodes to see them better
                var r = d3.scale.linear().domain([30, 1000]).range([8, 24]);
                radius = r(value.value.newValue);
                node.attr('r', radius);
            });


            updateData(slider.value());

            // Clear all events
            $('#file').change(function() {
                $('button#button_play').off();
                $('button#button_pause').off();
                $('select#properties').off();
                $('button#button_zoomFit').off();
                $('#speed-slider').slider('disable');
                $('#link-distance-slider').slider('disable').slider('setValue', 30);
            });

        }

    }

    ///]]