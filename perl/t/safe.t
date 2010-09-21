###
### $Release:$
### $Copyright$
### $License$
###

BEGIN {
    unshift @INC, "t"   if -f "t/Specofit.pm";
    unshift @INC, "lib" if -f "lib/Tenjin.pm";
}

use strict;
use Data::Dumper;
use Test::More tests => 18;
use Specofit;
use Tenjin;
$Tenjin::USE_STRICT = 1;


*read_file  = *Tenjin::Util::read_file;
*write_file = *Tenjin::Util::write_file;


spec_of "Tenjin::SafeStr", sub {


    spec_of "->new", sub {

        it "returns Tenjin::SafeStr object", sub {
            my $obj = Tenjin::SafeStr->new('<A&B>');
            is ref($obj), "Tenjin::SafeStr";
            is repr($obj), q|bless( {"value" => "<A&B>"}, 'Tenjin::SafeStr' )|;
        };

    };


    spec_of "#value", sub {

        it "converts Tenjin::SafeStr to normal string", sub {
            my $obj = Tenjin::SafeStr->new('<A&B>');
            is $obj->value, '<A&B>';
        };

    };


};



spec_of "Tenjin::SafeTemplate", sub {


    spec_of "#convert", sub {

        it "generates script to check whether value is safe string or not", sub {
            my $t = Tenjin::SafeTemplate->new(undef);
            my $input = "<div>\n[= \$_content =]\n</div>\n";
            my $expected = <<'END';
	my $_buf = ""; my $_V;  $_buf .= q`<div>
	` . (ref($_V = ( $_content )) eq 'Tenjin::SafeStr' ? $_V->{value} : ($_V =~ s/[&<>"]/$Tenjin::_H{$&}/ge, $_V)) . q`
	</div>
	`;  $_buf;
END
            $expected =~ s/^\t//mg;
            is $t->convert($input), $expected;
        };

        it "refuses to compile '[== expr =]'", sub {
            my $t = Tenjin::SafeTemplate->new(undef);
            my $input = "<div>\n[== \$_content =]\n</div>\n";
            eval { $t->convert($input); };
            $_ = $@;
            s/ at .*$//;
            is $_, "'[== \$_content =]': '[== =]' is not available with Tenjin::SafeTemplate.\n";
        };

        it "bypass to escape value if safe_str() is called directly", sub {
            my $t = Tenjin::SafeTemplate->new();
            my $ret = $t->convert('<div>[= safe_str($expr) =]</div>');
            is $ret, 'my $_buf = ""; my $_V;  $_buf .= q`<div>` . ( $expr ) . q`</div>`;  $_buf;'."\n";
            my $ret = $t->convert("<div>[=\tsafe_str(\n\$expr\n)  =]</div>");
            is $ret, "my \$_buf = \"\"; my \$_V;  \$_buf .= q`<div>` . (\t\n\$expr\n  ) . q`</div>`;  \$_buf;\n";
        };

    };


    spec_of "#render", sub {

        it "doesn't escape safe string value", sub {
            my $t = Tenjin::SafeTemplate->new(undef);
            my $input = "<div>\n[= \$_content =]\n</div>\n";
            $t->convert($input);
            my $actual = $t->render({_content => '<AAA&BBB>'});
            is $actual, "<div>\n&lt;AAA&amp;BBB&gt;\n</div>\n";
            my $actual = $t->render({_content => Tenjin::SafeStr->new('<AAA&BBB>')});
            is $actual, "<div>\n<AAA&BBB>\n</div>\n";
        };

    };


};



spec_of "Tenjin::SafePreprocessor#convert", sub {


    spec_of "#convert", sub {

        it "generates script to check whether value is safe string or not", sub {
            my $pp = Tenjin::SafePreprocessor->new();
            my $ret = $pp->convert('<<[*=$x=*]>>');
            is $ret, 'my $_buf = ""; my $_V;  $_buf .= q`<<` . (ref($_V = ($x)) eq \'Tenjin::SafeStr\' ? Tenjin::Util::_decode_params($_V->{value}) : ($_V = Tenjin::Util::_decode_params($_V), $_V =~ s/[&<>"]/$Tenjin::_H{$&}/ge, $_V)) . q`>>`;  $_buf;'."\n";
        };

        it "refuses to compile '[== expr =]'", sub {
            my $pp = Tenjin::SafePreprocessor->new();
            eval { $pp->convert('<<[*==$x=*]>>'); };
            $_ = $@;
            s/ at .*$//;
            is $_, "'[*==\$x=*]': '[*== =*]' is not available with Tenjin::SafePreprocessor."."\n";
            $@ = '';
        };

    };


};



spec_of "Tenjin::SafeEngine", sub {

    my $INPUT = <<'END';
	<ul>
	  <?pl for (@$items) { ?>
	  <li>[= $_ =]</li>
	  <?pl } ?>
	</ul>
END
    $INPUT =~ s/^\t//mg;

    my $SCRIPT = <<'END';
	my $_buf = ""; my $_V;  $_buf .= q`<ul>
	`;   for (@$items) {
	 $_buf .= q`  <li>` . (ref($_V = ( $_ )) eq 'Tenjin::SafeStr' ? $_V->{value} : ($_V =~ s/[&<>"]/$Tenjin::_H{$&}/ge, $_V)) . q`</li>
	`;   }
	 $_buf .= q`</ul>
	`;  $_buf;
END
    $SCRIPT =~ s/^\t//mg;

    my $EXPECTED = <<'END';
	<ul>
	  <li>&lt;br&gt;</li>
	  <li><BR></li>
	</ul>
END
    $EXPECTED =~ s/^\t//mg;

    my $INPUT2 = <<'END';
	<div>
	  <p>v1=[=$v1=]</p>
	  <p>v2=[=$v2=]</p>
	</div>
	<div>
	  <p>v1=[*=$v1=*]</p>
	  <p>v2=[*=$v2=*]</p>
	</div>
END
    $INPUT2 =~ s/^\t//mg;

    my $SCRIPT2 = <<'END';
	my $_buf = ""; my $_V;  $_buf .= q`<div>
	  <p>v1=` . (ref($_V = ($v1)) eq 'Tenjin::SafeStr' ? $_V->{value} : ($_V =~ s/[&<>"]/$Tenjin::_H{$&}/ge, $_V)) . q`</p>
	  <p>v2=` . (ref($_V = ($v2)) eq 'Tenjin::SafeStr' ? $_V->{value} : ($_V =~ s/[&<>"]/$Tenjin::_H{$&}/ge, $_V)) . q`</p>
	</div>
	<div>
	  <p>v1=&lt;&amp;&gt;</p>
	  <p>v2=<&></p>
	</div>
	`;  $_buf;
END
    $SCRIPT2 =~ s/^\t//mg;

    my $EXPECTED2 = <<'END';
	<div>
	  <p>v1=&lt;&amp;&gt;</p>
	  <p>v2=<&></p>
	</div>
	<div>
	  <p>v1=&lt;&amp;&gt;</p>
	  <p>v2=<&></p>
	</div>
END
    $EXPECTED2 =~ s/^\t//mg;

    my $CONTEXT = {
        items => [ "<br>", Tenjin::SafeStr->new("<BR>") ],
    };

    pre_task {
        unlink glob("_ex.plhtml*");
        write_file("_ex.plhtml", $INPUT);
        unlink glob("_ex2.plhtml*");
        write_file("_ex2.plhtml", $INPUT2);
    };

    my $engine;


    spec_of "->new", sub {

        my $engine = Tenjin::SafeEngine->new();

        it "sets 'templateclass' attribute to 'SafeTemplate'", sub {
            is $engine->{templateclass}, 'Tenjin::SafeTemplate';
            my $t = $engine->get_template("_ex.plhtml");
            is ref($t), 'Tenjin::SafeTemplate';
            is $t->{script}, $SCRIPT;
        };

        it "sets 'preprocessor' attribute to 'SafePreprocessor'", sub {
            is $engine->{preprocessorclass}, 'Tenjin::SafePreprocessor';
        }

    };

    unlink glob("_ex.plhtml.*");


    spec_of "#render", sub {

        it "prints safe string as it is", sub {
            my $e = Tenjin::SafeEngine->new();
            my $output = $e->render("_ex.plhtml", $CONTEXT);
            is $output, $EXPECTED;
        };

        it "supports preprocessing with SafePreprocessor class", sub {
            my $e = Tenjin::SafeEngine->new({preprocess=>1});
            my $context = { v1=>'<&>', v2=>Tenjin::SafeStr->new('<&>') };
            my $output = $e->render("_ex2.plhtml", $context);
            my $t = $e->get_template('_ex2.plhtml');
            is $t->{script}, $SCRIPT2;
            is $output, $EXPECTED2;
        };

    };


    post_task {
        unlink glob("_ex.plhtml*");
        unlink glob("_ex2.plhtml*");
    };


};