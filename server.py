import os
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.escape
import tornado.gen
import webbrowser

import yaml
import logging

import threading
import io
import networkx as nx
from time import sleep
from contextlib import contextmanager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class VisualizationElement:
    """
    Defines an element of the visualization.
    Attributes:
        package_includes: A list of external JavaScript files to include that
                          are part of the packages.
        local_includes: A list of JavaScript files that are local to the
                        directory that the server is being run in.
        js_code: A JavaScript code string to instantiate the element.
    Methods:
        render: Takes a model object, and produces JSON data which can be sent
                to the client.
    """

    package_includes = []
    local_includes = []
    js_code = ''
    render_args = {}

    def __init__(self):
        pass

    def render(self, model):
        return '<b>VisualizationElement goes here</b>.'


class PageHandler(tornado.web.RequestHandler):
    """ Handler for the HTML template which holds the visualization. """

    def get(self):
        self.render('index.html', port=self.application.port,
                    model_name=self.application.model_name,
                    package_includes=self.application.package_includes,
                    local_includes=self.application.local_includes,
                    scripts=self.application.js_code)


class SocketHandler(tornado.websocket.WebSocketHandler):

    def open(self):
        if self.application.verbose:
            logger.info('Socket opened!')

    def check_origin(self, origin):
        return True

    def on_message(self, message):
        """ Receiving a message from the websocket, parse, and act accordingly. """

        msg = tornado.escape.json_decode(message)

        if msg['type'] == 'config_file':

            if self.application.verbose:
                print(msg['data'])

            self.config = list(yaml.load_all(msg['data']))

            if len(self.config) > 1:
                error = 'Please, provide only one configuration.'
                if self.application.verbose:
                    logger.error(error)
                self.write_message({'type': 'error',
                    'error': error})
                return
            else:
                self.config = self.config[0]
                self.send_log('INFO.soil', 'Using config: {name}'.format(name=self.config['name']))

            self.name = self.config['name']
            self.run_simulation()

            settings = []
            for key in self.config['environment_params']: 
                if type(self.config['environment_params'][key]) == float:
                    setting_type = 'number'
                elif type(self.config['environment_params'][key]) == bool:
                    setting_type = 'boolean'
                else:
                    setting_type = 'undefined'

                settings.append({
                    'label': key,
                    'type': setting_type,
                    'value': self.config['environment_params'][key]
                })

            self.write_message({'type': 'settings',
                'data': settings})

        elif msg['type'] == 'get_trial':
            if self.application.verbose:
                logger.info('Trial {} requested!'.format(msg['data']))
            self.send_log('INFO.user', 'Trial {} requested!'.format(msg['data']))
            self.write_message({'type': 'get_trial',
                'data': self.get_trial( int(msg['data'] )) })

        elif msg['type'] == 'run_simulation':
            self.send_log('INFO.soil', 'Running new simulation for {name}'.format(name=self.config['name']))
            self.config['environment_params'] = msg['data']
            self.run_simulation()

        else:
            if self.application.verbose:
                logger.info('Unexpected message!')

    def update_logging(self):
        try:
            if (not self.log_capture_string.closed and self.log_capture_string.getvalue()):
                for i in range(len(self.log_capture_string.getvalue().split('\n')) - 1):
                    self.send_log('INFO.soil', self.log_capture_string.getvalue().split('\n')[i])
                self.log_capture_string.truncate(0)
                self.log_capture_string.seek(0)
        finally:
            if self.capture_logging:
                thread = threading.Timer(0.01, self.update_logging)
                thread.start()

    def on_close(self):
        logger.info('Socket closed!')

    def send_log(self, logger, logging):
        self.write_message({'type': 'log',
            'logger': logger,
            'logging': logging })

    def run_simulation(self):
        # Run simulation and capture logs
        with self.logging(self.application.model.name):
            self.simulation = self.application.model.run(self.config)

        trials = []
        for i in range(self.config['num_trials']):
            trials.append('{}_trial_{}'.format(self.name, i))
        self.write_message({'type': 'trials',
            'data': trials })

    def get_trial(self, trial):
        G = self.simulation[trial].history_to_graph()
        return nx.node_link_data(G)

    @contextmanager
    def logging(self, logger):
        self.capture_logging = True
        self.logger_application = logging.getLogger(logger)
        self.log_capture_string = io.StringIO()
        ch = logging.StreamHandler(self.log_capture_string)
        self.logger_application.addHandler(ch)
        self.update_logging()
        yield self.capture_logging

        sleep(0.2)
        self.log_capture_string.close()
        self.logger_application.removeHandler(ch)
        self.capture_logging = False
        return self.capture_logging
    

class ModularServer(tornado.web.Application):
    """ Main visualization application. """

    portrayal_method = None
    port = 8001
    model_args = ()
    model_kwargs = {}
    page_handler = (r'/', PageHandler)
    socket_handler = (r'/ws', SocketHandler)
    static_handler = (r'/(.*)', tornado.web.StaticFileHandler,
                      {'path': 'templates'})
    local_handler = (r'/local/(.*)', tornado.web.StaticFileHandler,
                     {'path': ''})

    handlers = [page_handler, socket_handler, static_handler, local_handler]
    settings = {'debug': True,
                'template_path': os.path.dirname(__file__) + '/templates'}

    def __init__(self, model, visualization_element, name='SOIL Model', verbose=True,
                 *args, **kwargs):
        
        self.verbose = verbose
        self.package_includes = set()
        self.local_includes = set()
        self.js_code = []
        
        self.visualization_element = visualization_element

        self.model_name = name
        self.model = model
        self.model_args = args
        self.model_kwargs = kwargs
        #self.reset_model()

        # Initializing the application itself:
        super().__init__(self.handlers, **self.settings)

    '''
    def reset_model(self):
        self.model = self.model_cls(*self.model_args, **self.model_kwargs)
    '''

    def render_model(self):
        return self.visualization_element.render(self.model)

    def launch(self, port=None):
        """ Run the app. """
        
        if port is not None:
            self.port = port
        url = 'http://127.0.0.1:{PORT}'.format(PORT=self.port)
        print('Interface starting at {url}'.format(url=url))
        self.listen(self.port)
        # webbrowser.open(url)
        tornado.ioloop.IOLoop.instance().start()
