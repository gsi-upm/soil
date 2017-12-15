

var _helpers = {
	attributesInterval: function (attributes, callback) {
		for ( var property in attributes ) {
			for ( var i = 0; i < attributes[property].length; i++ ) {
				attributes[property][i].interval.forEach(function(d) {
					callback(d);
				});
			}
		}
	},
	dynamicAttsToArray: function(atts) {
		var array = []
		for ( var property in atts ) {
			array.push(property)
		}
		return array;
	}
};
