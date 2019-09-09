from delfick_project.norms import sb, va

from docutils.statemachine import ViewList
from docutils.parsers.rst import Directive
from textwrap import dedent
from docutils import nodes


class ShowDirective(Directive):
    """Directive for outputting all the specs found in input_algorithms.spec_base.default_specs"""

    def run(self):
        sections = []
        for name, spec in self.showing:
            sect = nodes.section()
            sect["ids"].append(name)

            title = nodes.title()
            title += nodes.Text(name)
            sect += title

            viewlist = ViewList()
            for line in dedent(spec.__doc__).split("\n"):
                if line:
                    viewlist.append("    {0}".format(line), name)
                else:
                    viewlist.append("", name)
            self.state.nested_parse(viewlist, self.content_offset, sect)
            sections.append(sect)

        return sections


class ShowSpecsDirective(ShowDirective):
    showing = sb.default_specs


class ShowValidatorsDirective(ShowDirective):
    showing = va.default_validators


def setup(app):
    """Setup the show_specs directive"""
    app.add_directive("show_specs", ShowSpecsDirective)
    app.add_directive("show_validators", ShowValidatorsDirective)
