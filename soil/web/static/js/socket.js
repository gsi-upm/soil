
// Open the websocket connection
var ws = new WebSocket((window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws'); 

// Open conection with Socket
ws.onopen = function() {
    console.log('Connection opened!');
};

// Receive data from server
ws.onmessage = function(message) {
    //console.log('Message received!');

    var msg = JSON.parse(message.data);

    switch(msg['type']) {
        case 'trials':
            reset_trials();
            set_trials(msg['data']);
            // $('#load').removeClass('loader');
            break;

        case 'get_trial':
            console.log(msg['data']);

            self.GraphVisualization.import(convertJSON(msg['data']), function() {
                reset_configuration();
                set_configuration();
                // $('#home_menu').click(function() {
                //     setTimeout(function() {
                //         reset_timeline();
                //         set_timeline(msg['data']);
                //     }, 1000);
                // });
                reset_timeline();
                set_timeline(msg['data']);
                $('#load').hide();
            });
            $('#charts .chart').removeClass('no-data');
            set_chart_nodes(msg['data'], chart_nodes)
            set_chart_attrs(msg['data'], chart_attrs, $('.config-item #properties').val())
            $('.config-item #properties').change(function() {
                chart_attrs.destroy();
                chart_attrs = create_chart(width_chart, height_chart, 'Time', 'Attributes', '#chart_attrs');
                set_chart_attrs(msg['data'], chart_attrs, $('.config-item #properties').val())
            });
            break;

        case 'settings':
            $('#wrapper-settings').empty().removeClass('none');
            initGUI(msg['data']);
            break;

        case 'error':
            console.error(msg['error']);
            _socket.error(msg['error']);
            $('#load').removeClass('loader');
            break;

        case 'log':
            $('.console').append('$ ' + msg['logger'] + ': ' + msg['logging'] + '<br/>');
            $('.console').animate({ scrollTop: $('.console')[0].scrollHeight }, 'fast');
            break;

        case 'visualization_params':
            console.log(msg['data']);
            self.GraphVisualization.set_params(msg['data']['shape_property'], msg['data']['shapes'], msg['data']['colors']);

            if ( msg['data']['background_image'] ) {
                // $('svg#graph').css('background-image', 'linear-gradient(to bottom, rgba(0,0,0,0.4) 0%,rgba(0,0,0,0.4) 100%), url(img/background/' + msg['data']['background_image'])
                //               .css('background-size', '130%').css('background-position', '5% 30%').css('background-repeat', 'no-repeat');
                $('<style>').text('svg line.link { stroke: white !important; stroke-width: 1.5px !important; }').appendTo($('html > head'));
                $('<style>').text('svg circle.node { stroke-width: 2.5px !important; }').appendTo($('html > head'));
                self.GraphVisualization.set_background('img/background/' + msg['data']['background_image'], msg['data']['background_opacity'], msg['data']['background_filter_color']);
            }
            break;

        case 'download_gexf':
            var xml_declaration = '<?xml version="1.0" encoding="utf-8"?>';
            download(msg['filename'] + '.gexf', 'xml', xml_declaration + msg['data']);
            break;

        case 'download_json':
            download(msg['filename'] + '.json', 'json', JSON.stringify(msg['data'], null, 4));
            break;

        default:
            console.warn('Unexpected message!')
    }

}

var _socket = {
    send: function(message, type) {
        var json = {}
        json['type'] = type
        json['data'] = message
        ws.send(JSON.stringify(json))
    },
    error: function(message) {
        $('#error-message').text(message);
        $('.alert.alert-danger').show();
    },
    current_trial: undefined
};

var set_trials = function(trials) {
    for ( i in trials ) {
        var list_item = $('<li>').appendTo('.dropdown#trials .dropdown-menu');
        $('<a>').val(i).text(trials[i]).appendTo(list_item);
    }
    // Select 'trials'
    $('.dropdown#trials li a').click(function() {
        var a = $('.dropdown-toggle .caret');
        $('.dropdown-toggle').text($(this).text() + ' ').append(a);
        _socket.send($(this).val(), 'get_trial');
        _socket.current_trial = $(this).val();
    });
    // Request first trial as default
    _socket.send(0, 'get_trial')
    _socket.current_trial = 0
};

var reset_trials = function() {
    // 'Trials' selector
    $('.dropdown-menu').empty();
    var a = $('.dropdown-toggle .caret');
    $('.dropdown-toggle').text('Trials ').append(a);
}

var convertJSON = function(json) {
    // For NetworkX Geometric Graphs get positions
    json.nodes.forEach(function(node) {
        var scx = d3.scale.linear().domain([0, 1]).range([0, width]);
        var scy = d3.scale.linear().domain([0, 1]).range([width, 0]);
        if ( node.pos ) {
            node.scx = scx(node.pos[0]);
            node.scy = scy(node.pos[1]);
        }
        delete node.pos;
    });
    json.links.forEach(function(link) {
        link.source = json.nodes[link.source]
        link.target = json.nodes[link.target]
    });
    // Fix spells for nodes
    json.nodes.forEach(function(node) {
        for (i in node.spells) {
            if (node.spells[i][0] > node.spells[i][1]) {
                aux = node.spells[i][0];
                node.spells[i][0] = node.spells[i][1];
                node.spells[i][1] = aux;
            }
        }
    });
    return json;
}

var update_statistics_table = function() {

    $('#percentTable tbody').empty()

    var statisticsSorted = Object.keys(self.GraphVisualization.statistics).sort(function(a,b) {
        return self.GraphVisualization.statistics[b] - self.GraphVisualization.statistics[a];
    });

    for ( var i in statisticsSorted ) {
        if ( i <= 5 ) {
            // Draw table
            var appendTo = '#percentTable > tbody tr:nth-child(' + Number(parseInt(i) + 1) + ')';
            var propertyName = (statisticsSorted[i].includes('class')) ? 
                                        statisticsSorted[i].split('.').pop().split('\'')[0] : statisticsSorted[i];

            $('<tr>').addClass('col-sm-12').appendTo('#percentTable > tbody');
            $('<td>').css('background-color', self.GraphVisualization.color($('.config-item #properties').val(), statisticsSorted[i])).addClass('col-sm-1').appendTo(appendTo);
            $('<td>').addClass('text-left col-sm-4').text(self.GraphVisualization.statistics[statisticsSorted[i]] + ' %').appendTo(appendTo);
            $('<td>').addClass('text-right col-sm-6 property-name').text(propertyName).appendTo(appendTo);
        }
    }
}

var set_configuration = function() {
    // Number of nodes and links info table
    $('<tr>').appendTo('#info-graph > tbody');
    $('<th>').text('Nodes:').appendTo('#info-graph > tbody tr:nth-child(1)');
    $('<th>').text(self.GraphVisualization.nodes).addClass('text-right').appendTo('#info-graph > tbody tr:nth-child(1)');
    
    $('<tr>').appendTo('#info-graph > tbody');
    $('<th>').text('Links:').appendTo('#info-graph > tbody tr:nth-child(2)');
    $('<th>').text(self.GraphVisualization.links).addClass('text-right').appendTo('#info-graph > tbody tr:nth-child(2)');

    // Options of 'Select'
    for ( var i in self.GraphVisualization.model['dynamic'] ) {
        $('<option>').val(self.GraphVisualization.model['dynamic'][i].title)
                     .text(self.GraphVisualization.model['dynamic'][i].title).appendTo('#properties-dynamic');
    }
    for ( var i in self.GraphVisualization.model['static'] ) {
        $('<option>').val(self.GraphVisualization.model['static'][i].title)
                     .text(self.GraphVisualization.model['static'][i].title).appendTo('#properties-static');
    }

    // Hide optgroups if they are empty
    if ( $('#properties-dynamic').children().length === 0 ) $('#properties-dynamic').hide();
    if ( $('#properties-static').children().length === 0 )  $('#properties-static').hide();

    update_statistics_table();

    // Enable 'Link Distance' slider
    $('#link-distance-slider').slider('enable').on('change', function(value) {
        self.GraphVisualization.set_link_distance(value.value.newValue);
    });

    // Enable 'Run configuration' button
    $('#run_simulation').attr('data-toggle', 'modal').attr('data-target', '#simulation_modal');

    // Enable 'Download' buttons
    $('#download_modal .btn-success').prop('disabled', false);
    $('#download_gexf').on('click', function() {
        _socket.send(_socket.current_trial, 'download_gexf')
    });
    $('#download_json').on('click', function() {
        _socket.send(_socket.current_trial, 'download_json')
    });
}

var reset_configuration = function() {
    // Information table about the graph
    $('#info-graph > tbody').empty();

    // 'Select' for properties
    $('#properties-dynamic').empty().show();
    $('#properties-static').empty().show();

    // 'Link Distance' slider
    $('#link-distance-slider').slider('disable').slider('setValue', 30);

    // 'Download' buttons
    $('#download_gexf').off();
    $('#download_json').off();
}

var slider;

var set_timeline = function(graph) {
    // 'Timeline' slider
    var [min, max] = get_limits(graph);

    var stepUnix = 1;
    var minUnix  = (min !== Math.min()) ? min : 0;
    var maxUnix  = (max !== Math.max()) ? max : minUnix + 20;

    slider = d3.slider();
    d3.select('#slider3').attr('width', width).call(
        slider.axis(true).min(minUnix).max(maxUnix).step(stepUnix).value(minUnix)
        .on('slide', function(evt, value) {
            self.GraphVisualization.update_graph($('.config-item #properties').val(), value, function() {
                update_statistics_table();
            });
        })
    );

    // Draw graph for the first time
    self.GraphVisualization.update_graph($('.config-item #properties').val(), maxUnix, function() {
        update_statistics_table();
        setTimeout(function() {           
            self.GraphVisualization.fit(); 
            if ( $('svg #root > image').length !== 0 ) {
                $('svg #root > image').attr('height', d3.select('#root').node().getBBox().height * 1.2);
                var dx = d3.select('#graph-wrapper').node().getBBox().width - d3.select('svg #root > image').node().getBBox().width;
                var dy = d3.select('#graph-wrapper').node().getBBox().height - d3.select('svg #root > image').node().getBBox().height;
                $('svg #root > image').attr('transform', 'translate(' + (dx / 2) + ',' + (dy / 2) + ')');
                $('svg #root > rect').attr('transform', 'translate(' + (dx / 2) + ',' + (dy / 2) + ')')
                                     .attr('width', d3.select('svg #root > image').node().getBBox().width)
                                     .attr('height', d3.select('svg #root > image').node().getBBox().height);
            }
        }, 1000);
    });

    // 'Speed' slider
    $('#speed-slider').slider('enable').on('change', function(value) {
        speed = value.value.newValue;
    });

    // Button 'Play'
    $('button#button_play').on('click', function() {
        play();

    });

    // Button 'Pause'
    $('button#button_pause').on('click', function() {
        stop();
        $('button#button_play').removeClass('pressed').prop("disabled", false);
    });

    // Button 'Zoom to Fit'
    $('button#button_zoomFit').click(function() { self.GraphVisualization.fit(); });
}

var player;

function play(){
    $('button#button_play').addClass('pressed').prop("disabled", true);

    if (slider.value() >= slider.max()) {
        slider.value(slider.min());
    }

    var FRAME_INTERVAL = 100;
    var speed_ratio = FRAME_INTERVAL / 1000 // speed=1 => 1 step per second
    
    nextStep = function() {
        newvalue = Math.min(slider.value() + speed*speed_ratio, slider.max());
        console.log("new time value", newvalue);
        slider.value(newvalue);

        self.GraphVisualization.update_graph($('.config-item #properties').val(), slider.value(), function () {
            update_statistics_table();
        });

        if (newvalue < slider.max()) {
            player = setTimeout(nextStep, FRAME_INTERVAL);
        } else {
            $('button#button_play').removeClass('pressed').prop("disabled", false);
        }
    }

    player = setTimeout(nextStep, FRAME_INTERVAL);
}

function stop() {
    clearTimeout(player);
}

var reset_timeline = function() {
    // 'Timeline' slider
    $('#slider3').html('');

    // 'Speed' slider
    // $('#speed-slider').slider('disable').slider('setValue', 1000);

    // Buttons
    stop();
    $('button#button_play').off().removeClass('pressed').prop("disabled", false);
    $('button#button_pause').off();
    $('button#button_zoomFit').off();
}

var get_limits = function(graph) {
    var max = Math.max();
    var min = Math.min()
    graph.links.forEach(function(link) {
        if (link.end    > max) max = link.end
        if (link.start  > max) max = link.start
        if (link.end    < min) min = link.end
        if (link.start  < min) min = link.start
    });
    graph.nodes.forEach(function(node) {
        for (property in node) {
            if ( Array.isArray(node[property]) ) {

                for (i in node[property]) {
                    for (j in node[property][i]) {
                        if (node[property][i][j] > max) max = node[property][i][j];
                        if (node[property][i][j] < min) min = node[property][i][j];
                    }
                }

            }
        }
    })
    return [min, max];
}

var set_chart_nodes = function(graph, chart) {
    var [min, max] = get_limits(graph);
    var data = ['nodes']
    for (var i = min; i <= max; i++) {
        data.push(this.GraphVisualization.get_nodes(i));
    }
    chart.load({
        unload: true,
        columns: [data]
    });
}

var set_chart_attrs = function(graph, chart, property) {
    var [min, max] = get_limits(graph);
    var data_tmp = {}
    for (var i = min; i <= max; i++) {
        this.GraphVisualization.get_attributes(property, i, function(object) {
            for (var value in object) {
                if (!data_tmp[value]) {
                    var time = 0
                    for (var done in data_tmp)
                        time = (data_tmp[done].length > time) ? data_tmp[done].length - 1 : time
                    data_tmp[value] = Array(time).fill(0);
                }
                data_tmp[value].push(object[value]);
            }
        });
    }
    var data = $.map(data_tmp, function(value, index) {
        value.splice(0,0,index);
        return [value];
    });
    chart.load({
        unload: true,
        columns: data
    });
    chart.axis.labels({y: property});
}

var create_chart = function(width, height, label_x, label_y, bind_to) {
    return c3.generate({
        size: {
            width: width,
            height: height
        },
        data: {
            columns: [],
            type: 'area-spline'
        },
        axis: {
            x: { label: label_x },
            y: { label: label_y }
        },
        point: { show: false },
        bindto: bind_to
    });
}

var run_simulation = function() {
    var environment_variables = {}
    $('#wrapper-settings input').each(function() {
        switch(this.type) {
            case 'text':
                environment_variables[this.id] = Number(this.value);
                break;
            case 'checkbox':
                environment_variables[this.id] = ($(this).is(':checked')) ? true : false;
                break;
            case 'number':
                environment_variables[this.id] = Number(this.value);
                break;
            default:
                console.warn(this.id +  ' not defined when running simulation!');
                break;
        }
        
    });
    return environment_variables;
}

var download = function(filename, filetype, content) {
    var file = document.createElement('a');
    file.setAttribute('href', 'data:text/' + filetype + ';charset=utf-8,' + encodeURIComponent(content));
    file.setAttribute('download', filename);
    file.click();
    delete file;
}
