import logging

import webapp2

def handle_404(request, response, exception):
    logging.exception(exception)
    response.write('Oops! I could swear this page was here!')
    response.set_status(404)

def handle_500(request, response, exception):
    logging.exception(exception)
    response.write('A server error occurred!')
    response.set_status(500)

app = webapp2.WSGIApplication([
    webapp2.Route(r'/', handler='handlers.HomeHandler', name='home')
])
app.error_handlers[404] = handle_404
app.error_handlers[500] = handle_500