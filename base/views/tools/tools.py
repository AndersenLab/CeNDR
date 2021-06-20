from flask import (render_template,
                   Blueprint)


# Tools blueprint
tools_bp = Blueprint('tools',
                     __name__,
                     template_folder='tools')


@tools_bp.route('/')
def tools():
  disable_parent_breadcrumb = True
  return render_template('tools/tools.html', **locals())

