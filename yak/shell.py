import os
import subprocess
import sha
import logging

from .filters import INSTALL_FILTERS


logger = logging.getLogger(__name__)


def hash(path):
    """
        Computes and returns the SHA hash of the file
        :param:`path`.
    """
    data = open(path).read()
    h = sha.sha(data)
    return h.hexdigest()


def pipe(program, input, cwd=None):
    """
        Pipe :param:`input` into the program :param:`program` run in
        the directory :param:`cwd`. Returns the program output stream.
    """
    p = subprocess.Popen(program, stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True, cwd=cwd)
    return p.communicate(input)[0]

def cp(src, dst, create_parents=False, filters=[]):
    """
        Copies the file :param:`src` to the destination :param:`dst`,
        optionally creating the necessary parent directories of :param:`dst`
        if they don't exist and :param:`create_parents` is set to True.
        The :param:`filters` param is a list of filters the file is passed
        through before it is output. Filters can either be python functions
        (see filters.py) or names of programs. The filters are run in the
        directory where the file :param:`src` is located.
    """
    src_dir = os.path.dirname(src)
    if create_parents:
        mkdir_p(os.path.dirname(dst))
    s = open(src).read()
    for f in filters:
        if f in INSTALL_FILTERS:
            s = INSTALL_FILTERS[f](s, cwd=src_dir)
        else:
            s = pipe(f, s, cwd=src_dir)
    open(dst, 'w').write(s)

def mkdir_p(path):
    """
        Equivalent of mkdir -p
    """
    dirs = path.split(os.sep)
    parent = ''
    for d in dirs:
        path = parent+d
        if os.path.exists(path):
            if not os.path.isdir(path):
                raise BaseException("Path component '"+parent+d+"' is a file")
        else:
            os.mkdir(path)
        parent = parent + d + posixpath.sep


def ls(path, pattern, recursive):
    """
        Lists all files in :param:`path` matching the regular expression
        :param:`pattern`. If :param:`recursive` is true, recursively includes
        files all subdirectories.
    """
    ret = []
    if not os.path.isdir(path):
        return [path]
    for node in os.listdir(path):
        try:
            if re.match(pattern, node):
                node_path = os.path.join(path, node)
                if os.path.isdir(node_path):
                    if recursive:
                        ret.extend(ls(os.path.join(node_path), pattern, recursive))
                else:
                    ret.append(node_path)
        except Exception as e:
            logger.error("Exception "+str(e)+" when listing assets in '"+path+"' matching pattern '"+pattern+"'")
    return ret

def get_extension(path):
    """
        Returns the extension part (i.e. the part after the last dot) of
        the file path :param:`path`
    """
    base = os.path.basename(path)
    n = len(base)-1
    while n >= 0:
        if base[n] == '.':
            return base[n+1:]
        n = n-1
    return base


def strip_extension(path):
    """
        Removes the extension (i.e. the part after the last dot) of the
        file path :param:`path`
    """
    base = os.path.basename(path)
    n = len(base)-1
    while n >= 0:
        if base[n] == '.':
            return base[:n]
        n = n-1
    return base