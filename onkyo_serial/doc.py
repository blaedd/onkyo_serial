"""Sphinx extensions used for onkyo_serial documentation."""

from docutils.nodes import reference
from docutils.parsers.rst.roles import set_classes


# pylint: disable=too-many-arguments,unused-argument
# noinspection PyUnusedLocal
def role_twisted(name, rawtext, text, lineno, inliner, options=None,
                 content=None):
    """
    Aliases :twisted:`twisted.internet` to
      'https://twistedmatrix.com/documents/14.0.1/api/twisted.internet.html

    :param name: the role name used in the document
    :param rawtext: the entire markup snippet, with role
    :param text: the text marked with the role
    :param lineno: the line number where rawtext appears in the input
    :param inliner: the inliner instance that called us
    :param options: directive options for customization
    :param content: the directive content for customization

    """

    # checking if the number is valid
    if not text.startswith('twisted'):
        msg = inliner.reporter.error(
            'Invalid twisted class: %s' % text, line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    app = inliner.document.settings.env.app
    slug = text + '.html'
    return (
        [make_link_node(rawtext, app, text, slug, options)],
        [],
    )


def make_link_node(rawtext, app, link_text, slug, options):
    """
    Creates a link to a trac ticket.

    :param rawtext: text being replaced with link node
    :param app: sphinx application context
    :param link_text: text for the link
    :param slug: ID of the thing to link to
    :param options: options dictionary passed to role func

    """

    options = options or {}
    base_url = app.config.twisted_url

    if not base_url:
        raise ValueError(
            "'twisted_url' isn't set in our config")
    ref = base_url.rstrip('/') + '/' + slug
    set_classes(options)

    return reference(rawtext, link_text, refuri=ref, **options)


def setup(app):
    """
    Installs the plugin.
    :param app: sphinx application context
    """

    app.add_role('twisted', role_twisted)
    app.add_config_value('twisted_url', None, 'env')
