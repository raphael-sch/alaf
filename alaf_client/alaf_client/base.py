from socketIO_client import SocketIO, LoggingNamespace
import time
import logging
import threading
logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
logging.basicConfig()


class BaseALModel(object):

    def __init__(self, project_name, name, host='localhost', port=5000, simulation=False):
        """
        Connect to the server and send initial scores. If simulation mode, start background thread
        to send annotated instances and scores to the server. Wait for any events from the server.
        :param project_name: Name of the project
        :param name: name of this model/client
        :param host: host url/ip
        :param port: port of host
        :param simulation: simulation mode
        """
        self.project_name = project_name
        self.name = name
        self.host = host
        self.port = port
        self.simulation = simulation

        self.registered = False

        if self.host == 'dummy':
            return

        self.socketIO = None
        self.namespace = None

        scores = self.get_scores()
        count = self.get_count()

        self._connect()
        self._on_events()

        logging.info('start with scores: {} at count: {}'.format(scores, count))
        self._emit_scores(scores, count)

        if self.simulation:
            threading.Thread(target=self._run_simulation, daemon=True).start()

        self.socketIO.wait()

    def _connect(self):
        """
        Initiate namespace for socketIO and connect to server.
        """
        namespace_cls = self._get_namespace()
        self.socketIO = SocketIO(self.host, self.port)
        self.namespace = self.socketIO.define(namespace_cls, '/model')
        time.sleep(5)

    def _get_namespace(self):
        """
        Add connect and reconnect listener to namespace to catch connect event and
        send register message to server.
        :return:
        """
        outer = self

        class ALModelNamespace(LoggingNamespace):
            def on_connect(self):
                message = outer._get_register_message()
                self.emit('register', message)
                super(ALModelNamespace, self).on_connect()

            def on_reconnect(self):
                message = outer._get_register_message()
                self.emit('register', message)
                super(ALModelNamespace, self).on_reconnect()

        return ALModelNamespace

    def _get_register_message(self):
        """
        Compose register message for the server. Server checks if project
        model combination if available and tags this client as online
        :return: registration message
        """
        message = {'project_name': self.project_name,
                   'model_name': self.name,
                   'count': self.get_count()}
        return message

    def _on_events(self):
        """
        Add event listeners to socketIO.
        :return:
        """
        self.namespace.on('annotation', self._on_annotation)
        self.namespace.on('next_utterance', self._on_next_utterance)
        self.namespace.on('finished', self._on_finished)

    def _on_annotation(self, message):
        """
        Annotation event receives message from server containing utterance and human annotation.
        Emits next selected utterance to server.
        :param message: utterance and annotation from server
        """
        logging.info('received: {}'.format(message))
        io_time_start = message['io_time_start']
        client_time_start = time.time()
        self.add_instance(utterance=message['utterance'],
                          annotation=message['annotation'])

        scores = self.get_scores()
        self._emit_scores(scores)

        self._emit_next_utterance(client_time_start,
                                  io_time_start,
                                  prev_annotation=message['annotation'])

    def _on_finished(self, message):
        """
        Client gets disconnected on 'finished' message from server. Includes the cause to shut client down.
        :param message: cause
        """
        cause = message['cause']
        logging.info('Server is finished with client: {}'.format(cause))
        self.socketIO.disconnect()

    def _on_next_utterance(self, message):
        """
        Select and emit the next utterance to the server.
        :param message: io_time_start: timestamp of serverside transmission start
        """
        if self.simulation:
            return
        io_time_start = message['io_time_start']
        self._emit_next_utterance(io_time_start,
                                  prev_annotation=None)

    def _emit_register(self):
        """
        Send register message to server.
        :return:
        """
        message = self._get_register_message()
        self.namespace.emit('register', message)

    def _emit_utterance(self, utterance, client_time, al_time, io_time_start, label=None):
        """
        Compose the next utterance message for the server. Includes the utterance and several time measures.
        :param utterance: text
        :param client_time: total time spent on the client
        :param al_time: time spent for the al algorithm
        :param io_time_start: timestamp of serverside transmission start
        :param label: is simulation mode, attach label
        """
        count = self.get_count()
        message = {'utterance': utterance,
                   'label': label if self.simulation else None,
                   'count': count,
                   'client_time': client_time,
                   'al_time': al_time,
                   'io_time_start': io_time_start}
        self.namespace.emit('utterance', message)
        logging.info("Sent utterance '{}' at count {}".format(utterance, count))

    def _emit_next_utterance(self, client_time_start=None, io_time_start=None, prev_annotation=None):
        """
        Query the AL algorithm to get next utterance and send it to the server.
        Keeps track of different times during computations.
        :param client_time_start: timestamp when client receives instance
        :param io_time_start: timestamp of serverside transmission start
        :return:
        """
        if client_time_start is None:
            client_time_start = time.time()
        if io_time_start is None:
            io_time_start = time.time()

        al_time_start = time.time()
        utterance, label = self.get_next_utterance(prev_annotation)

        time_end = time.time()
        client_time = time_end - client_time_start
        al_time = time_end - al_time_start

        self._emit_utterance(utterance,
                             client_time,
                             al_time,
                             io_time_start,
                             label=label)
        return utterance, label

    def _emit_scores(self, scores, count=None):
        """
        Get score of machine learning model and send it to the server.
        :param scores: precision, recall and f1 score
        :param count: current number of added train instances
        :return:
        """
        if count is None:
            count = self.get_count()
        precision, recall, f1 = scores
        message = {'precision': precision, 'recall': recall, 'f1': f1, 'count': count}
        self.namespace.emit('scores', message)
        logging.info("Sent scores {} at count {}".format(scores, count))

    def get_next_utterance(self, prev_annotation=None):
        """
        Override this in a custom model.
        :return: utterance, label/None
        """
        raise NotImplementedError

    def get_count(self):
        """
        Override this in a custom model.
        :return: current number of added training instances
        """
        raise NotImplementedError

    def get_scores(self):
        """
        Override this in a custom model.
        :return: precision, recall and f1 score
        """
        raise NotImplementedError

    def add_instance(self, utterance, annotation):
        """
        Override this in a custom model.
        :param utterance: text
        :param annotation: human label
        """
        raise NotImplementedError

    def _run_simulation(self):
        """
        Simulation mode.
        Started in a separate thread. Instead of asking a human to label an instance,
        read it from a provided label file and send results to the server.
        """
        label = None
        while True:
            utterance, label = self._emit_next_utterance(label)
            self.add_instance(utterance, label)

            scores = self.get_scores()
            self._emit_scores(scores)
