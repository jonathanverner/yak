from yak.formats.jinjatpl import template_filter


@template_filter('YOUTUBE')
def youtube_filter(video, playlist, width='"853"', height='"480"'):
    return '<iframe width={width} height={height} src="https://www.youtube-nocookie.com/embed/{id}?list={playlist_id}&amp;showinfo=0" frameborder="0" allowfullscreen></iframe>'.format(id=video, playlist_id=playlist, width=width, height=height)


@template_filter('VIMEO')
def vimeo_filter(video, color=None, width="700px", height="394px", title=False, byline=False, portrait=False, frameborder="0", css_class=""):
    attrs = {
              'width': width,
              'height': height,
              'frameborder': frameborder,
              "class": css_class
              }
    params = {
              'title': '0',
              'byline': '0',
              'portrait': '0'
             }
    if title:
        params['title'] = '1'
    if byline:
        params['byline'] = '1'
    if color:
        params['color'] = color
    if portrait:
        params['portrait'] = portrait
    query_string = '&'.join([str(key)+'='+str(val) for (key, val) in params.items()])
    attr_string = ' '.join([str(key)+'="'+str(val)+'"' for (key, val) in attrs.items()])
    return '<iframe src="https://player.vimeo.com/video/{video_id}?{query_string}" {attr_string} webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>'.format(video_id=video, query_string=query_string, attr_string=attr_string)


@template_filter('DOI')
def doi_filter(value):
    return 'http://dx.doi.org/'+value
