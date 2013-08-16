#! /usr/bin/python

# PyGreen
# Copyright (c) 2013, Nicolas Vanhoren
# 
# Released under the MIT license
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
# AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals, print_function

import bottle
import os.path
from mako.lookup import TemplateLookup
import os, os.path, itertools
import wsgiref.handlers
import sys, logging, re
import argparse
import sys
import markdown
import waitress
import utils

_logger = logging.getLogger(__name__)

# always adds the location of the default templates

op = os.path


class PyGreen:
    TEMPLATE_DIR = op.abspath(op.join(op.split(__file__)[0], "templates"))

    def __init__(self):

        # the Bottle application
        self.app = bottle.Bottle()
        # a set of strings that identifies the extension of the files
        # that should be processed using Mako
        self.template_exts = set(["html"])
        # the folder where the files to serve are located. Do not set
        # directly, use set_folder instead
        self.folder = "."
        # the TemplateLookup of Mako
        self.templates = TemplateLookup(directories=[self.folder, self.TEMPLATE_DIR],
                                        imports=["from markdown import markdown"],
                                        input_encoding='iso-8859-1',
                                        collection_size=100,
        )
        # A list of regular expression. Files whose the name match
        # one of those regular expressions will not be outputed when generating
        # a static version of the web site
        self.file_exclusion = [r".*\.mako", r".*\.py", r"(^|.*\/)\..*"]

        def is_public(path):
            for ex in self.file_exclusion:
                if re.match(ex, path):
                    return False
            return True

        def base_lister():
            files = []
            for dirpath, dirnames, filenames in os.walk(self.folder):
                filenames.sort()
                for f in filenames:
                    absp = os.path.join(dirpath, f)
                    path = os.path.relpath(absp, self.folder)
                    if is_public(path):
                        files.append(path)
            return files

            # A list of function. Each function must return a list of paths

        # of files to export during the generation of the static web site.
        # The default one simply returns all the files contained in the folder.
        # It is necessary to define new listers when new routes are defined
        # in the Bottle application, or the static site generation routine
        # will not be able to detect the files to export.
        self.file_listers = [base_lister]

        def file_renderer(path):
            if is_public(path):
                if path.split(".")[-1] in self.template_exts and self.templates.has_template(path):
                    f = utils.File(fname=path, root=self.folder)
                    t = self.templates.get_template(path)
                    data = t.render_unicode(pygreen=self, f=f, u=utils, files=self.files)
                    return data.encode(t.module._source_encoding)
                return bottle.static_file(path, root=self.folder)
            return bottle.HTTPError(404, 'File does not exist.')

            # The default function used to render files. Could be modified to change the way files are

        # generated, like using another template language or transforming css...
        self.file_renderer = file_renderer
        self.app.route('/', method=['GET', 'POST', 'PUT', 'DELETE'])(lambda: self.file_renderer('index.html'))
        self.app.route('/<path:path>', method=['GET', 'POST', 'PUT', 'DELETE'])(lambda path: self.file_renderer(path))

    def set_folder(self, folder):
        """
        Sets the folder where the files to serve are located.
        """
        self.folder = folder
        self.templates.directories[0] = folder
        if self.folder not in sys.path:
            sys.path.append(self.folder)

    def run(self, host='0.0.0.0', port=8080):
        """
        Launch a development web server.
        """
        waitress.serve(self, host=host, port=port)

    def get(self, f):
        """
        Get the content of a file, indentified by its path relative to the folder configured
        in PyGreen. If the file extension is one of the extensions that should be processed
        through Mako, it will be processed.
        """
        handler = wsgiref.handlers.SimpleHandler(sys.stdin, sys.stdout, sys.stderr, {})
        handler.setup_environ()
        env = handler.environ
        env.update({'PATH_INFO': "/%s" % f.fname, 'REQUEST_METHOD': "GET"})
        out = b"".join(self.app(env, lambda *args: None))
        return out

    @property
    def settings(self):
        m = __import__('settings', globals(), locals(), [], -1)
        reload(m)
        return m

    def links(self, patt=".", root=".", short=True):
        "Produces name, links pairs from file names"

        def match(item):
            return re.search(patt, item)

        def split(item):
            head, tail = os.path.split(item)
            base, ext = os.path.splitext(tail)

            if short:
                name = base.title().replace("-", " ").replace("_", " ")
            else:
                name = item
            return name, os.path.join(root, item)

        items = filter(match, self.files)
        pairs = map(split, items)
        return pairs

    def toc(self, patt=".", root=".", short=True):
        "Produces name, links pairs from file names"

        def match(item):
            return re.search(patt, item)

        def split(item):
            head, tail = os.path.split(item)
            base, ext = os.path.splitext(tail)

            if short:
                name = base.title().replace("-", " ").replace("_", " ")
            else:
                name = item
            return name, os.path.join(root, item)

        items = filter(match, self.files)
        pairs = map(split, items)
        return pairs

    @property
    def files(self):
        """
        Collects all files that will be parsed. Will also be available in main context.
        TODO: this method crawls the entire directory tree each time it is accessed.
        It is handy during development but very large trees may affect performance.
        """
        files = []
        for l in self.file_listers:
            files += l()
        return files

    def collect(self):
        """
        Collects all files that will be parsed. Will also be available in main context.
        TODO: this method crawls the entire directory tree each time it is accessed.
        It is handy during development but very large trees may affect performance.
        """
        files = []
        for l in self.file_listers:
            files += l()

        return map(lambda x: utils.File(x, self.folder), files)

    def gen_static(self, output_folder):
        """
        Generates a complete static version of the web site. It will stored in 
        output_folder.
        """

        # this makes all files available in the template context
        for f in self.collect():
            if f.skip_file:
                _logger.info("skipping large file %s of %.1fkb" % (f.fname, f.size))
                continue
            _logger.info("generating %s" % f.fname)
            content = self.get(f)
            f.write(output_folder, content)

    def __call__(self, environ, start_response):
        return self.app(environ, start_response)

    def cli(self, cmd_args=None):
        """
        The command line interface of PyGreen.
        """
        logging.basicConfig(level=logging.INFO, format='%(message)s')

        parser = argparse.ArgumentParser(description='PyGreen, micro web framework/static web site generator')
        subparsers = parser.add_subparsers(dest='action')

        parser_serve = subparsers.add_parser('serve', help='serve the web site')
        parser_serve.add_argument('-p', '--port', type=int, default=8080, help='folder containg files to serve')
        parser_serve.add_argument('-f', '--folder', default=".", help='folder containg files to serve')
        parser_serve.add_argument('-d', '--disable-templates', action='store_true', default=False,
                                  help='just serve static files, do not use invoke Mako')

        def serve():
            if args.disable_templates:
                self.template_exts = set([])
            self.run(port=args.port)

        parser_serve.set_defaults(func=serve)

        parser_gen = subparsers.add_parser('gen', help='generate a static version of the site')
        parser_gen.add_argument('output', help='folder to store the files')
        parser_gen.add_argument('-f', '--folder', default=".", help='folder containg files to serve')

        def gen():
            self.gen_static(args.output)

        parser_gen.set_defaults(func=gen)

        args = parser.parse_args(cmd_args)
        self.set_folder(args.folder)
        print(parser.description)
        print("")
        args.func()


pygreen = PyGreen()

if __name__ == "__main__":
    pygreen.cli()