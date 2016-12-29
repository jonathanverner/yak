from yak.content import content_format
from yak.meta import meta_format
from yak.formats.jinjatpl import content_jinja_format
from yak.utils import missing_feature

try:
    import markdown

    @content_format('md')
    def content_md_format(content, context):
        return markdown.markdown(content, extensions=['markdown.extensions.codehilite', 'markdown.extensions.fenced_code'])

    @content_format('tmd')
    def content_tmd_format(content, context):
        return content_md_format(content_jinja_format(content, context), context)

    @meta_format('md')
    def meta_md_format(val, meta):
        return markdown.markdown(val)

    content_md_format.scan_assets = True
    meta_md_format.scan_assets = True

except:
    missing_feature("content format", "To enable the markdown format, please install the markdown python package.")
