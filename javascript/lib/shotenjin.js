/*
 * $Release: $
 * $Copyright: copyright(c) 2007-2011 kuwata-lab.com all rights reserved. $
 * $License: MIT License $
 */

/**
 *  namespace
 */

var Shotenjin = {

  _escape_table: { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' },

  _escape_func: function(m) { return Shotenjin._escape_table[m] },

  escapeXml: function(s) {
    if (s === null || s === undefined) return '';
    if (typeof(s) != 'string') return s;
    return s.replace(/[&<>"]/g, Shotenjin._escape_func); //"
  },

  toStr: function(s) {
    if (s === null || s === undefined) return "";
    return s;
  },

  strip: function(s) {
    if (! s) return s;
    //return s.replace(/^\s+|\s+$/g, '');
    return s.replace(/^\s+/, '').replace(/\s+$/, '');
  },

  // ex. {x: 10, y: 'foo'}
  //       => "var x = _context['x'];\nvar y = _conntext['y'];\n"
  _setlocalvarscode: function(obj) {
    var sb = "";
    for (var p in obj) sb += "var " + p + " = _context['" + p + "'];\n";
    return sb;
  }

};

var escapeXml = Shotenjin.escapeXml;
var toStr     = Shotenjin.toStr;


/**
 *  Template class
 */

Shotenjin.Template = function(input, properties) {
  if (typeof(input) === 'object' && ! properties) {
    input = null;
    properties = input;
  }
  if (properties) {
    var p = properties;
    if (p['tostrfunc'])  this.escapefunc = p['tostrfunc'];
    if (p['escapefunc']) this.escapefunc = p['escapefunc'];
  }
  if (input) this.convert(input);
};

Shotenjin.Template.prototype = {

  tostrfunc: 'toStr',
  escapefunc: 'escapeXml',

  script: null,

  preamble: "var _buf = ''; ",
  postamble: "_buf\n",

  convert: function(input) {
    this.args = null;
    input = input.replace(/<!--\?js/g, '<?js').replace(/\?-->/g, '?>');  // for Chrome
    return this.script = this.preamble + this.parseStatements(input) + this.postamble;
  },

  parseStatements: function(input) {
    var sb = '', pos = 0;
    var regexp = /(^[ \t]*)?<\?js(\s(?:.|\n)*?) ?\?>([ \t]*\r?\n)?/mg;
    var ended_with_nl = true, remained = null;
    var m;
    while ((m = regexp.exec(input)) != null) {
      var lspace = m[1], stmt = m[2], rspace = m[3];
      var is_bol = lspace || ended_with_nl;
      var ended_with_nl = !! rspace;
      var text = input.substring(pos, m.index);
      pos = m.index + m[0].length;
      if (remained) {
        text = remained + text;
        remained = null;
      }
      if (is_bol && rspace) {
        stmt = (lspace || '') + stmt + rspace;
      }
      else {
        if (lspace) text += lspace;
        remained = rspace;
      }
      if (text) sb += this.parseExpressions(text);
      stmt = this._parseArgs(stmt);
      sb += stmt;
    }
    var rest = pos == 0 ? input : input.substring(pos);
    sb += this.parseExpressions(rest);
    return sb;
  },

  args: null,

  _parseArgs: function(stmt) {
    if (this.args !== null) return stmt;
    var m = stmt.match(/^(\s*)\/\/@ARGS:?[ \t]+(.*?)(\r?\n)?$/);
    if (! m) return stmt;
    var sb = m[1];
    var arr = m[2].split(/,/);
    var args = [];
    for (var i = 0, n = arr.length; i < n; i++) {
      var arg = arr[i].replace(/^\s+/, '').replace(/\s+$/, '');
      args.push(arg);
      sb += " var " + arg + "=_context." + arg + ";";
    }
    sb += m[3];
    this.args = args;
    return sb;
  },

  parseExpressions: function(input) {
    if (! input) return '';
    var sb = " _buf += ";
    var regexp = /([$#])\{(.*?)\}/g;
    var pos = 0;
    var m;
    while ((m = regexp.exec(input)) != null) {
      var text = input.substring(pos, m.index);
      var s = m[0];
      pos = m.index + s.length;
      var indicator = m[1];
      var expr = m[2];
      var funcname = indicator == "$" ? this.escapefunc : this.tostrfunc;
      sb += "'" + this._escapeText(text) + "' + " + funcname + "(" + expr + ") + ";
    }
    var rest = pos == 0 ? input : input.substring(pos);
    var is_newline = input.charAt(input.length-1) == "\n";
    sb += "'" + this._escapeText(rest, true) + (is_newline ? "';\n" : "';");
    return sb;
  },

  _escapeText: function(text, eol) {
    if (! text) return "";
    text = text.replace(/[\'\\]/g, '\\$&').replace(/\n/g, '\\n\\\n');
    if (eol) text = text.replace(/\\n\\\n$/, "\\n");
    return text;
  },

  render: function(_context) {
    if (! _context) {
      _context = {};
    }
    else if (this.args === null) {
      eval(Shotenjin._setlocalvarscode(_context));
    }
    return eval(this.script);
  }

};


/*
 *  convenient function
 */
Shotenjin.render = function(template_str, context) {
  var template = new Shotenjin.Template();
  template.convert(template_str);
  var output = template.render(context);
  return output;
};


/*
 * jQuery plugin
 *
 * usage:
 *    <div id="template" style="display:none">
 *         <ul>
 *         <?js for (var i = 0, n = items.length; i < n; i++) { ?>
 *           <li>${i}: ${items[i]}</li>
 *         <?js } ?>
 *         </ul>
 *    </div>
 *    <div id="placeholder"></div>
 *
 *    <script>
 *      var context = {
 *        items: ["A","B","C"]
 *      };
 *      var html = $('#template').renderWith(context, true);          // return html string
 *      $('#template').renderWith(context, '#placeholder');           // replace '#placeholder' content by html
 *      $('#template').renderWith(context).appendTo('#placeholder');  // append html into into #placeholder
 *    </script>
 *
 */
if (typeof(jQuery) !== "undefined") {
  jQuery.fn.extend({
    renderWith: function renderWith(context, option) {
      var tmpl = this.html();
      tmpl = tmpl.replace(/^\s*\<\!\-\-/, '').replace(/\-\-\>\s*$/, '');
      var html = Shotenjin.render(tmpl, context);
      if (option === true) return html;
      if (option) return jQuery(option).html(html);
      return jQuery(html);
    }
  });
}


/*
 *  for node.js
 */
if (typeof(exports) == 'object') {  // node.js
  //(function() {
  //  for (var k in Shotenjin) {
  //    exports[k] = Shotenjin[k];
  //  }
  //})();
  exports.Shotenjin = Shotenjin;
}
