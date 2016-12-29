import os
from yak.shell import pipe
from yak.filters import install_filter

try:
    from scss import Scss
    compiler = Scss()

    @install_filter('sass')
    def sass_filter(bytes, cwd):
        os.chdir(cwd)
        return compiler.compile(bytes)
except:
    @install_filter('sass')
    def sass_filter(bytes, cwd):
        return pipe('sass --scss', bytes, cwd=cwd)
