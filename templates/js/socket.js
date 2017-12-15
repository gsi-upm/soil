
// Open the websocket connection
var ws = new WebSocket((window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws'); 

// Open conection with Socket
ws.onopen = function() {
    console.log('Connection opened!');
};

// Receive data from server
ws.onmessage = function(message) {
	console.log('Message received!');

	var msg = JSON.parse(message.data);

	switch(msg['type']) {
		case 'trials':
			$('#load').removeClass('loader');
			set_trials(msg['data']);
			break;

		case 'get_trial':
			console.log(msg['data']);
			GraphVisualization.import(convertJSON(msg['data']['graph']), msg['data']['models'], function() {
				$('#load').hide();
				reset_configuration();
				set_configuration();
				reset_timeline();
				set_timeline(msg['data']['graph']);
			});
			break;

		case 'error':
			console.log(msg['error']);
			_socket.error(msg['error']);
			$('#load').removeClass('loader');

		default:
			console.log('Unexpected message!')
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
	}
};

var set_trials = function(trials) {
	for ( i in trials ) {
		$('<option>').val(i).text(trials[i]).appendTo('select#trials');
	}
	// Request first trial as default
	_socket.send(0, 'get_trial')
};

var convertJSON = function(json) {
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
            $('<td>').css('background-color', self.GraphVisualization.color(statisticsSorted[i])).addClass('col-sm-1').appendTo(appendTo);
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
    if ( $('#properties-static').children().length === 0 ) 	$('#properties-static').hide();

    update_statistics_table();

    // Enable 'Link Distance' slider
	$('#link-distance-slider').slider('enable').on('change', function(value) {
		self.GraphVisualization.set_link_distance(value.value.newValue);
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

}

var set_timeline = function(graph) {
	// 'Timeline' slider
	var [min, max] = get_min_and_max(graph);

	var stepUnix = (max - min) / 200;
	var minUnix  = (min !== Math.min()) ? min : 0;
    var maxUnix  = (max !== Math.max()) ? max : minUnix + 20;

	slider = d3.slider();
	d3.select('#slider3').attr('width', width).call(
		slider.axis(true).min(minUnix).max(maxUnix).step(stepUnix).value(maxUnix)
		.on('slide', function(evt, value) {
			self.GraphVisualization.update_graph($('.config-item #properties').val(), value, function() {
				update_statistics_table();
			});
		})
	);

	// Draw graph for the first time
	self.GraphVisualization.update_graph($('.config-item #properties').val(), maxUnix, function() {
		update_statistics_table();
	});

	// 'Speed' slider
	$('#speed-slider').slider('enable').on('change', function(value) {
        speed = value.value.newValue;
    });

	// Button 'Play'
	$('button#button_play').on('click', function() {

        $('button#button_play').addClass('pressed').prop("disabled", true);
        $('#speed-slider').slider('disable');
        slider.step( 1 / speed );
        
        if (slider.value() >= maxUnix) {
            slider.value(minUnix);
            self.GraphVisualization.update_graph($('.config-item #properties').val(), slider.value(), function() {
				update_statistics_table();
			});
            setTimeout(player, 1000);
        } else {
            player();
        }

        var i = slider.value();
        function player() {
            clearInterval(play);
            play = setInterval(function() {
            	self.GraphVisualization.update_graph($('.config-item #properties').val(), slider.value(), function() {
					update_statistics_table();
				});

                if (slider.value() + slider.step() >= maxUnix) {
                    slider.value(maxUnix);
                    slider.step(stepUnix);
                    clearInterval(play);
                    $('button#button_play').removeClass('pressed').prop("disabled", false);
                    $('#speed-slider').slider('enable');
                } else {
                    slider.value(i);
                    i += slider.step();
                }

            }, 5);
        }
    });

	// Button 'Pause'
	$('button#button_pause').on('click', function() {
        clearInterval(play);
        slider.step(stepUnix);
        $('button#button_play').removeClass('pressed').prop("disabled", false);
        $('#speed-slider').slider('enable');
    });

	// Button 'Zoom to Fit'
    $('button#button_zoomFit').click(function() { self.GraphVisualization.fit(); });
}

var reset_timeline = function() {
	// 'Timeline' slider
	$('#slider3').html('');

	// 'Speed' slider
	$('#speed-slider').slider('disable').slider('setValue', 1000);

	// Buttons
	clearInterval(play);
    $('button#button_play').off().removeClass('pressed').prop("disabled", false);
    $('button#button_pause').off();
    $('button#button_zoomFit').off();
}

var get_min_and_max = function(graph) {
	var max = Math.max();
	var min = Math.min()
	graph.links.forEach(function(link) {
		if (link.end 	> max) max = link.end
		if (link.start 	> max) max = link.start
		if (link.end 	< min) min = link.end
		if (link.start 	< min) min = link.start
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
