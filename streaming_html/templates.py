from os.path import join, dirname

from starlette.templating import Jinja2Templates

templates = Jinja2Templates(directory=join(dirname(__file__), "templates"))