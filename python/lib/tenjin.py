##
## $Release: $
## $Copyright: copyright(c) 2007-2010 kuwata-lab.com all rights reserved. $
## $License: MIT License $
##
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:
##
## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
##

"""Very fast and light-weight template engine based embedded Python.
   See User's Guide and examples for details.
   http://www.kuwata-lab.com/tenjin/pytenjin-users-guide.html
   http://www.kuwata-lab.com/tenjin/pytenjin-examples.html
"""

__release__  = "$Release$"
__license__  = "MIT License"
__all__      = ['Template', 'Engine', 'helpers', ]


import re, sys, os, time, marshal
from time import time as _time
from os.path import getmtime as _getmtime
from os.path import isfile as _isfile
random = pickle = unquote = None   # lazy import
python3 = sys.version_info[0] == 3
python2 = sys.version_info[0] == 2

logger = None


##
## utilities
##

def _write_binary_file(filename, content):
    global random
    f = None
    try:
        if random is None: from random import random
        tmpfile = filename + str(random())[1:]
        f = open(tmpfile, 'wb')
        f.write(content)
    finally:
        if f:
            f.close()
            os.rename(tmpfile, filename)

def _read_binary_file(filename):
    f = None
    try:
        f = open(filename, 'rb')
        return f.read()
    finally:
        if f: f.close()

if python2:

    codecs = None    # lazy import

    def _read_text_file(filename, encoding=None):
        global codecs
        if not codecs: import codecs
        f = codecs.open(filename, encoding=(encoding or 'utf-8'))
        try:
            return f.read()
        finally:
            f.close()

    def _read_template_file(filename, encoding=None):
        s = _read_binary_file(filename)          ## binary(=str)
        if encoding: s = s.decode(encoding)      ## binary(=str) to unicode
        return s

    def _is_unicode(val):
        return isinstance(val, unicode)

    def _is_binary(val):
        return isinstance(val, str)

elif python3:

    def _read_text_file(filename, encoding=None):
        f = open(filename, encoding=(encoding or 'utf-8'))
        try:
            return f.read()
        finally:
            f.close()

    def _read_template_file(filename, encoding=None):
        s = _read_binary_file(filename)          ## binary
        return s.decode(encoding or 'utf-8')     ## binary to unicode(=str)

    def _is_unicode(val):
        return isinstance(val, str)

    def _is_binary(val):
        return isinstance(val, bytes)

def _create_module(module_name):
    """ex. mod = _create_module('tenjin.util')"""
    mod = type(sys)(module_name)    # or type(sys)(module_name.split('.')[-1]) ?
    mod.__file__ = __file__
    sys.modules[module_name] = mod
    return mod



##
## helper method's module
##

if True:

    if python2:
        def generate_tostrfunc(encode=None, decode=None):
            """Generate 'to_str' function with encode or decode encoding.
               ex. generate to_str() function which encodes unicode into binary(=str).
                  to_str = tenjin.generate_tostrfunc(encode='utf-8')
                  repr(to_str(u'hoge'))  #=> 'hoge' (str)
               ex. generate to_str() function which decodes binary(=str) into unicode.
                  to_str = tenjin.generate_tostrfunc(decode='utf-8')
                  repr(to_str('hoge'))   #=> u'hoge' (unicode)
            """
            if encode:
                if decode:
                    raise ValueError("can't specify both encode and decode encoding.")
                else:
                    def to_str(val,   _str=str, _unicode=unicode, _isa=isinstance, _encode=encode):
                        """Convert val into string or return '' if None. Unicode will be encoded into binary(=str)."""
                        if _isa(val, _str):     return val
                        if val is None:                return ''
                        if _isa(val, _unicode): return val.encode(_encode)  # unicode to binary(=str)
                        return _str(val)
            else:
                if decode:
                    def to_str(val,   _str=str, _unicode=unicode, _isa=isinstance, _decode=decode):
                        """Convert val into string or return '' if None. Binary(=str) will be decoded into unicode."""
                        if _isa(val, _str):     return val.decode(_decode)  # binary(=str) to unicode
                        if val is None:         return ''
                        if _isa(val, _unicode): return val
                        return _unicode(val)
                else:
                    def to_str(val,   _str=str, _unicode=unicode, _isa=isinstance):
                        """Convert val into string or return '' if None. Both binary(=str) and unicode will be retruned as-is."""
                        if _isa(val, _str):     return val
                        if val is None:         return ''
                        if _isa(val, _unicode): return val
                        return _str(val)
            return to_str

    elif python3:
        def generate_tostrfunc(decode=None, encode=None):
            """Generate 'to_str' function with encode or decode encoding.
               ex. generate to_str() function which encodes unicode(=str) into bytes
                  to_str = tenjin.generate_tostrfunc(encode='utf-8')
                  repr(to_str('hoge'))  #=> b'hoge' (bytes)
               ex. generate to_str() function which decodes bytes into unicode(=str).
                  to_str = tenjin.generate_tostrfunc(decode='utf-8')
                  repr(to_str(b'hoge'))   #=> 'hoge' (str)
            """
            if encode:
                if decode:
                    raise ValueError("can't specify both encode and decode encoding.")
                else:
                    def to_str(val,   _str=str, _bytes=bytes, _isa=isinstance, _encode=encode):
                        """Convert val into string or return '' if None. Unicode(=str) will be encoded into bytes."""
                        if _isa(val, _str):   return val.encode(_encode)  # unicode(=str) to binary
                        if val is None:       return ''
                        if _isa(val, _bytes): return val
                        return _str(val).encode(_encode)
            else:
                if decode:
                    def to_str(val,   _str=str, _bytes=bytes, _isa=isinstance, _decode=decode):
                        """Convert val into string or return '' if None. Bytes will be decoded into unicode(=str)."""
                        if _isa(val, _str):    return val
                        if val is None:        return ''
                        if _isa(val, _bytes):  return val.decode(_decode)  # binary to unicode(=str)
                        return _str(val)
                else:
                    def to_str(val,   _str=str, _bytes=bytes, _isa=isinstance):
                        """Convert val into string or return '' if None. Both bytes and unicode(=str) will be retruned as-is."""
                        if _isa(val, _str):    return val
                        if val is None:        return ''
                        if _isa(val, _bytes):  return val
                        return _str(val)
            return to_str

    if python2:
        to_str = generate_tostrfunc(encode='utf-8')  # or encode=None?
    elif python3:
        to_str = generate_tostrfunc(decode='utf-8')

    def echo(string):
        """add string value into _buf. this is equivarent to '#{string}'."""
        frame = sys._getframe(1)
        context = frame.f_locals
        context['_buf'].append(string)

    def start_capture(varname=None, _depth=1):
        """start capturing with name."""
        frame = sys._getframe(_depth)
        context = frame.f_locals
        context['_buf_tmp'] = context['_buf']
        context['_capture_varname'] = varname
        context['_buf'] = []

    def stop_capture(store_to_context=True, _depth=1):
        """stop capturing and return the result of capturing.
           if store_to_context is True then the result is stored into _context[varname].
        """
        frame = sys._getframe(_depth)
        context = frame.f_locals
        result = ''.join(context['_buf'])
        context['_buf'] = context.pop('_buf_tmp')
        varname = context.pop('_capture_varname')
        if varname:
            context[varname] = result
            if store_to_context:
                context['_context'][varname] = result
        return result

    def captured_as(name, _depth=1):
        """helper method for layout template.
           if captured string is found then append it to _buf and return True,
           else return False.
        """
        frame = sys._getframe(_depth)
        context = frame.f_locals
        if name in context:
            _buf = context['_buf']
            _buf.append(context[name])
            return True
        return False

    def _p(arg):
        """ex. '/show/'+_p("item['id']") => "/show/#{item['id']}" """
        return '<`#%s#`>' % arg    # decoded into #{...} by preprocessor

    def _P(arg):
        """ex. '<b>%s</b>' % _P("item['id']") => "<b>${item['id']}</b>" """
        return '<`$%s$`>' % arg    # decoded into ${...} by preprocessor

    def _decode_params(s):
        """decode <`#...#`> and <`$...$`> into #{...} and ${...}"""
        global unquote
        if unquote is None:
            import urllib
            if   python2:  from urllib       import unquote
            elif python3:  from urllib.parse import unquote
        dct = { 'lt':'<', 'gt':'>', 'amp':'&', 'quot':'"', '#039':"'", }
        def unescape(s):
            #return s.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#039;', "'").replace('&amp;',  '&')
            return re.sub(r'&(lt|gt|quot|amp|#039);',  lambda m: dct[m.group(1)],  s)
        s = to_str(s)
        s = re.sub(r'%3C%60%23(.*?)%23%60%3E', lambda m: '#{%s}' % unquote(m.group(1)), s)
        s = re.sub(r'%3C%60%24(.*?)%24%60%3E', lambda m: '${%s}' % unquote(m.group(1)), s)
        s = re.sub(r'&lt;`#(.*?)#`&gt;',   lambda m: '#{%s}' % unescape(m.group(1)), s)
        s = re.sub(r'&lt;`\$(.*?)\$`&gt;', lambda m: '${%s}' % unescape(m.group(1)), s)
        s = re.sub(r'<`#(.*?)#`>', r'#{\1}', s)
        s = re.sub(r'<`\$(.*?)\$`>', r'${\1}', s)
        return s

    class SafeStr(str):
        """string class to avoid escape in template"""
        def __init__(self, s):
            if not isinstance(s, basestring):
                raise TypeError("%r is not a string." % (s, ))
            self.value = s
        def __str__(self):
            return self
        def __unicode__(self):
            return self

    def safe_escape(s):
        if isinstance(s, helpers.SafeStr):
            return s.value
        return helpers.escape(s)

    mod = _create_module('tenjin.helpers')
    mod.to_str             = to_str
    mod.generate_tostrfunc = generate_tostrfunc
    mod.echo               = echo
    mod.start_capture      = start_capture
    mod.stop_capture       = stop_capture
    mod.captured_as        = captured_as
    mod._p                 = _p
    mod._P                 = _P
    mod._decode_params     = _decode_params
    mod.SafeStr            = SafeStr
    mod.safe_escape        = safe_escape
    mod.__all__ = ['escape', 'to_str', 'echo', 'generate_tostrfunc',
                   'start_capture', 'stop_capture', 'captured_as',
                   '_p', '_P', '_decode_params', 'SafeStr', 'safe_escape',
                   ]

helpers = mod
del echo, start_capture, stop_capture, captured_as, _p, _P, _decode_params, SafeStr, safe_escape
#del to_str, generate_tostrfunc
del mod


##
## module for html
##
if True:

    #_escape_table = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }
    #_escape_pattern = re.compile(r'[&<>"]')
    ##_escape_callable = lambda m: _escape_table[m.group(0)]
    ##_escape_callable = lambda m: _escape_table.__get__(m.group(0))
    #_escape_get     = _escape_table.__getitem__
    #_escape_callable = lambda m: _escape_get(m.group(0))
    #_escape_sub     = _escape_pattern.sub

    #def escape_html(s):
    #    return s                                          # 3.02

    #def escape_html(s):
    #    return _escape_pattern.sub(_escape_callable, s)   # 6.31

    #def escape_html(s):
    #    return _escape_sub(_escape_callable, s)           # 6.01

    #def escape_html(s, _p=_escape_pattern, _f=_escape_callable):
    #    return _p.sub(_f, s)                              # 6.27

    #def escape_html(s, _sub=_escape_pattern.sub, _callable=_escape_callable):
    #    return _sub(_callable, s)                         # 6.04

    #def escape_html(s):
    #    s = s.replace('&', '&amp;')
    #    s = s.replace('<', '&lt;')
    #    s = s.replace('>', '&gt;')
    #    s = s.replace('"', '&quot;')
    #    return s                                          # 5.83

    def escape_html(s):
        """Escape '&', '<', '>', '"' into '&amp;', '&lt;', '&gt;', '&quot;'."""
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')   # 5.72


    def tagattr(name, expr, value=None, escape=True):
        """(experimental) Return ' name="value"' if expr is true value, else '' (empty string).
           If value is not specified, expr is used as value instead."""
        if not expr: return ''
        if value is None: value = expr
        if escape: value = helpers.html.escape_html(to_str(value))
        return ' %s="%s"' % (name, value)

    def tagattrs(**kwargs):
        """(experimental) built html tag attribtes.
           ex.
           >>> tagattrs(klass='main', size=20)
           ' class="main" size="20"'
           >>> tagattrs(klass='', size=0)
           ''
        """
        if 'klass' in kwargs: kwargs['class'] = kwargs.pop('klass')
        if 'checked'  in kwargs: kwargs['checked']  = kwargs.pop('checked')  and 'checked'  or None
        if 'selected' in kwargs: kwargs['selected'] = kwargs.pop('selected') and 'selected' or None
        if 'disabled' in kwargs: kwargs['disabled'] = kwargs.pop('disabled') and 'disabled' or None
        escape_html = helpers.html.escape_html
        return ''.join([ ' %s="%s"' % (k, escape_html(to_str(v))) for k, v in kwargs.items() if v ])

    def checked(expr):
        """return ' checked="checked"' if expr is true."""
        return expr and ' checked="checked"' or ''

    def selected(expr):
        """return ' selected="selected"' if expr is true."""
        return expr and ' selected="selected"' or ''

    def disabled(expr):
        """return ' disabled="disabled"' if expr is true."""
        return expr and ' disabled="disabled"' or ''

    def nl2br(text):
        """replace "\n" to "<br />\n" and return it."""
        if not text:
            return ''
        return text.replace('\n', '<br />\n')

    def text2html(text, use_nbsp=True):
        """(experimental) escape xml characters, replace "\n" to "<br />\n", and return it."""
        if not text:
            return ''
        s = helpers.html.escape_html(text)
        if use_nbsp: s = s.replace('  ', ' &nbsp;')
        return helpers.html.nl2br(s)

    def nv(name, value, sep=None, **kwargs):
        """(experimental) Build name and value attributes.
           ex.
           >>> nv('rank', 'A')
           'name="rank" value="A"'
           >>> nv('rank', 'A', '.')
           'name="rank" value="A" id="rank.A"'
           >>> nv('rank', 'A', '.', checked=True)
           'name="rank" value="A" id="rank.A" checked="checked"'
           >>> nv('rank', 'A', '.', klass='error', style='color:red')
           'name="rank" value="A" id="rank.A" class="error" style="color:red"'
        """
        s = sep and 'name="%s" value="%s" id="%s"' % (name, value, name+sep+value) \
                or  'name="%s" value="%s"'         % (name, helpers.html.escape_html(value))
        return kwargs and s + helpers.html.tagattrs(**kwargs) or s

    def new_cycle(*values):
        """Generate cycle object.
           ex.
             cycle = new_cycle('odd', 'even')
             print(cycle())   #=> 'odd'
             print(cycle())   #=> 'even'
             print(cycle())   #=> 'odd'
             print(cycle())   #=> 'even'
        """
        def gen(values):
            n = len(values)
            i = 0
            while True:
                yield values[i]
                i = (i + 1) % n
        if   python2:  return gen(values).next
        elif python3:  return gen(values).__next__

    mod = _create_module('tenjin.helpers.html')
    #mod._escape_table = _escape_table
    mod.escape_html = escape_html
    mod.escape_xml = escape_html   # for backward compatibility
    mod.escape     = escape_html
    mod.tagattr    = tagattr
    mod.tagattrs   = tagattrs
    mod.checked    = checked
    mod.selected   = selected
    mod.disabled   = disabled
    mod.nl2br      = nl2br
    mod.text2html  = text2html
    mod.nv         = nv
    mod.new_cycle  = new_cycle

helpers.html = mod
helpers.escape = escape_html
del escape_html, tagattr, tagattrs, checked, selected, disabled, nl2br, text2html, nv, new_cycle
del mod



##
## Template class
##

class TemplateSyntaxError(SyntaxError):

    def build_error_message(self):
        ex = self
        if not ex.text:
            return self.args[0]
        return ''.join([
            "%s:%s:%s: %s\n" % (ex.filename, ex.lineno, ex.offset, ex.msg, ),
            "%4d: %s\n"      % (ex.lineno, ex.text.rstrip(), ),
            "     %s^\n"     % (' ' * ex.offset, ),
        ])


class Template(object):
    """Convert and evaluate embedded python string.
       See User's Guide and examples for details.
       http://www.kuwata-lab.com/tenjin/pytenjin-users-guide.html
       http://www.kuwata-lab.com/tenjin/pytenjin-examples.html
    """

    ## default value of attributes
    filename   = None
    encoding   = None
    escapefunc = 'escape'
    tostrfunc  = 'to_str'
    indent     = 4
    preamble   = None    # "_buf = []"
    postamble  = None    # "print ''.join(_buf)"
    smarttrim  = None
    args       = None
    timestamp  = None
    trace      = False   # if True then '<!-- begin: file -->' and '<!-- end: file -->' are printed

    def __init__(self, filename=None, encoding=None, input=None, escapefunc=None, tostrfunc=None,
                       indent=None, preamble=None, postamble=None, smarttrim=None, trace=None):
        """Initailizer of Template class.

           filename:str (=None)
             Filename to convert (optional). If None, no convert.
           encoding:str (=None)
             Encoding name. If specified, template string is converted into
             unicode object internally.
             Template.render() returns str object if encoding is None,
             else returns unicode object if encoding name is specified.
           input:str (=None)
             Input string. In other words, content of template file.
             Template file will not be read if this argument is specified.
           escapefunc:str (='escape')
             Escape function name.
           tostrfunc:str (='to_str')
             'to_str' function name.
           indent:int (=4)
             Indent width.
           preamble:str or bool (=None)
             Preamble string which is inserted into python code.
             If true, '_buf = []' is used insated.
           postamble:str or bool (=None)
             Postamble string which is appended to python code.
             If true, 'print("".join(_buf))' is used instead.
           smarttrim:bool (=None)
             If True then "<div>\\n#{_context}\\n</div>" is parsed as
             "<div>\\n#{_context}</div>".
        """
        if encoding   is not None:  self.encoding   = encoding
        if escapefunc is not None:  self.escapefunc = escapefunc
        if tostrfunc  is not None:  self.tostrfunc  = tostrfunc
        if indent     is not None:  self.indent     = indent
        if preamble   is not None:  self.preamble   = preamble
        if postamble  is not None:  self.postamble  = postamble
        if smarttrim  is not None:  self.smarttrim  = smarttrim
        if trace      is not None:  self.trace      = trace
        #
        if preamble  is True:  self.preamble = "_buf = []"
        if postamble is True:  self.postamble = "print(''.join(_buf))"
        if input:
            self.convert(input, filename)
            self.timestamp = False      # False means 'file not exist' (= Engine should not check timestamp of file)
        elif filename:
            self.convert_file(filename)
        else:
            self._reset()

    def _reset(self, input=None, filename=None):
        self.script   = None
        self.bytecode = None
        self.input    = input
        self.filename = filename
        if input != None:
            i = input.find("\n")
            if i < 0:
                self.newline = "\n"   # or None
            elif len(input) >= 2 and input[i-1] == "\r":
                self.newline = "\r\n"
            else:
                self.newline = "\n"

    def before_convert(self, buf):
        if self.preamble:
            buf.append(self.preamble)
            buf.append(self.input.startswith('<?py') and "\n" or "; ")

    def after_convert(self, buf):
        if self.postamble:
            if buf and not buf[-1].endswith("\n"):
                buf.append("\n")
            buf.append(self.postamble + "\n")

    def convert_file(self, filename):
        """Convert file into python script and return it.
           This is equivarent to convert(open(filename).read(), filename).
        """
        input = _read_template_file(filename)
        return self.convert(input, filename)

    def convert(self, input, filename=None):
        """Convert string in which python code is embedded into python script and return it.

           input:str
             Input string to convert into python code.
           filename:str (=None)
             Filename of input. this is optional but recommended to report errors.
        """
        if python2:
            if self.encoding and isinstance(input, str):
                input = input.decode(self.encoding)
        self._reset(input, filename)
        buf = []
        self.before_convert(buf)
        self.parse_stmts(buf, input)
        self.after_convert(buf)
        script = ''.join(buf)
        self.script = script
        return script

    def compile_stmt_pattern(pi):
        return re.compile(r'<\?%s( |\t|\r?\n)(.*?) ?\?>([ \t]*\r?\n)?' % pi, re.S)

    compile_stmt_pattern = staticmethod(compile_stmt_pattern)

    STMT_PATTERN = None

    def stmt_pattern(self):
        pat = Template.STMT_PATTERN
        if not pat:   # make re.compile() to be lazy (because it is heavy weight)
            pat = Template.STMT_PATTERN = Template.compile_stmt_pattern('py')
        return pat

    def parse_stmts(self, buf, input):
        if not input: return
        rexp = self.stmt_pattern()
        is_bol = True
        index = 0
        for m in rexp.finditer(input):
            mspace, code, rspace = m.groups()
            #mspace, close, rspace = m.groups()
            #code = input[m.start()+4+len(mspace):m.end()-len(close)-(rspace and len(rspace) or 0)]
            text = input[index:m.start()]
            index = m.end()
            ## detect spaces at beginning of line
            lspace = None
            if text == '':
                if is_bol:
                    lspace = ''
            elif text[-1] == '\n':
                lspace = ''
            else:
                rindex = text.rfind('\n')
                if rindex < 0:
                    if is_bol and text.isspace():
                        lspace, text = text, ''
                else:
                    s = text[rindex+1:]
                    if s.isspace():
                        lspace, text = s, text[:rindex+1]
            #is_bol = rspace is not None
            ## add text, spaces, and statement
            self.parse_exprs(buf, text, is_bol)
            is_bol = rspace is not None
            #if mspace == "\n":
            if mspace and mspace.endswith("\n"):
                code = "\n" + (code or "")
            #if rspace == "\n":
            if rspace and rspace.endswith("\n"):
                code = (code or "") + "\n"
            if code:
                code = self.statement_hook(code)
                self.add_stmt(buf, code)
        rest = input[index:]
        if rest:
            self.parse_exprs(buf, rest)
        self._arrange_indent(buf)

    def statement_hook(self, stmt):
        """expand macros and parse '#@ARGS' in a statement."""
        stmt = stmt.replace("\r\n", "\n")   # Python can't handle "\r\n" in code
        if self.args is None:
            args_pattern = r'^ *#@ARGS(?:[ \t]+(.*?))?$'
            m = re.match(args_pattern, stmt)
            if m:
                arr = (m.group(1) or '').split(',')
                args = [];  declares = []
                for s in arr:
                    arg = s.strip()
                    if not s: continue
                    if not re.match('^[a-zA-Z_]\w*$', arg):
                        raise ValueError("%r: invalid template argument." % arg)
                    args.append(arg)
                    declares.append("%s = _context.get('%s'); " % (arg, arg))
                self.args = args
                nl = stmt[m.end():]
                if nl: declares.append(nl)
                return ''.join(declares)
        ##
        return stmt

    EXPR_PATTERN = None

    def expr_pattern(self):
        pat = Template.EXPR_PATTERN
        if not pat:   # make re.compile() to be lazy (because it is heavy weight)
            pat = Template.EXPR_PATTERN = re.compile(r'([#$])\{(.*?)\}', re.S)
        return pat

    def get_expr_and_escapeflag(self, match):
        return match.group(2), match.group(1) == '$'

    def parse_exprs(self, buf, input, is_bol=False):
        buf2 = []
        self._parse_exprs(buf2, input, is_bol)
        if buf2:
            buf.append(''.join(buf2))

    def _parse_exprs(self, buf, input, is_bol=False):
        if not input: return
        self.start_text_part(buf)
        rexp = self.expr_pattern()
        smarttrim = self.smarttrim
        nl = self.newline
        nl_len  = len(nl)
        pos = 0
        for m in rexp.finditer(input):
            start = m.start()
            text  = input[pos:start]
            pos   = m.end()
            expr, flag_escape = self.get_expr_and_escapeflag(m)
            #
            if text:
                self.add_text(buf, text)
            self.add_expr(buf, expr, flag_escape)
            #
            if smarttrim:
                flag_bol = text.endswith(nl) or not text and (start > 0  or is_bol)
                if flag_bol and not flag_escape and input[pos:pos+nl_len] == nl:
                    pos += nl_len
                    buf.append("\n")
        if smarttrim:
            if buf and buf[-1] == "\n":
                buf.pop()
        rest = input[pos:]
        if rest:
            self.add_text(buf, rest, True)
        self.stop_text_part(buf)
        if input[-1] == '\n':
            buf.append("\n")

    def start_text_part(self, buf):
        buf.append("_buf.extend((")

    def stop_text_part(self, buf):
        buf.append("));")

    _quote_rexp = None

    def _quote_text(self, text):
        #return re.sub(r"(['\\\\])", r"\\\1", text)
        rexp = Template._quote_rexp
        if not rexp:   # make re.compile() to be lazy (because it is heavy weight)
            rexp = Template._quote_rexp = re.compile(r"(['\\\\])")
        return rexp.sub(r"\\\1", text)

    def add_text(self, buf, text, encode_newline=False):
        if not text: return
        use_unicode = self.encoding and python2
        buf.append(use_unicode and "u'''" or "'''")
        text = self._quote_text(text)
        if   not encode_newline:    buf.extend((text,       "''', "))
        elif text.endswith("\r\n"): buf.extend((text[0:-2], "\\r\\n''', "))
        elif text.endswith("\n"):   buf.extend((text[0:-1], "\\n''', "))
        else:                       buf.extend((text,       "''', "))

    _add_text = add_text

    def add_expr(self, buf, code, flag_escape=None):
        if not code or code.isspace(): return
        if flag_escape is None:
            buf.extend((code, ", "))
        elif flag_escape is False:
            buf.extend((self.tostrfunc, "(", code, "), "))
        else:
            buf.extend((self.escapefunc, "(", self.tostrfunc, "(", code, ")), "))

    def add_stmt(self, buf, code):
        if not code: return
        lines = code.splitlines(True)   # keep "\n"
        if lines[-1][-1] != "\n":
            lines[-1] = lines[-1] + "\n"
        buf.extend(lines)


    _START_WORDS = dict.fromkeys(('for', 'if', 'while', 'def', 'try:', 'with', 'class'), True)
    _END_WORDS   = dict.fromkeys(('#end', '#endfor', '#endif', '#endwhile', '#enddef', '#endtry', '#endwith', '#endclass'), True)
    _CONT_WORDS  = dict.fromkeys(('elif', 'else:', 'except', 'except:', 'finally:'), True)
    _WORD_REXP   = re.compile(r'\S+')

    depth = -1

    ##
    ## ex.
    ##   input = r"""
    ##   if items:
    ##   _buf.extend(('<ul>\n', ))
    ##   i = 0
    ##   for item in items:
    ##   i += 1
    ##   _buf.extend(('<li>', to_str(item), '</li>\n', ))
    ##   #endfor
    ##   _buf.extend(('</ul>\n', ))
    ##   #endif
    ##   """[1:]
    ##   lines = input.splitlines(True)
    ##   block = self.parse_lines(lines)
    ##      #=>  [ "if items:\n",
    ##             [ "_buf.extend(('<ul>\n', ))\n",
    ##               "i = 0\n",
    ##               "for item in items:\n",
    ##               [ "i += 1\n",
    ##                 "_buf.extend(('<li>', to_str(item), '</li>\n', ))\n",
    ##               ],
    ##               "#endfor\n",
    ##               "_buf.extend(('</ul>\n', ))\n",
    ##             ],
    ##             "#endif\n",
    ##           ]
    def parse_lines(self, lines):
        block = []
        try:
            self._parse_lines(lines.__iter__(), False, block, 0)
        except StopIteration:
            if self.depth > 0:
                fname, linenum, colnum, linetext = self.filename, len(lines), None, None
                raise TemplateSyntaxError("unexpected EOF.", (fname, linenum, colnum, linetext))
        else:
            pass
        return block

    def _parse_lines(self, lines_iter, end_block, block, linenum):
        if block is None: block = []
        _START_WORDS = self._START_WORDS
        _END_WORDS   = self._END_WORDS
        _CONT_WORDS  = self._CONT_WORDS
        _WORD_REXP   = self._WORD_REXP
        get_line = python2 and lines_iter.next or lines_iter.__next__
        while True:
            line = get_line()
            linenum += line.count("\n")
            m = _WORD_REXP.search(line)
            if not m:
                block.append(line)
                continue
            word = m.group(0)
            if word in _END_WORDS:
                if word != end_block and word != '#end':
                    if end_block is False:
                        msg = "'%s' found but corresponding statement is missing." % (word, )
                    else:
                        msg = "'%s' expected but got '%s'." % (end_block, word)
                    colnum = m.start() + 1
                    raise TemplateSyntaxError(msg, (self.filename, linenum, colnum, line))
                return block, line, None, linenum
            elif line.endswith(':\n') or line.endswith(':\r\n'):
                if word in _CONT_WORDS:
                    return block, line, word, linenum
                elif word in _START_WORDS:
                    block.append(line)
                    self.depth += 1
                    cont_word = None
                    try:
                        child_block, line, cont_word, linenum = \
                            self._parse_lines(lines_iter, '#end'+word, [], linenum)
                        block.extend((child_block, line, ))
                        while cont_word:   # 'elif' or 'else:'
                            child_block, line, cont_word, linenum = \
                                self._parse_lines(lines_iter, '#end'+word, [], linenum)
                            block.extend((child_block, line, ))
                    except StopIteration:
                        msg = "'%s' is not closed." % (cont_word or word)
                        colnum = m.start() + 1
                        raise TemplateSyntaxError(msg, (self.filename, linenum, colnum, line))
                    self.depth -= 1
                else:
                    block.append(line)
            else:
                block.append(line)
        assert "unreachable"

    def _join_block(self, block, buf, depth):
        indent = ' ' * (self.indent * depth)
        for line in block:
            if isinstance(line, list):
                self._join_block(line, buf, depth+1)
            elif line.isspace():
                buf.append(line)
            else:
                buf.append(indent + line.lstrip())

    def _arrange_indent(self, buf):
        """arrange indentation of statements in buf"""
        block = self.parse_lines(buf)
        buf[:] = []
        self._join_block(block, buf, 0)


    def render(self, context=None, globals=None, _buf=None):
        """Evaluate python code with context dictionary.
           If _buf is None then return the result of evaluation as str,
           else return None.

           context:dict (=None)
             Context object to evaluate. If None then new dict is created.
           globals:dict (=None)
             Global object. If None then globals() is used.
           _buf:list (=None)
             If None then new list is created.
        """
        if context is None:
            locals = context = {}
        elif self.args is None:
            locals = context.copy()
        else:
            locals = {}
            if '_engine' in context:
                context.get('_engine').hook_context(locals)
        locals['_context'] = context
        if globals is None:
            globals = sys._getframe(1).f_globals
        bufarg = _buf
        if _buf is None:
            _buf = []
        locals['_buf'] = _buf
        if not self.bytecode:
            self.compile()
        if self.trace:
            _buf.append("<!-- ***** begin: %s ***** -->\n" % self.filename)
            exec(self.bytecode, globals, locals)
            _buf.append("<!-- ***** end: %s ***** -->\n" % self.filename)
        else:
            exec(self.bytecode, globals, locals)
        if bufarg is not None:
            return bufarg
        elif not logger:
            return ''.join(_buf)
        else:
            try:
                return ''.join(_buf)
            except UnicodeDecodeError:
                ex = sys.exc_info()[1]
                logger.error("[tenjin.Template] " + str(ex))
                logger.error("[tenjin.Template] (_buf=%r)" % (_buf, ))
                raise

    def compile(self):
        """compile self.script into self.bytecode"""
        self.bytecode = compile(self.script, self.filename or '(tenjin)', 'exec')


##
## secure template class
##
class SafeTemplate(Template):
    """Deny '#{}' and allow only '${}'. Use '${SafeStr(x)}' instead of '#{x}'.
       usage.
         import tenjin
         from tenjin.helpers import *
         from tenjin.helpers.html import SafeTemplate, to_html
         tenjin.Engine.templateclass = SafeTemplate
         engine = tenjin.Engine()
         output = engine.render('hello.pyhtml', {'value':'<>&"'})
    """
    escapefunc = 'safe_escape'

    def get_expr_and_escapeflag(self, match):
        expr = match.group(2)
        if match.group(1) == '#':
            msg = "'#{%s}': '#{}' is not available in %s."
            raise TemplateSyntaxError(msg % (expr, self.__class__.__name__))
        #return expr, True      # always escapes expresion value
        global _safe_str_rexp
        if not _safe_str_rexp:
            _safe_str_rexp = re.compile(r'^\s*SafeStr\((.*)\)\s*$')  # or r'^SafeStr\([^\)]*\)$'
        m = _safe_str_rexp.match(expr)
        if m:
            expr = m.group(1)
            return expr, False    # skip escape
        else:
            return expr, True     # escapes by safe_escape()

_safe_str_rexp = None


##
## preprocessor class
##

class Preprocessor(Template):
    """Template class for preprocessing."""

    STMT_PATTERN = None

    def stmt_pattern(self):
        pat = Preprocessor.STMT_PATTERN
        if not pat:   # re.compile() is heavy weight, so make it lazy
            pat = Preprocessor.STMT_PATTERN = Template.compile_stmt_pattern('PY')
        return Preprocessor.STMT_PATTERN

    EXPR_PATTERN = None

    def expr_pattern(self):
        pat = Preprocessor.EXPR_PATTERN
        if not pat:   # re.compile() is heavy weight, so make it lazy
            pat = Preprocessor.EXPR_PATTERN = re.compile(r'([#$])\{\{(.*?)\}\}', re.S)
        return Preprocessor.EXPR_PATTERN

    #def get_expr_and_escapeflag(self, match):
    #    return match.group(2), match.group(1) == '$'

    def add_expr(self, buf, code, flag_escape=None):
        if not code or code.isspace():
            return
        code = "_decode_params(%s)" % code
        Template.add_expr(self, buf, code, flag_escape)


class SafePreprocessor(Preprocessor):
    """ex.
         tenjin.Engine.preprocessor = tenjin.SafePreprocessor
    """
    escapefunc = 'safe_escape'

    def get_expr_and_escapeflag(self, match):
        if match.group(1) == '#':
            msg = "'#{%s}': '#{{}}' is not available in %s."
            raise TemplateSyntaxError(msg % (match.group(2), self.__class__.__name__))
        return match.group(2), True


##
## cache storages
##

class CacheStorage(object):
    """[abstract] Template object cache class (in memory and/or file)"""

    def __init__(self, postfix='.cache'):
        self.postfix = postfix
        self.items = {}    # key: full path, value: template object

    def get(self, fullpath, create_template):
        """get template object. if not found, load attributes from cache file and restore  template object."""
        template = self.items.get(fullpath)
        if not template:
            dict = self._load(fullpath)
            if dict:
                template = create_template()
                for k, v in dict.items():
                    setattr(template, k, v)
                self.items[fullpath] = template
        return template

    def set(self, fullpath, template):
        """set template object and save template attributes into cache file."""
        self.items[fullpath] = template
        dict = self._save_data_of(template)
        return self._store(fullpath, dict)

    def _save_data_of(self, template):
        return { 'args'  : template.args,   'bytecode' : template.bytecode,
                 'script': template.script, 'timestamp': template.timestamp }

    def unset(self, fullpath):
        """remove template object from dict and cache file."""
        self.items.pop(fullpath, None)
        return self._delete(fullpath)

    def clear(self):
        """remove all template objects and attributes from dict and cache file."""
        for k, v in self.items.items():
            self._delete(k)
        self.items.clear()

    def _load(self, fullpath):
        """(abstract) load dict object which represents template object attributes from cache file."""
        raise NotImplementedError.new("%s#_load(): not implemented yet." % self.__class__.__name__)

    def _store(self, fullpath, template):
        """(abstract) load dict object which represents template object attributes from cache file."""
        raise NotImplementedError.new("%s#_store(): not implemented yet." % self.__class__.__name__)

    def _delete(self, fullpath):
        """(abstract) remove template object from cache file."""
        raise NotImplementedError.new("%s#_delete(): not implemented yet." % self.__class__.__name__)

    def _cachename(self, fullpath):
        """change fullpath into cache file path."""
        return fullpath + self.postfix


class MemoryCacheStorage(CacheStorage):

    def _load(self, fullpath):
        return None

    def _store(self, fullpath, template):
        pass

    def _delete(self, fullpath):
        pass


class FileCacheStorage(CacheStorage):

    def _delete(self, fullpath):
        cachepath = self._cachename(fullpath)
        if _isfile(cachepath): os.unlink(cachepath)


class MarshalCacheStorage(FileCacheStorage):

    def __init__(self, postfix='.cache'):
        FileCacheStorage.__init__(self, postfix)

    def _load(self, fullpath):
        cachepath = self._cachename(fullpath)
        if not _isfile(cachepath): return None
        if logger: logger.info("[tenjin.MarshalCacheStorage] load cache (file=%r)" % (cachepath, ))
        dump = _read_binary_file(cachepath)
        return marshal.loads(dump)

    def _store(self, fullpath, dict):
        cachepath = self._cachename(fullpath)
        if logger: logger.info("[tenjin.MarshalCacheStorage] store cache (file=%r)" % (cachepath, ))
        _write_binary_file(cachepath, marshal.dumps(dict))


class PickleCacheStorage(FileCacheStorage):

    def __init__(self, postfix='.cache'):
        global pickle
        if pickle is None:
            try:    import cPickle as pickle
            except: import pickle
        FileCacheStorage.__init__(self, postfix)

    def _load(self, fullpath):
        cachepath = self._cachename(fullpath)
        if not _isfile(cachepath): return None
        if logger: logger.info("[tenjin.PickleCacheStorage] load cache (file=%r)" % (cachepath, ))
        dump = _read_binary_file(cachepath)
        return pickle.loads(dump)

    def _store(self, fullpath, dict):
        if 'bytecode' in dict: dict.pop('bytecode')
        cachepath = self._cachename(fullpath)
        if logger: logger.info("[tenjin.PickleCacheStorage] store cache (file=%r)" % (cachepath, ))
        _write_binary_file(cachepath, pickle.dumps(dict))


class TextCacheStorage(FileCacheStorage):

    def _load(self, fullpath):
        cachepath = self._cachename(fullpath)
        if not _isfile(cachepath): return None
        if logger: logger.info("[tenjin.TextCacheStorage] load cache (file=%r)" % (cachepath, ))
        s = _read_binary_file(cachepath)
        if python2:
            header, script = s.split("\n\n", 1)
        elif python3:
            header, script = s.split("\n\n".encode('ascii'), 1)
            header = header.decode('ascii')
        timestamp = encoding = args = None
        for line in header.split("\n"):
            key, val = line.split(": ", 1)
            if   key == 'timestamp':  timestamp = float(val)
            elif key == 'encoding':   encoding  = val
            elif key == 'args':       args      = val.split(', ')
        if python2:
            if encoding: script = script.decode(encoding)   ## binary(=str) to unicode
        elif python3:
            script = script.decode(encoding or 'utf-8')     ## binary to unicode(=str)
        return {'args': args, 'script': script, 'timestamp': timestamp}

    def _store(self, fullpath, dict):
        s = dict['script']
        if python2:
            if dict.get('encoding') and isinstance(s, unicode):
                s = s.encode(dict['encoding'])           ## unicode to binary(=str)
        sb = []
        sb.append("timestamp: %s\n" % dict['timestamp'])
        if dict.get('encoding'):
            sb.append("encoding: %s\n" % dict['encoding'])
        if dict.get('args') is not None:
            sb.append("args: %s\n" % ', '.join(dict['args']))
        sb.append("\n")
        sb.append(s)
        s = ''.join(sb)
        if python3:
            if isinstance(s, str):
                s = s.encode(dict.get('encoding') or 'utf-8')   ## unicode(=str) to binary
        cachepath = self._cachename(fullpath)
        if logger: logger.info("[tenjin.TextCacheStorage] store cache (file=%r)" % (cachepath, ))
        _write_binary_file(cachepath, s)

    def _save_data_of(self, template):
        dict = FileCacheStorage._save_data_of(self, template)
        dict['encoding'] = template.encoding
        return dict



##
## abstract class for data cache
##
class KeyValueStore(object):

    def get(self, key, *options):
        raise NotImplementedError("%s.get(): not implemented yet." % self.__class__.__name__)

    def set(self, key, value, *options):
        raise NotImplementedError("%s.set(): not implemented yet." % self.__class__.__name__)

    def delete(self, key, *options):
        raise NotImplementedError("%s.del(): not implemented yet." % self.__class__.__name__)

    def has(self, key, *options):
        raise NotImplementedError("%s.has(): not implemented yet." % self.__class__.__name__)


##
## memory base data cache
##
class MemoryBaseStore(KeyValueStore):

    def __init__(self):
        self.values = {}

    def get(self, key):
        pair = self.values.get(key)
        if not pair:
            return None
        value, timestamp = pair
        if timestamp and timestamp < _time():
            self.values.pop(key)
            return None
        return value

    def set(self, key, value, lifetime=0):
        ts = lifetime and _time() + lifetime or 0
        self.values[key] = (value, ts)
        return True

    def delete(self, key):
        try:
            del self.values[key]
            return True
        except KeyError:
            return False

    def has(self, key):
        pair = self.values.get(key)
        if not pair:
            return False
        value, timestamp = pair
        if timestamp and timestamp < _time():
            self.values.pop(key)
            return False
        return True


##
## file base data cache
##
class FileBaseStore(KeyValueStore):

    def __init__(self, root_path, encoding=None):
        if not os.path.isdir(root_path):
            raise ValueError("%r: directory not found." % (root_path, ))
        self.root_path = root_path
        if encoding is None and python3:
            encoding = 'utf-8'
        self.encoding = encoding

    _pat = re.compile(r'[^-.\/\w]')

    def filepath(self, key, _pat1=_pat):
        return os.path.join(self.root_path, _pat1.sub('_', key))

    def get(self, key):
        fpath = self.filepath(key)
        if not _isfile(fpath):
            return
        if _getmtime(fpath) < _time():
            os.unlink(fpath)
            return
        if self.encoding:
            return _read_text_file(fpath, self.encoding)
        else:
            return _read_binary_file(fpath)

    def set(self, key, value, lifetime=0):
        fpath = self.filepath(key)
        dirname = os.path.dirname(fpath)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        now = _time()
        if _is_unicode(value):
            value = value.encode(self.encoding or 'utf-8')
        _write_binary_file(fpath, value)
        ts = now + (lifetime or 604800)   # 60*60*24*7 = 604800
        os.utime(fpath, (ts, ts))
        return True

    def delete(self, key):
        fpath = self.filepath(key)
        if _isfile(fpath):
            os.unlink(fpath)
            return True
        return False

    def has(self, key):
        fpath = self.filepath(key)
        if not _isfile(fpath):
            return False
        if _getmtime(fpath) < _time():
            os.unlink(fpath)
            return False
        return True



##
## html fragment cache helper class
##
class FragmentCacheHelper(object):
    """html fragment cache helper.
       ex (main script):
           kv_store = tenjin.FileBaseStore('cache.d')
           not_cached, echo_cached = tenjin.FragmentCacheHelper(kv_store).functions()
           engine = tenjin.Engine()
           context = {'get_items': lambda: ['AAA', 'BBB', 'CCC'] }
           html = engine.render('template.pyhtml', context)
           print(html)
       ex (template):
           <?py if not_cached('item_list', 10): ?>
           <ol>
           <?py     for item in get_items(): ?>
             <li>${item}</li>
           <?py     #endif ?>
           </ol>
           <?py #endif ?>
           <?py echo_cached()  # necessary! ?>
    """

    lifetime = 60   # 1 minute
    prefix   = None

    def __init__(self, store, lifetime=None, prefix=None):
        self.store = store
        if lifetime is not None:  self.lifetime = lifetime
        if prefix   is not None:  self.prefix   = prefix

    def not_cached(self, cache_key, lifetime=None):
        """html fragment cache helper. see document of FragmentCacheHelper class."""
        context = sys._getframe(1).f_locals['_context']
        context['_cache_key'] = cache_key
        key = self.prefix and self.prefix + cache_key or cache_key
        value = self.store.get(key)
        if value:    ## cached
            if logger: logger.debug('[tenjin.not_cached] %r: cached.' % (cache_key, ))
            context[key] = value
            return False
        else:        ## not cached
            if logger: logger.debug('[tenjin.not_cached]: %r: not cached.' % (cache_key, ))
            if key in context: del context[key]
            if lifetime is None:  lifetime = self.lifetime
            context['_cache_lifetime'] = lifetime
            helpers.start_capture(cache_key, _depth=2)
            return True

    def echo_cached(self):
        """html fragment cache helper. see document of FragmentCacheHelper class."""
        f_locals = sys._getframe(1).f_locals
        context = f_locals['_context']
        cache_key = context.pop('_cache_key')
        key = self.prefix and self.prefix + cache_key or cache_key
        if key in context:    ## cached
            value = context.pop(key)
        else:                 ## not cached
            value = helpers.stop_capture(False, _depth=2)
            lifetime = context.pop('_cache_lifetime')
            self.store.set(key, value, lifetime)
        f_locals['_buf'].append(value)

    def functions(self):
        return (self.not_cached, self.echo_cached)

## you can change default store by 'tenjin.helpers.fragment_cache.store = ...'
helpers.fragment_cache = FragmentCacheHelper(MemoryBaseStore())
helpers.not_cached  = helpers.fragment_cache.not_cached
helpers.echo_cached = helpers.fragment_cache.echo_cached
helpers.__all__.extend(('not_cached', 'echo_cached'))



##
## template engine class
##

class Engine(object):
    """Template Engine class.
       See User's Guide and examples for details.
       http://www.kuwata-lab.com/tenjin/pytenjin-users-guide.html
       http://www.kuwata-lab.com/tenjin/pytenjin-examples.html
    """

    ## default value of attributes
    prefix     = ''
    postfix    = ''
    layout     = None
    templateclass = Template
    path       = None
    cache      = MarshalCacheStorage()  # save converted Python code into file by marshal-format
    preprocess = False
    timestamp_interval = 1  # seconds
    prefer_fullpath = False    # if True then use fullpath when template error is reported

    def __init__(self, prefix=None, postfix=None, layout=None, path=None, cache=True, preprocess=None, templateclass=None, **kwargs):
        """Initializer of Engine class.

           prefix:str (='')
             Prefix string used to convert template short name to template filename.
           postfix:str (='')
             Postfix string used to convert template short name to template filename.
           layout:str (=None)
             Default layout template name.
           path:list of str(=None)
             List of directory names which contain template files.
           cache:bool or CacheStorage instance (=True)
             Cache storage object to store converted python code.
             If True, default cache storage (=Engine.cache) is used (if it is None
             then create MarshalCacheStorage object for each engine object).
             If False, no cache storage is used nor no cache files are created.
           preprocess:bool(=False)
             Activate preprocessing or not.
           templateclass:class (=Template)
             Template class which engine creates automatically.
           kwargs:dict
             Options for Template class constructor.
             See document of Template.__init__() for details.
        """
        if prefix:  self.prefix  = prefix
        if postfix: self.postfix = postfix
        if layout:  self.layout  = layout
        if templateclass: self.templateclass = templateclass
        if path is not None:  self.path = path
        if preprocess is not None: self.preprocess = preprocess
        self.kwargs = kwargs
        self.encoding = kwargs.get('encoding')
        self._filepaths = {}   # template_name => relative path and absolute path
        self._added_templates = {}   # templates added by add_template()
        #self.cache = cache
        self._set_cache_storage(cache)

    def _set_cache_storage(self, cache):
        if cache is True:
            if not self.cache:
                self.cache = MarshalCacheStorage()
        elif cache is None:
            pass
        elif cache is False:
            self.cache = None
        elif isinstance(cache, CacheStorage):
            self.cache = cache
        else:
            raise ValueError("%r: invalid cache object." % (cache, ))

    def to_filename(self, template_name):
        """Convert template short name into filename.
           ex.
             >>> engine = tenjin.Engine(prefix='user_', postfix='.pyhtml')
             >>> engine.to_filename(':list')
             'user_list.pyhtml'
             >>> engine.to_filename('list')
             'list'
        """
        if template_name[0] == ':' :
            return self.prefix + template_name[1:] + self.postfix
        return template_name

    def _relative_and_absolute_path(self, filename):
        pair = self._filepaths.get(filename)
        if pair: return pair
        filepath = self._find_file(filename)
        if not filepath:
            raise IOError('%s: filename not found (path=%r).' % (filename, self.path, ))
        fullpath = os.path.abspath(filepath)
        self._filepaths[filename] = pair = (filepath, fullpath)
        return pair

    def _find_file(self, filename):
        if self.path:
            for dirname in self.path:
                filepath = os.path.join(dirname, filename)
                if _isfile(filepath):
                    return filepath
        else:
            if _isfile(filename):
                return filename
        return None

    def _create_template(self, filepath, _context, _globals):
        if filepath and self.preprocess:
            s = self._preprocess(filepath, _context, _globals)
            template = self.templateclass(None, **self.kwargs)
            template.convert(s, filepath)
        else:
            template = self.templateclass(filepath, **self.kwargs)
        return template

    def _preprocess(self, filepath, _context, _globals):
        #if _context is None: _context = {}
        #if _globals is None: _globals = sys._getframe(3).f_globals
        if '_engine' not in _context:
            self.hook_context(_context)
        preprocessor = Preprocessor(filepath)
        return preprocessor.render(_context, globals=_globals)

    def add_template(self, template):
        self._added_templates[template.filename] = template

    def get_template(self, template_name, _context=None, _globals=None):
        """Return template object.
           If template object has not registered, template engine creates
           and registers template object automatically.
        """
        filename = self.to_filename(template_name)
        if filename in self._added_templates:
            return self._added_templates[filename]
        filepath, fullpath = self._relative_and_absolute_path(filename)
        assert filepath and fullpath
        cache = self.cache
        template = cache and cache.get(fullpath, self.templateclass) or None
        mtime = None
        now = _time()
        if template:
            assert template.timestamp is not None
            if not template.filename:
                template.filename = self.prefer_fullpath and fullpath or filepath
            if now > getattr(template, '_last_checked_at', 0) + self.timestamp_interval:
                mtime = _getmtime(filepath)
                if template.timestamp != mtime:
                    #if cache: cache.delete(fullpath)
                    template = None
                    if logger: logger.info("[tenjin.Engine] cache is old (filepath=%r, template=%r)" % (filepath, template, ))
        if not template:
            if not mtime: mtime = _getmtime(filepath)
            if self.preprocess:   ## required for preprocess
                if _context is None: _context = {}
                if _globals is None: _globals = sys._getframe(1).f_globals
            template = self._create_template(filepath, _context, _globals)
            template.timestamp = mtime
            template._last_checked_at = now
            template.filename = self.prefer_fullpath and fullpath or filepath
            if cache:
                if not template.bytecode: template.compile()
                cache.set(fullpath, template)
        #else:
        #    template.compile()
        return template

    def include(self, template_name, append_to_buf=True, **kwargs):
        """Evaluate template using current local variables as context.

           template_name:str
             Filename (ex. 'user_list.pyhtml') or short name (ex. ':list') of template.
           append_to_buf:boolean (=True)
             If True then append output into _buf and return None,
             else return stirng output.

           ex.
             <?py include('file.pyhtml') ?>
             #{include('file.pyhtml', False)}
             <?py val = include('file.pyhtml', False) ?>
        """
        frame = sys._getframe(1)
        locals  = frame.f_locals
        globals = frame.f_globals
        assert '_context' in locals
        context = locals['_context']
        if kwargs:
            context.update(kwargs)
        ## context and globals are passed to get_template() only for preprocessing.
        template = self.get_template(template_name, context, globals)
        if append_to_buf:  _buf = locals['_buf']
        else:              _buf = None
        s = template.render(context, globals, _buf=_buf)
        if kwargs:
            for k in kwargs:
                del context[k]
        return s

    def render(self, template_name, context=None, globals=None, layout=True):
        """Evaluate template with layout file and return result of evaluation.

           template_name:str
             Filename (ex. 'user_list.pyhtml') or short name (ex. ':list') of template.
           context:dict (=None)
             Context object to evaluate. If None then new dict is used.
           globals:dict (=None)
             Global context to evaluate. If None then globals() is used.
           layout:str or Bool(=True)
             If True, the default layout name specified in constructor is used.
             If False, no layout template is used.
             If str, it is regarded as layout template name.

           If temlate object related with the 'template_name' argument is not exist,
           engine generates a template object and register it automatically.
        """
        if context is None:
            context = {}
        if globals is None:
            globals = sys._getframe(1).f_globals
        self.hook_context(context)
        while True:
            ## context and globals are passed to get_template() only for preprocessing
            template = self.get_template(template_name, context, globals)
            content  = template.render(context, globals)
            layout   = context.pop('_layout', layout)
            if layout is True or layout is None:
                layout = self.layout
            if not layout:
                break
            template_name = layout
            layout = False
            context['_content'] = content
        context.pop('_content', None)
        return content

    def hook_context(self, context):
        context['_engine'] = self
        #context['render'] = self.render
        context['include'] = self.include



##
## for Google App Engine
## (should separate into individual file or module?)
##

memcache = None      # lazy import of google.appengine.api.memcache


class GaeMemcacheCacheStorage(CacheStorage):

    lifetime = 0     # 0 means unlimited

    def __init__(self, lifetime=None, postfix='.cache', namespace=None):
        CacheStorage.__init__(self, postfix)
        if lifetime is not None:  self.lifetime = lifetime
        self.namespace = namespace

    def _load(self, fullpath):
        key = self._cachename(fullpath)
        if logger: logger.info("[tenjin.gae.GaeMemcacheCacheStorage] load cache (key=%r)" % (key, ))
        return memcache.get(key, namespace=self.namespace)

    def _store(self, fullpath, dict):
        if 'bytecode' in dict: dict.pop('bytecode')
        key = self._cachename(fullpath)
        if logger: logger.info("[tenjin.gae.GaeMemcacheCacheStorage] store cache (key=%r)" % (key, ))
        ret = memcache.set(key, dict, self.lifetime, namespace=self.namespace)
        if not ret:
            if logger: logger.info("[tenjin.gae.GaeMemcacheCacheStorage] failed to store cache (key=%r)" % (key, ))

    def _delete(self, fullpath):
        key = self._cachename(fullpath)
        memcache.delete(key, namespace=self.namespace)


class GaeMemcacheStore(KeyValueStore):

    lifetime = 0

    def __init__(self, lifetime=None, namespace=None):
        if lifetime is not None:  self.lifetime = lifetime
        self.namespace = namespace

    def get(self, key):
        return memcache.get(key, namespace=self.namespace)

    def set(self, key, value, lifetime=None):
        if lifetime is None:  lifetime = self.lifetime
        if memcache.set(key, value, lifetime, namespace=self.namespace):
            return True
        else:
            if logger: logger.info("[tenjin.gae.GaeMemcacheStore] failed to set (key=%r)" % (key, ))
            return False

    def delete(self, key):
        return memcache.delete(key, namespace=self.namespace)

    def has(self, key):
        if memcache.add(key, 'dummy', namespace=self.namespace):
            memcache.delete(key, namespace=self.namespace)
            return False
        else:
            return True


def init():
    global memcache
    if not memcache:
        from google.appengine.api import memcache
    ## avoid cache confliction between versions
    ver = os.environ.get('CURRENT_VERSION_ID').split('.')[0]
    Engine.cache = gae.GaeMemcacheCacheStorage(namespace=ver)
    ## set fragment cache store
    helpers.fragment_cache.store    = gae.GaeMemcacheStore(namespace=ver)
    helpers.fragment_cache.lifetime = 60    #  1 minute
    helpers.fragment_cache.prefix   = 'fragment.'


gae = _create_module('tenjin.gae')
gae.GaeMemcacheCacheStorage = GaeMemcacheCacheStorage
gae.GaeMemcacheStore        = GaeMemcacheStore
gae.init = init
del GaeMemcacheStore, GaeMemcacheCacheStorage, init
