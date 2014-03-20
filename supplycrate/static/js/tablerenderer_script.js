TableRenderer = {

	goTo: function(url) {
		window.location.href = url;
		return false;
	},

	formChanged: function(element) {
		$('#submit_parameters').removeAttr('disabled');
		return true;
	},

}