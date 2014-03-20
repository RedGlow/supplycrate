function setCookie(c_name,value,exdays)
{
	var exdate=new Date();
	exdate.setDate(exdate.getDate() + exdays);
	var c_value=escape(value) + ((exdays==null) ? "" : "; expires="+exdate.toUTCString());
	document.cookie=c_name + "=" + c_value;
}

function getCookie(c_name)
{
	var c_value = document.cookie;
	var c_start = c_value.indexOf(" " + c_name + "=");
	if (c_start == -1)
	  {
	  c_start = c_value.indexOf(c_name + "=");
	  }
	if (c_start == -1)
	  {
	  c_value = null;
	  }
	else
	  {
	  c_start = c_value.indexOf("=", c_start) + 1;
	  var c_end = c_value.indexOf(";", c_start);
	  if (c_end == -1)
	  {
	c_end = c_value.length;
	}
	c_value = unescape(c_value.substring(c_start,c_end));
	}
	return c_value;
}

var formulas = [];

function loadformulas() {
	var rootElement = $('#formulas');
	rootElement.empty();
	formulas = [];
	var formulasCookie = getCookie('formulas');
	if(formulasCookie != null && formulasCookie != '')
	{
		var pieces = formulasCookie.split('~');
		for(var i = 0; i < pieces.length; i++)
		{
			var piece = pieces[i];
			var a = $('<p><a href="#" onclick="javascript:deleteformula(' + i + '); return false;">[del]</a> <a href="#" onclick="javascript:loadformula(' + i + '); return false;">' + piece + '</a></p>');
			rootElement.append(a);
			formulas.push(piece);
		}
	}
}

function saveformula() {
	var formulas = getCookie('formulas');
	if(formulas === null)
		formulas = '';
	if(formulas != '')
		formulas += '~';
	formulas += $('#formulatext').val();
	setCookie('formulas', formulas, 30*3);
	loadformulas();
}

function loadformula(i) {
	var piece = formulas[i];
	console.debug('piece=', piece);
	 $('#formulatext').val(piece);
	 $('#mainform').submit();
}

function deleteformula(i) {
	var formulas = getCookie('formulas');
	var pieces = formulas.split('~');
	pieces.splice(i, 1);
	formulas = pieces.join('~');
	setCookie('formulas', formulas);
	loadformulas();
}

$(document).ready(loadformulas);