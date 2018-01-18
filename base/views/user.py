from flask import render_template, url_for, request, redirect, Blueprint, session

user_bp = Blueprint('user',
                    __name__)



@user_bp.route('/profile/<string:username>')
def user(username):
    """
        The User Profile
    """
    user = session.get('user')
    VARS = {'title': username,
            'user': user}
    return render_template('user.html', **VARS)