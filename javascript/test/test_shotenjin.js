load('../lib/shotenjin.js');
load('oktest.js');

var target = Oktest.target;
var ok = Oktest.ok;

target('Shotenjin.Tenjin', function(t) {

	target('#convert()', function(t) {

		t.spec("converts text into JS coode.", function(s) {
			var input = [
				'<table>\n',
				'</table>\n',
			].join('');
			var expected = [
				'var _buf = \'\', _V;  _buf += \'<table>\\n\\\n',
				'</table>\\n\';\n',
				'_buf\n',
			].join('');
			var actual = (new Shotenjin.Template()).convert(input);
			ok (actual).eq(expected);
		});

		t.spec("converts expression to JS coode.", function(s) {
			var input = [
				'<td>#{i}</td>\n',
				'<td>${item}</td>\n',
			].join('');
			var expected = [
				'var _buf = \'\', _V;  _buf += \'<td>\' + ((_V = (i)) === null || _V === undefined ? \'\' : _V) + \'</td>\\n\\\n',
				'<td>\' + escapeXml(item) + \'</td>\\n\';\n',
				'_buf\n',
			].join('');
			var actual = new Shotenjin.Template().convert(input);
			ok (actual).eq(expected);
		});

		t.spec("converts statements into JS coode.", function(s) {
			var input = [
				'<table>\n',
				'  <?js for (var i = 0, n = items.length; i < n; ) { ?>\n',
				'  <?js   var item = items[i++]; ?>\n',
				'  <tr class="#{i % 2 == 1 ? \'odd\' : \'even\'}">\n',
				'    <td>#{i}</td>\n',
				'    <td>${item}</td>\n',
				'  </tr>\n',
				'  <?js } ?>\n',
				'</table>\n',
			].join('');
			var expected = [
				'var _buf = \'\', _V;  _buf += \'<table>\\n\';\n',
				'   for (var i = 0, n = items.length; i < n; ) {\n',
				'     var item = items[i++];\n',
				' _buf += \'  <tr class="\' + ((_V = (i % 2 == 1 ? \'odd\' : \'even\')) === null || _V === undefined ? \'\' : _V) + \'">\\n\\\n',
				'    <td>\' + ((_V = (i)) === null || _V === undefined ? \'\' : _V) + \'</td>\\n\\\n',
				'    <td>\' + escapeXml(item) + \'</td>\\n\\\n',
				'  </tr>\\n\';\n',
				'   }\n',
				' _buf += \'</table>\\n\';\n',
				'_buf\n',
			].join('');
			var actual = new Shotenjin.Template().convert(input);
			ok (actual).eq(expected);
		});

	});

});

Oktest.run_all();